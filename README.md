# FinSight — AI Business Copilot

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green?style=flat&logo=node.js&logoColor=white)](https://nodejs.org/)
[![License](https://img.shields.io/badge/License-MIT-purple?style=flat)](#license)

> **Talk directly to your business numbers.** FinSight empowers business owners to track revenue and expenses, ingest bank statements, simulate what-if scenarios, and ask questions in plain language (*"Why is my profit lower this month?"*) with zero-hallucination, deterministic financial answers.

---

## 🏛️ Core Architecture Principle

> [!IMPORTANT]  
> **The Golden Rule:** The AI never performs mental arithmetic.  
> `Database (Source of Truth) → Analytics Engine (Calculations) → AI Copilot (Interpretation & Reasoning) → Frontend (Clean UI)`

```
┌─────────────────────────────────┐
│     Database (SQLite / PG)      │  ← Single source of truth (tenanted by business_id)
└───────────────┬─────────────────┘
                │ Raw records
┌───────────────▼─────────────────┐
│     Analytics Engine (Pandas)   │  ← Strict mathematical calculations & aggregations
└───────────────┬─────────────────┘
                │ Computed figures & ₹ formatting
┌───────────────▼─────────────────┐
│     AI Copilot / Tool Engine    │  ← Gemini API or Deterministic Fallback Rules
└───────────────┬─────────────────┘
                │ Natural language explanation & actionable advice
┌───────────────▼─────────────────┐
│     Next.js Web Interface       │  ← Human-friendly dashboards & interactive chat
└─────────────────────────────────┘
```

When you ask a question:
1. The AI evaluates the query and triggers an analytical tool (e.g., `get_profit`, `compare_months`, `calculate_scenario`).
2. The **Analytics Engine** executes deterministic queries and math using Pandas/SQL.
3. The AI receives verified figures (with standard Indian Rupee `₹` formatting) and synthesizes insights.
4. If no Gemini API key is configured, FinSight's **built-in rule-based analyst** takes over seamlessly—meaning the app is 100% functional out of the box with zero external API dependencies.

---

## ✨ Key Features

- **💬 Conversational Business Assistant**: Ask financial questions in natural language and receive grounded explanations with follow-up recommendations.
- **📈 Executive Financial Dashboard**: Real-time month-to-date (MTD) revenue, expenses, net profit, and profit margin trends.
- **⚖️ True Like-for-Like Comparisons**: On the 14th of the month, "this month" is compared to the first 14 days of last month—eliminating false alarms from early-month fixed costs (e.g., rent).
- **📂 Universal Statement Ingestion**: Drag-and-drop ingestion of **CSV, Excel (.xlsx, .xls), and PDF bank statements** with auto-column mapping, smart categorization, deduplication preview, and bulk import.
- **🔮 What-If Financial Simulator**: Model outcomes for price hikes, sales volume shifts, and cost-cutting measures with explicit assumptions stated.
- **💡 Actionable Profit Advice**: Automated detection of cost spikes, expense leakage, and clear steps to improve margins.
- **🔒 Multi-Tenant Data Isolation**: Every query, transaction, and calculation is scoped strictly by the authenticated user's `business_id`. Passwords hashed with `bcrypt`, authenticated via JWT.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**

---

### Step 1: Backend Setup (FastAPI)

1. Open a terminal and navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Windows (Command Prompt):**
     ```cmd
     python -m venv .venv
     .\.venv\Scripts\activate.bat
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - **macOS / Linux:**
     ```bash
     cp .env.example .env
     ```
   - **Windows:**
     ```powershell
     Copy-Item .env.example .env
     ```

5. Seed demo data (creates sample transactions and demo user):
   ```bash
   python seed.py
   ```

6. Start the API server:
   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```
   * Backend API: `http://localhost:8000`
   * Interactive Swagger Docs: `http://localhost:8000/docs`

---

### Step 2: Frontend Setup (Next.js)

1. Open a **new terminal window** and navigate to `frontend`:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   - **macOS / Linux:**
     ```bash
     cp .env.local.example .env.local
     ```
   - **Windows:**
     ```powershell
     Copy-Item .env.local.example .env.local
     ```

4. Start the development server:
   ```bash
   npm run dev
   ```
   * Web App: [http://localhost:3000](http://localhost:3000)

---

## 🔑 Demo Account Credentials

A pre-populated demo account is seeded out of the box with realistic revenue and expense history:

| Field | Value |
|---|---|
| **Email** | `demo@finsight.app` |
| **Password** | `demo12345` |

*(You can also click **Register** on the login page to create a fresh business account.)*

---

## 💬 Sample Prompts to Try in the Assistant

Navigate to the **Assistant** tab and try asking:

### 1. Performance & Diagnosis
- *"How much did I spend this month?"*
- *"What was my profit last month?"*
- *"Why is my profit lower this month?"*
- *"Which expense category is increasing the most?"*

### 2. Strategic Optimization
- *"What can I do to increase my profit?"*
- Follow up with: *"Show me how"*
- *"Where is most of my money going?"*

### 3. What-If Scenarios
- *"If I reduce my monthly expenses by ₹5,000, what happens to my profit?"*
- *"What happens if I increase my prices by 5%?"*
- *"If my sales drop by 10% and costs increase by 5%, what is my projected net margin?"*

### 4. Forecasting
- *"What could my revenue look like next month?"*

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./finsight.db` | SQLAlchemy connection string (`postgresql://...` for production) |
| `JWT_SECRET` | `change-me` | Secret key used to sign authentication tokens |
| `JWT_EXPIRE_MINUTES` | `720` | JWT expiration time in minutes (12 hours) |
| `FRONTEND_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated for multiple) |
| `BUSINESS_TIMEZONE` | `Asia/Kolkata` | Timezone used to evaluate "today" and "this month" |
| `GEMINI_API_KEY` | *(empty)* | Optional. Google Gemini API key for LLM-powered tool calling |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |

> [!NOTE]  
> If `GEMINI_API_KEY` is not provided, FinSight automatically falls back to its deterministic rule-based assistant (`ai/rules.py`). It still queries actual database numbers, provides exact math, and answers all core business inquiries.

### Frontend (`frontend/.env.local`)

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

---

## 📡 API Reference

All protected endpoints require an `Authorization: Bearer <token>` header obtained from `/api/auth/login`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register new business account & owner |
| `POST` | `/api/auth/login` | Authenticate and obtain JWT token |
| `GET` | `/api/auth/me` | Fetch authenticated user & business details |
| `GET` | `/api/dashboard` | Fetch aggregated KPI cards and monthly trends |
| `GET` | `/api/transactions` | Query transactions (filters: `type`, `category`, `month`) |
| `POST` | `/api/transactions` | Create a single transaction |
| `POST` | `/api/transactions/upload` | Parse & normalize CSV / Excel / PDF bank statement |
| `POST` | `/api/transactions/bulk` | Bulk insert verified transactions after preview |
| `PUT` | `/api/transactions/{id}` | Update existing transaction |
| `DELETE` | `/api/transactions/{id}` | Remove a transaction |
| `GET` | `/api/transactions/categories`| Get existing category list for revenue/expense |
| `GET` | `/api/analytics/monthly` | Retrieve monthly revenue, expense, and profit totals |
| `GET` | `/api/analytics/profit` | In-depth profit margin & growth breakdown |
| `GET` | `/api/analytics/expenses` | Category breakdown & growth alerts |
| `GET` | `/api/analytics/insights` | Actionable profit & cost recommendations |
| `GET` | `/api/analytics/forecast` | Linear trend projection with labelled assumptions |
| `POST` | `/api/analytics/scenario` | What-if simulation engine |
| `POST` | `/api/assistant/chat` | Conversational financial copilot endpoint |

Full interactive API docs and schema definitions are available at `http://localhost:8000/docs`.

---

## 🧪 Running Tests

FinSight includes comprehensive test suites covering Indian currency formatting, like-for-like date comparisons, what-if math, deterministic fallback assistants, and statement ingestion (CSV, XLSX, PDF).

To run the test suite:

```bash
cd backend
python -m pytest -v
```

Or run individual test modules:
```bash
python tests/test_analytics.py
python tests/test_ingestion.py
```

---

## 📂 Project Directory Structure

```text
finsight/
├── backend/
│   ├── main.py                     # FastAPI entry point & CORS configuration
│   ├── config.py                   # Pydantic Settings & environment variables
│   ├── seed.py                     # Database initialization and demo account seeding
│   ├── demo_data.py                # Realistic synthetic transactions
│   ├── api/                        # REST route controllers
│   │   ├── auth.py                 # Registration & JWT login
│   │   ├── transactions.py         # CRUD, file upload & bulk ingestion
│   │   ├── analytics.py            # Financial reports & scenario endpoints
│   │   ├── assistant.py            # AI assistant chat endpoint
│   │   └── deps.py                 # Auth and database dependencies
│   ├── models/                     # SQLAlchemy ORM models (User, Business, Transaction)
│   ├── schemas/                    # Pydantic request/response validation schemas
│   ├── services/                   # Core business logic
│   │   ├── financial_service.py    # Database queries & CRUD operations
│   │   ├── analytics_service.py    # Pandas calculations (profit, growth, scenarios)
│   │   └── ingestion_service.py    # Universal CSV/Excel/PDF parsing engine
│   ├── ai/                         # Copilot intelligence
│   │   ├── tools.py                # Tool registry exposing analytical functions
│   │   ├── agent.py                # Gemini tool-calling integration
│   │   ├── rules.py                # Deterministic zero-API fallback analyst
│   │   └── prompts.py              # System prompts & analytical tone guidelines
│   ├── database/                   # SQLAlchemy engine & session factory
│   ├── utils/                      # Security (bcrypt, JWT) & rate limiting
│   └── tests/                      # Pytest test suites
│
└── frontend/
    ├── app/                        # Next.js 14 App Router pages
    │   ├── login/                  # Authentication view
    │   ├── dashboard/              # High-level KPIs & trend graphs
    │   ├── expenses/               # Expense ledger & category breakdown
    │   ├── revenue/                # Revenue ledger & source analysis
    │   ├── analytics/              # Deep-dive analytics & what-if simulator
    │   └── assistant/              # Interactive AI chat interface
    ├── components/                 # Reusable UI components
    │   ├── AppShell.js             # Navigation sidebar & responsive layout
    │   ├── FileUploader.js         # Drag-and-drop statement parser modal
    │   ├── TransactionManager.js   # Ledger table with filters & pagination
    │   ├── RevenueChart.js         # Revenue vs expense area/bar charts
    │   ├── ExpenseChart.js         # Category allocation breakdown
    │   └── ChatBox.js              # Streaming conversational assistant UI
    ├── services/                   # Client-side API abstraction (`api.js`)
    └── lib/                        # Formatting utilities (INR ₹ formatting, dates)
```

---

## 🚢 Deployment Guidelines

### 1. Database (PostgreSQL)
- Create a managed PostgreSQL instance on **Supabase** or **Neon**.
- Update `DATABASE_URL` in your backend environment:
  ```text
  DATABASE_URL=postgresql://user:password@host:5432/finsight
  ```

### 2. Backend (Render / Railway / Fly.io)
- **Start Command**:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
- Set production environment variables: `DATABASE_URL`, `JWT_SECRET` (generate a 64-char string), `FRONTEND_ORIGINS` (your frontend domain), and optional `GEMINI_API_KEY`.

### 3. Frontend (Vercel)
- Deploy the `frontend/` directory to **Vercel**.
- Configure environment variable:
  ```text
  NEXT_PUBLIC_API_URL=https://your-backend-domain.com
  ```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
