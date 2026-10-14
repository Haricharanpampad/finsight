"""AI orchestration: the assistant decides *what to ask*, the analytics engine calculates.

Flow:  question -> LLM picks tools -> tools run on database numbers -> LLM explains the result.
If no Gemini key is configured (or the API fails), the rule-based assistant answers instead.
"""
from __future__ import annotations

import logging

import httpx

from ai.prompts import SYSTEM_PROMPT
from ai.rules import RuleAssistant
from ai.tools import TOOL_SPECS, run_tool
from services.analytics_service import Analytics

log = logging.getLogger("finsight.agent")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_TOOL_ROUNDS = 5


class FinSightAgent:
    def __init__(self, analytics: Analytics, api_key: str = "", model: str = "gemini-2.0-flash"):
        self.analytics = analytics
        self.api_key = api_key
        self.model = model

    def chat(self, message: str, history: list[dict] | None = None) -> dict:
        if self.api_key:
            try:
                return self._chat_gemini(message, history or [])
            except Exception as exc:  # network error, quota, unexpected response shape ...
                log.warning("Gemini call failed (%s); using rule-based assistant", exc)
        answer, tools = RuleAssistant(self.analytics).respond(message)
        return {"answer": answer, "tools_used": tools, "mode": "rules"}

    def _chat_gemini(self, message: str, history: list[dict]) -> dict:
        contents: list[dict] = []
        for turn in history[-10:]:
            role = "user" if turn["role"] == "user" else "model"
            if not contents and role == "model":
                continue  # Gemini conversations must start with a user turn
            contents.append({"role": role, "parts": [{"text": turn["text"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        tools_used: list[str] = []
        url = GEMINI_URL.format(model=self.model)
        headers = {"x-goog-api-key": self.api_key}  # key stays on the server, never in the browser
        with httpx.Client(timeout=30) as client:
            for _ in range(MAX_TOOL_ROUNDS):
                resp = client.post(url, headers=headers, json={
                    "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": contents,
                    "tools": [{"functionDeclarations": TOOL_SPECS}],
                    "generationConfig": {"temperature": 0.2},
                })
                resp.raise_for_status()
                parts = resp.json()["candidates"][0]["content"].get("parts", [])
                calls = [p["functionCall"] for p in parts if "functionCall" in p]
                if not calls:
                    text = "".join(p.get("text", "") for p in parts).strip()
                    if not text:
                        raise RuntimeError("empty model response")
                    return {"answer": text, "tools_used": tools_used, "mode": "gemini"}
                contents.append({"role": "model", "parts": parts})
                results = []
                for call in calls:
                    tools_used.append(call["name"])
                    result = run_tool(self.analytics, call["name"], call.get("args") or {})
                    results.append({"functionResponse": {"name": call["name"], "response": {"result": result}}})
                contents.append({"role": "user", "parts": results})
        raise RuntimeError("too many tool rounds")
