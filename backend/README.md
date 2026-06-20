# MyBudget Backend

This is the modular, production-ready backend for the **MyBudget** application. Built using Python Flask, Firebase (Authentication and Firestore), Gemini AI, and an Agentic AI design.

## Features

1. **Authentication & Identity Isolation:** Standard Firebase Auth token verification middleware. All CRUD collections isolate entries automatically using Firebase `uid`.
2. **Expenses Module:** Full CRUD operations supporting pagination, filtering (category, month, year), and custom sorting.
3. **Budget limits & Alerts:** Budget limits tracking per month and category. Recalculates spent metrics dynamically on expense updates and notifies user at `80%`, `90%`, and `100%` thresholds.
4. **Savings Goals progress:** Computes target progress percentages, remaining sums, and estimates monthly saving schedules required to meet deadlined goals.
5. **Dashboard Analytics:** Calculates aggregates, category spending distributions, remaining budgets, active goal counts, and recent transactions list.
6. **Group split budgeting:** Group creations, email/uid member invitations, expense posting, split calculations, roommate balance tallies, and suggested settlements mapping.
7. **Notifications Hub:** Dynamic notification builder for budget alerts, goal status changes, and general updates.
8. **AI Advisor & Coordinated Chat:** Call `/api/ai/analyze` for a consolidated behavioral financial report, or `/api/ai/chat` to speak to a multi-agent orchestrated financial assistant.

---

## Directory Structure

```text
backend/
├── app.py                # Flask entry point and blueprint loader
├── config.py             # Configuration settings and env validation
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies list
├── test_backend.py       # Integration tests suite (runs offline!)
├── firebase/
│   └── serviceAccountKey.json  # Firebase admin credential
├── middleware/
│   ├── auth_middleware.py      # Token verification
│   └── error_handler.py        # Centralized JSON exception mapping
├── models/
│   ├── user_model.py
│   ├── expense_model.py
│   ├── budget_model.py
│   └── goal_model.py
├── services/
│   ├── firebase_service.py     # Firebase SDK singleton wrapper
│   ├── expense_service.py
│   ├── budget_service.py
│   ├── savings_service.py
│   ├── group_service.py
│   ├── notification_service.py
│   ├── analytics_service.py
│   └── ai_service.py           # Gemini wrapper
├── routes/
│   ├── user_routes.py
│   ├── expense_routes.py
│   ├── budget_routes.py
│   ├── savings_routes.py
│   ├── group_routes.py
│   ├── notification_routes.py
│   ├── analytics_routes.py
│   └── ai_routes.py
├── agents/               # Multi-Agent AI system
│   ├── orchestrator.py
│   ├── expense_agent.py
│   ├── budget_agent.py
│   ├── savings_agent.py
│   ├── insights_agent.py
│   ├── finance_coach_agent.py
│   ├── forecasting_agent.py
│   └── health_score_agent.py
└── utils/
    ├── validator.py
    └── constants.py
```

---

## Setup & Running Locally

### 1. Prerequisites
- Python 3.10+
- A valid Firebase service account JSON key in `backend/firebase/serviceAccountKey.json`
- A Gemini API Key inside `backend/.env`

### 2. Installation
Initialize virtual environment and install packages:
```bash
# Navigate to backend directory
cd backend

# Activate Virtual Environment (Windows)
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run the Server
```bash
python app.py
```
The server starts on `http://localhost:5000` (based on environment config).

---

## How to Test

### Running Automated Integration Tests (Offline)
We have built a dedicated test suite `backend/test_backend.py` using Python's `unittest` library. It mocks Firebase Firestore calls and patches token verification to execute **completely offline and standalone**.

To run the suite:
```bash
# Make sure you are in the backend directory with virtual environment active
python test_backend.py
```

This runs all tests for:
- App configuration validations
- Expenses CRUD & filtering
- Budgets limits tracking & threshold calculations
- Savings Goals projections & deadlines
- Dashboard Analytics math
- Splitwise-style Group settlements mapping
- Mocked Gemini AI chat & financial recommendations engine

---

## API Endpoints List

### User Profile
- `POST /api/users/sync` - Syncs user profile metadata from decoded Firebase token.

### Expenses
- `POST /api/expenses` - Create expense.
- `GET /api/expenses` - Fetch expenses. Supports query params: `category`, `month` (YYYY-MM), `year` (YYYY), `sort_by` (date, amount), `sort_order` (asc, desc), `limit`, `offset`.
- `GET /api/expenses/<id>` - Fetch expense detail.
- `PUT /api/expenses/<id>` - Update expense.
- `DELETE /api/expenses/<id>` - Delete expense.

### Budgets
- `POST /api/budgets` - Create category budget cap.
- `GET /api/budgets` - Fetch budgets with updated spent fields.
- `GET /api/budgets/alerts` - Get budgets exceeding `80%` utilization.
- `GET /api/budgets/<id>` - Get budget detail.
- `PUT /api/budgets/<id>` - Update budget limit.
- `DELETE /api/budgets/<id>` - Delete budget.
- `GET /api/budgets/<id>/remaining` - Compute remaining limit space.

### Savings Goals
- `POST /api/goals` - Set savings goal.
- `GET /api/goals` - List savings goals with calculated progress.
- `GET /api/goals/<id>` - Goal details.
- `PUT /api/goals/<id>` - Edit savings goal fields.
- `DELETE /api/goals/<id>` - Delete savings goal.
- `GET /api/goals/<id>/progress` - Progress percentage & monthly savings needed.

### Groups Budget Splits
- `POST /api/groups` - Create split group budget.
- `POST /api/groups/invite` - Invite/add member (email/uid).
- `POST /api/groups/expense` - Post transaction paid by a member to split.
- `GET /api/groups/<id>` - Group details & transaction feeds.
- `GET /api/groups/<id>/summary` - Splitwise-style roommate balance tallies and suggested debt settlements.

### Notifications
- `GET /api/notifications` - Get user alerts log.
- `PUT /api/notifications/<id>/read` - Toggle read state.

### AI Advisor & Agents Chat
- `POST /api/ai/analyze` - Generates a consolidated financial behavior report using Gemini.
- `POST /api/ai/chat` - Chats with the orchestrated advisor. Request body: `{"query": "User question..."}`.
