from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from services.savings_service import SavingsService
from datetime import datetime
import collections
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    @staticmethod
    def get_dashboard_summary(uid):
        try:
            # Fetch data (cap at 10000 expenses for analytics in-memory processing)
            expenses = ExpenseService.get_expenses(uid, limit=10000)["expenses"]
            budgets = BudgetService.get_budgets(uid)
            goals = SavingsService.get_goals(uid)

            now = datetime.utcnow()
            current_month_str = now.strftime("%Y-%m")

            # 1. Total expenses vs current month expenses
            total_exp_amt = 0.0
            current_month_exp_amt = 0.0
            for exp in expenses:
                amt = float(exp.get("amount", 0.0))
                # Skip "Income" category for expenses tallying
                if exp.get("category") != "Income":
                    total_exp_amt += amt
                    if exp.get("date", "").startswith(current_month_str):
                        current_month_exp_amt += amt

            # 2. Budget utilization summary
            budget_util = []
            for b in budgets:
                pct = (b["spent"] / b["limit"]) * 100.0 if b["limit"] > 0 else 0
                budget_util.append({
                    "category": b["category"],
                    "limit": b["limit"],
                    "spent": b["spent"],
                    "remaining": b["remaining"],
                    "utilization_percentage": round(pct, 2)
                })

            # 3. Active goals & Savings progress
            active_goals_count = 0
            savings_prog = []
            for g in goals:
                pct = g.get("progress_percentage", 0.0)
                if pct < 100.0:
                    active_goals_count += 1
                savings_prog.append({
                    "goal_id": g["goal_id"],
                    "goal_name": g["goal_name"],
                    "target_amount": g["target_amount"],
                    "current_amount": g["current_amount"],
                    "progress_percentage": pct,
                    "deadline": g["deadline"]
                })

            # 4. Top spending categories (excluding Income)
            cat_map = collections.defaultdict(float)
            for exp in expenses:
                if exp.get("category") != "Income":
                    cat_map[exp.get("category")] += float(exp.get("amount", 0.0))
                    
            top_categories = []
            for cat, amt in cat_map.items():
                top_categories.append({
                    "category": cat,
                    "total_amount": round(amt, 2)
                })
            top_categories.sort(key=lambda x: x["total_amount"], reverse=True)

            # 5. Recent transactions
            sorted_expenses = sorted(expenses, key=lambda x: x.get("date", ""), reverse=True)
            recent_txns = sorted_expenses[:5]

            return {
                "summary": {
                    "total_expenses": round(total_exp_amt, 2),
                    "monthly_expenses": round(current_month_exp_amt, 2),
                    "active_goals_count": active_goals_count
                },
                "budget_utilization": budget_util,
                "savings_progress": savings_prog,
                "top_spending_categories": top_categories,
                "recent_transactions": recent_txns
            }
        except Exception as e:
            logger.error(f"Error calculating dashboard summary: {str(e)}")
            raise e
