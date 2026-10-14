# FinSight — AI business copilot

Talk to your business numbers. A business owner records revenue and expenses, then asks
questions in plain language ("Why is my profit lower this month?") and gets answers, explanations
and suggestions.

**The one rule of the architecture:**
`Database = source of truth → Analytics engine = calculations → AI = interpretation + conversation → Frontend = human-friendly experience.`
The AI never does arithmetic. It chooses a tool, the analytics engine computes the number from the database, and the AI explains it.

---

## Run it locally

You need **Python 3.11+** and **Node.js 18+**.

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # Windows: copy .env.example .env
python seed.py                       # creates demo account: demo@finsight.app / demo12345
uvicorn main:app --reload            # API on http://localhost:8000  (docs: /docs)
```

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local     # Windows: copy .env.local.example .env.local
npm run dev                          # http://localhost:3000
```

Log in with the demo account (or create your own), then try the questions below.

### 3. Tests (analytics + assistant logic)

```bash
cd backend
python tests/test_analytics.py       # or: pytest
```

### Questions to try

- How much did I spend this month? / What was my profit last month?
- Why is my profit lower this month? / Which expense is increasing the most?
- What can I do to increase my profit? → then: **show me how**
- If I reduce my monthly expenses by ₹5,000, what happens to my profit?
- What happens if I increase my price by 5%?
- What could my revenue look like next month?

---

## What we used, and how

| Tool | Where it lives | How we used it |
| --- | --- | --- |
| **Next.js 14 (App Router) + React** | `frontend/app`, `frontend/components` | Pages: login, dashboard, expenses, revenue, analytics, assistant. A shared `AppShell` redirects to `/login` when signed out. |
| **Tailwind CSS** | `frontend/app/globals.css`, class names | Styling. A few reusable classes (`card`, `btn`, `input`) keep pages consistent. |
| **Recharts** | `RevenueChart.js`, `ExpenseChart.js` | Revenue-vs-expenses-vs-profit chart and a "where is my money going" bar chart. Rising categories are highlighted amber. Every chart is titled with the question it answers. |
| **`services/api.js`** | `frontend/services` | The only place the browser talks to the backend. Adds the login token, turns API errors into readable messages. |
| **FastAPI** | `backend/main.py`, `backend/api/*` | REST API: auth, transactions CRUD, dashboard, analytics, assistant chat. Swagger docs at `/docs`. |
| **Pydantic** | `backend/schemas/*` | Validates every request (positive amounts, valid email, 8+ char password, max lengths). |
| **SQLAlchemy 2** | `backend/models/*`, `database/connection.py` | ORM models: users, businesses, transactions. SQLite by default; set `DATABASE_URL` to use PostgreSQL (Supabase / Neon) with no code change. |
| **PostgreSQL** | production database | Relational fit for business → transactions → categories. |
| **JWT (PyJWT) + bcrypt** | `backend/utils/security.py` | Passwords are stored as bcrypt hashes only. Login returns a signed, expiring token sent as `Authorization: Bearer …`. |
| **Pandas + NumPy** | `backend/services/analytics_service.py` | The analytics engine: profit, margin, growth, category breakdown, trends, linear-trend forecast, what-if scenarios, recommendations. |
| **Tool / function calling** | `backend/ai/tools.py`, `ai/agent.py` | 13 tools (`get_profit`, `compare_months`, `get_expense_growth`, `calculate_scenario`, …). The LLM picks a tool and arguments; the engine returns numbers (with ready-formatted ₹ strings); the LLM explains. |
| **Gemini API** (optional) | `backend/ai/agent.py` | Called from the server only (key in `.env`, never in the browser). Without a key, `ai/rules.py` answers the same questions with the same tools, so the app always works. |
| **Recommendation engine** | `Analytics.recommendations` | Number-backed advice: which category drives costs, how much could be saved, concrete steps. |
| **What-if simulator** | `Analytics.scenario`, Analytics page, chat | Price / sales / expense changes → projected profit, with the assumptions stated. |

### Design decisions worth knowing

- **Month-in-progress is compared like-for-like.** On the 7th, "this month" is compared with the first 7 days of last month, not the whole of last month. Recommendations use the last *full* month so early-month noise (rent paid on day 1) doesn't give bad advice.
- **Forecasts and what-ifs are labelled** as estimates/projections, with their assumptions.
- **Security:** every query is filtered by the logged-in user's business (the business is never taken from the URL, and other businesses' IDs return 404); passwords hashed; JWT expiry; CORS restricted to `FRONTEND_ORIGINS`; request validation; basic rate limiting on login and chat.

---

## API summary

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register`, `/api/auth/login` | Create account (+ business) / log in |
| GET | `/api/auth/me` | Current user + business |
| GET/POST | `/api/transactions` | List (filter by `type`, `category`, `month`) / create |
| PUT/DELETE | `/api/transactions/{id}` | Edit / delete |
| GET | `/api/transactions/categories?type=` | Category suggestions |
| GET | `/api/dashboard` | Everything the dashboard needs |
| GET | `/api/analytics/monthly`, `/profit`, `/expenses`, `/insights`, `/forecast` | Analytics |
| POST | `/api/analytics/scenario` | What-if analysis |
| POST | `/api/assistant/chat` | Ask FinSight (`{"message": "...", "history": []}`) |

## Enable Gemini

1. Create a key in Google AI Studio.
2. In `backend/.env` set `GEMINI_API_KEY=...` (and `GEMINI_MODEL` if you want a different model).
3. Restart the backend. `GET /api/health` shows `"assistant": "gemini"`.

If the Gemini call fails for any reason, the chat quietly falls back to the built-in analyst.

## Deploying

Frontend → Vercel (set `NEXT_PUBLIC_API_URL`). Backend → Render / Railway (`uvicorn main:app --host 0.0.0.0 --port $PORT`;
set `DATABASE_URL`, `JWT_SECRET`, `FRONTEND_ORIGINS`, `GEMINI_API_KEY`). Database → Supabase / Neon.

## Known limits (deliberately left out of the MVP)

- Voice, CSV/Excel/PDF import, and goals are not built yet (they are in the "later" part of the architecture).
- Tables are created with `create_all`; use Alembic migrations before changing the schema in production.
- The login token is kept in `localStorage` for simplicity; for production consider an httpOnly cookie.
- Rate limiting is in-memory (single instance); use Redis if you run several instances.
- Revenue and expenses share one `transactions` table (type = revenue/expense) instead of separate `revenue` and `expense_categories` tables.

## Project structure

```
finsight/
├── backend/
│   ├── main.py  config.py  seed.py  demo_data.py
│   ├── api/        auth, transactions, analytics, assistant, deps
│   ├── models/     user, business, transaction
│   ├── schemas/    user, transaction
│   ├── services/   financial_service, analytics_service, recommendation_service, ai_service
│   ├── ai/         prompts, tools, agent (Gemini), rules (built-in assistant)
│   ├── database/   connection
│   ├── utils/      security, ratelimit
│   └── tests/
└── frontend/
    ├── app/        login, dashboard, expenses, revenue, analytics, assistant
    ├── components/ AppShell, StatCard, RevenueChart, ExpenseChart, ChatBox, TransactionManager
    ├── services/   api.js
    └── lib/        format.js
```
