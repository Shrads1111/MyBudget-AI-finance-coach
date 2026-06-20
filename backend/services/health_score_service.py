import datetime
import math
from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from services.savings_service import SavingsService
import logging

logger = logging.getLogger(__name__)

class HealthScoreService:
    @staticmethod
    def calculate_health_score(uid):
        try:
            # 1. Fetch live user data
            expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            budgets = BudgetService.get_budgets(uid)
            goals = SavingsService.get_goals(uid)

            # Get current month details
            now = datetime.datetime.utcnow()
            current_month_str = now.strftime("%Y-%m")

            # Initialize scores
            savings_score = 15.0
            budget_score = 12.5
            goals_score = 10.0
            stability_score = 15.0
            consistency_score = 2.0

            recommendations = []

            # ---- 1. SAVINGS RATE (Max 30 Points) ----
            # Compute total income vs expense
            income_total = sum(float(e["amount"]) for e in expenses if e["category"] == "Income")
            expense_total = sum(float(e["amount"]) for e in expenses if e["category"] != "Income")

            if income_total > 0:
                net_savings = income_total - expense_total
                savings_ratio = net_savings / income_total
                if savings_ratio >= 0.20:
                    savings_score = 30.0
                elif savings_ratio > 0:
                    savings_score = (savings_ratio / 0.20) * 30.0
                else:
                    savings_score = 0.0
                
                savings_pct = round(savings_ratio * 100, 1)
                if savings_ratio < 0.20:
                    recommendations.append(
                        f"Your current savings rate is {savings_pct}%. Try to save at least 20% of your total income."
                    )
            else:
                recommendations.append(
                    "No income recorded this period. Record stipends, pocket money, or earnings to accurately track your savings rate."
                )

            # ---- 2. BUDGET DISCIPLINE (Max 25 Points) ----
            if budgets:
                current_budgets = [b for b in budgets if b.get("month") == current_month_str]
                if not current_budgets:
                    # Fallback to all budgets if none exist for current month
                    current_budgets = budgets
                    
                overspent = sum(1 for b in current_budgets if float(b.get("spent", 0)) > float(b.get("limit", 0)))
                total_b = len(current_budgets)
                budget_score = (1.0 - (overspent / total_b)) * 25.0
                
                if overspent > 0:
                    recommendations.append(
                        f"You exceeded your spending limit in {overspent} out of {total_b} category budgets. Keep an eye on category caps."
                    )
            else:
                recommendations.append(
                    "You haven't configured any budget caps. Create category budgets to safeguard against overspending."
                )

            # ---- 3. GOAL COMPLETION (Max 20 Points) ----
            if goals:
                avg_progress = sum(float(g.get("progress_percentage", 0)) for g in goals) / len(goals)
                goals_score = (avg_progress / 100.0) * 20.0
                
                if avg_progress < 80.0:
                    recommendations.append(
                        f"Your savings goals are average {round(avg_progress, 1)}% complete. Contribute regularly to speed up completion."
                    )
            else:
                recommendations.append(
                    "No active savings goals found. Setting up specific goals (e.g., Laptop, Travel) improves saving motivation."
                )

            # ---- 4. EXPENSE STABILITY / ANOMALIES (Max 15 Points) ----
            # Detect spikes: transaction exceeding 3x average of non-income expenses
            non_income_expenses = [float(e["amount"]) for e in expenses if e["category"] != "Income"]
            if non_income_expenses:
                avg_expense = sum(non_income_expenses) / len(non_income_expenses)
                anomalies_count = sum(1 for amt in non_income_expenses if amt > avg_expense * 3)
                
                # Deduct 3 points per spike, bounded at 0
                stability_score = max(0.0, 15.0 - (3.0 * anomalies_count))
                if anomalies_count > 0:
                    recommendations.append(
                        f"We detected {anomalies_count} unusual spending spikes this month. Review large transactions to prevent budget leakage."
                    )
            else:
                stability_score = 7.5

            # ---- 5. FINANCIAL CONSISTENCY (Max 10 Points) ----
            # Distinct days of logged expenses/income in the current month
            month_txns = [e for e in expenses if e.get("date", "").startswith(current_month_str)]
            distinct_days = len(set(e.get("date") for e in month_txns if e.get("date")))
            
            if distinct_days >= 6:
                consistency_score = 10.0
            elif distinct_days >= 3:
                consistency_score = 5.0
            else:
                consistency_score = 2.0
                recommendations.append(
                    "Track your expenses more frequently. Logging transactions on at least 6 separate days a month secures your consistency score."
                )

            # Calculate total score
            total_score = round(savings_score + budget_score + goals_score + stability_score + consistency_score)
            
            # Map to Grade
            if total_score >= 90:
                grade = "A+"
            elif total_score >= 80:
                grade = "A"
            elif total_score >= 70:
                grade = "B"
            elif total_score >= 50:
                grade = "C"
            else:
                grade = "D"

            if not recommendations:
                recommendations.append("Excellent work! Your financial habits are balanced and consistent.")

            return {
                "score": total_score,
                "grade": grade,
                "breakdown": {
                    "savings": round(savings_score),
                    "budget": round(budget_score),
                    "goals": round(goals_score),
                    "stability": round(stability_score),
                    "consistency": round(consistency_score)
                },
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"Error calculating financial health score: {str(e)}")
            raise e
