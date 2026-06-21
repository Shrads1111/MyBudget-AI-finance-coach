from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from services.savings_service import SavingsService
from services.group_service import GroupService
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

            # 1. Total expenses, total income, current month expenses
            total_exp_amt = 0.0
            total_income_amt = 0.0
            current_month_exp_amt = 0.0
            cat_map = collections.defaultdict(float)

            for exp in expenses:
                amt = float(exp.get("amount", 0.0))
                category = exp.get("category", "")

                if category == "Income":
                    total_income_amt += amt
                else:
                    total_exp_amt += amt
                    cat_map[category] += amt
                    if exp.get("date", "").startswith(current_month_str):
                        current_month_exp_amt += amt

            # Total balance = Income - Expenses
            total_balance = round(total_income_amt - total_exp_amt, 2)

            # 2. Friend owe — amount owed TO the user across all groups, plus detailed breakdown
            friend_owe_you = 0.0
            friend_you_owe = 0.0
            try:
                user_groups = GroupService.get_user_groups(uid)
                for group in user_groups:
                    group_id = group.get("group_id")
                    if not group_id:
                        continue
                    summary = GroupService.get_group_summary(uid, group_id)
                    balances = summary.get("balances", {})
                    user_balance = balances.get(uid, 0.0)
                    if user_balance > 0:
                        friend_owe_you += user_balance
                    elif user_balance < 0:
                        friend_you_owe += abs(user_balance)
            except Exception as ge:
                logger.warning(f"Could not calculate friend_owe details for {uid}: {str(ge)}")
                friend_owe_you = 0.0
                friend_you_owe = 0.0

            friend_owe_you = round(friend_owe_you, 2)
            friend_you_owe = round(friend_you_owe, 2)
            friend_net = round(friend_owe_you - friend_you_owe, 2)

            # 3. Budget utilization summary
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

            # 4. Active goals & Savings progress
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

            # 5. Top spending categories (excluding Income) — also used for pie chart
            top_categories = []
            expense_by_category = {}
            total_non_income = sum(cat_map.values())
            for cat, amt in cat_map.items():
                rounded_amt = round(amt, 2)
                pct = round((amt / total_non_income) * 100, 1) if total_non_income > 0 else 0
                top_categories.append({"category": cat, "total_amount": rounded_amt})
                expense_by_category[cat] = {
                    "amount": rounded_amt,
                    "percentage": pct
                }
            top_categories.sort(key=lambda x: x["total_amount"], reverse=True)

            # 6. Recent transactions
            sorted_expenses = sorted(expenses, key=lambda x: x.get("date", ""), reverse=True)
            recent_txns = sorted_expenses[:5]

            return {
                "summary": {
                    "total_expenses": round(total_exp_amt, 2),
                    "monthly_expenses": round(current_month_exp_amt, 2),
                    "active_goals_count": active_goals_count,
                    "total_balance": total_balance,
                    "total_income": round(total_income_amt, 2),
                    "friend_owe": friend_owe_you,
                    "friend_owe_you": friend_owe_you,
                    "friend_you_owe": friend_you_owe,
                    "friend_net": friend_net
                },
                "budget_utilization": budget_util,
                "savings_progress": savings_prog,
                "top_spending_categories": top_categories,
                "expense_by_category": expense_by_category,
                "recent_transactions": recent_txns
            }
        except Exception as e:
            logger.error(f"Error calculating dashboard summary: {str(e)}")
            raise e
