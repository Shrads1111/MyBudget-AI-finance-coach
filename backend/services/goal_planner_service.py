import datetime
from services.savings_service import SavingsService
from services.expense_service import ExpenseService
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)

class GoalPlannerService:
    @staticmethod
    def get_goal_plan(uid, goal_id):
        try:
            # 1. Fetch goal
            goal = SavingsService.get_goal_by_id(uid, goal_id)
            
            target = float(goal.get("target_amount", 0.0))
            current = float(goal.get("current_amount", 0.0))
            deadline = goal.get("deadline")
            
            remaining = max(0.0, target - current)

            # 2. Calculate remaining months/days
            try:
                deadline_date = datetime.datetime.strptime(str(deadline), "%Y-%m-%d").date()
                today = datetime.datetime.utcnow().date()
                days_remaining = (deadline_date - today).days
                if days_remaining <= 0:
                    days_remaining = 1
                months_remaining = max(0.1, days_remaining / 30.4)
            except Exception:
                days_remaining = 30
                months_remaining = 1.0

            # 3. Calculate targets
            if remaining <= 0:
                monthly_target = 0.0
                weekly_target = 0.0
                daily_target = 0.0
                completion_probability = 100
            else:
                monthly_target = round(remaining / months_remaining, 2)
                weekly_target = round(remaining / (months_remaining * 4.345), 2)
                daily_target = round(remaining / days_remaining, 2)

                # 4. Calculate Cash Flow Savings Rate for completion probability
                expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
                income_total = sum(float(e["amount"]) for e in expenses if e["category"] == "Income")
                expense_total = sum(float(e["amount"]) for e in expenses if e["category"] != "Income")

                # Estimate user monthly net savings
                # Assume a minimum basic saving capacity of ₹2,500/mo if no transactions exist
                monthly_saving_capacity = 2500.0
                
                # Check if there is transaction history to build a real rate
                if expenses:
                    # Estimate number of months represented in transactions
                    dates = [e.get("date") for e in expenses if e.get("date")]
                    if dates:
                        try:
                            min_d = datetime.datetime.strptime(min(dates), "%Y-%m-%d").date()
                            max_d = datetime.datetime.strptime(max(dates), "%Y-%m-%d").date()
                            span_days = max(1, (max_d - min_d).days)
                            span_months = span_days / 30.4
                        except Exception:
                            span_months = 1.0
                    else:
                        span_months = 1.0

                    span_months = max(1.0, span_months)
                    net_savings = income_total - expense_total
                    
                    if net_savings > 0:
                        monthly_saving_capacity = net_savings / span_months

                # Compare monthly capacity vs required monthly target
                if monthly_saving_capacity >= monthly_target:
                    # Safe zone
                    completion_probability = int(min(98, 85 + (monthly_saving_capacity / monthly_target * 5)))
                else:
                    # Deficit zone
                    ratio = monthly_saving_capacity / monthly_target if monthly_target > 0 else 0
                    completion_probability = int(max(10, ratio * 85))

            return {
                "goal_id": goal_id,
                "goal_name": goal.get("goal_name"),
                "target_amount": target,
                "current_amount": current,
                "remaining_amount": remaining,
                "deadline": deadline,
                "monthly_target": round(monthly_target),
                "weekly_target": round(weekly_target),
                "daily_target": round(daily_target),
                "completion_probability": completion_probability,
                "estimated_completion_date": deadline
            }
        except Exception as e:
            logger.error(f"Error generating goal plan for {goal_id}: {str(e)}")
            raise e
