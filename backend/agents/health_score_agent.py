from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from services.savings_service import SavingsService
from agents.expense_agent import ExpenseAgent
import logging

logger = logging.getLogger(__name__)

class HealthScoreAgent:
    @staticmethod
    def analyze(uid):
        """
        Calculate a financial health score (0-100) based on savings, budget discipline, consistency, and goals.
        """
        try:
            expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            budgets = BudgetService.get_budgets(uid)
            goals = SavingsService.get_goals(uid)

            # 1. Savings Ratio Score (Max 30 points)
            income_total = sum(float(e["amount"]) for e in expenses if e["category"] == "Income")
            expense_total = sum(float(e["amount"]) for e in expenses if e["category"] != "Income")
            
            savings_score = 15.0 # default fallback
            savings_ratio = 0.0
            if income_total > 0:
                net_savings = income_total - expense_total
                savings_ratio = net_savings / income_total
                if savings_ratio >= 0.20:
                    savings_score = 30.0
                elif savings_ratio > 0:
                    savings_score = (savings_ratio / 0.20) * 30.0
                else:
                    savings_score = 0.0

            # 2. Budget Discipline Score (Max 30 points)
            budget_score = 15.0 # default fallback if no budgets
            if budgets:
                overspent_count = sum(1 for b in budgets if float(b["spent"]) > float(b["limit"]))
                overspent_ratio = overspent_count / len(budgets)
                budget_score = (1.0 - overspent_ratio) * 30.0

            # 3. Spending Consistency Score (Max 20 points)
            # Penalize anomalies found by the ExpenseAgent
            consistency_score = 20.0
            exp_analysis = ExpenseAgent.analyze(uid)
            if exp_analysis.get("status") == "Success":
                anomalies_count = len(exp_analysis.get("anomalies", []))
                # Lose 5 points per anomaly, min 0
                consistency_score = max(0.0, 20.0 - (5.0 * anomalies_count))

            # 4. Goal Progress Score (Max 20 points)
            goal_score = 10.0 # default fallback if no goals
            if goals:
                avg_progress = sum(float(g["progress_percentage"]) for g in goals) / len(goals)
                goal_score = (avg_progress / 100.0) * 20.0

            total_score = round(savings_score + budget_score + consistency_score + goal_score, 1)
            
            # Formulate status message
            status = "Fair"
            advice = "Track your expenses carefully and set up categories limits to improve."
            
            if total_score >= 85:
                status = "Excellent"
                advice = "Outstanding financial management! You have strong savings discipline and goal tracking."
            elif total_score >= 70:
                status = "Good"
                advice = "Solid progress. Auditing small expense leaks can push your score to Excellent."
            elif total_score < 50:
                status = "Critical"
                advice = "Budget overruns or low savings ratio detected. Consider reducing luxury items."

            return {
                "agent": "Health Score Agent",
                "status": "Success",
                "health_score": total_score,
                "rating": status,
                "advice": advice,
                "breakdown": {
                    "savings_ratio_score": round(savings_score, 1),
                    "budget_discipline_score": round(budget_score, 1),
                    "consistency_score": round(consistency_score, 1),
                    "goal_progress_score": round(goal_score, 1)
                }
            }
        except Exception as e:
            logger.error(f"HealthScoreAgent error: {str(e)}")
            return {
                "agent": "Health Score Agent",
                "status": "Error",
                "error_message": str(e)
            }
