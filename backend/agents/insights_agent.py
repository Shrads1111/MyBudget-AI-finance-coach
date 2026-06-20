from services.expense_service import ExpenseService
import logging

logger = logging.getLogger(__name__)

class InsightsAgent:
    @staticmethod
    def analyze(uid):
        """
        Generate spending recommendations and optimization strategies based on expense proportions.
        """
        try:
            expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            
            if not expenses:
                return {
                    "agent": "Insights Agent",
                    "status": "No data",
                    "recommendations": [
                        "Track your expenses daily to get personalized optimization tips.",
                        "Set up category budgets to limit unnecessary spending."
                    ]
                }

            total_spend = sum(float(e["amount"]) for e in expenses if e["category"] != "Income")
            
            if total_spend <= 0:
                return {
                    "agent": "Insights Agent",
                    "status": "No spending",
                    "recommendations": ["You have not spent anything yet. Keep up the high savings!"]
                }

            # Group by category
            cat_spend = {}
            for e in expenses:
                if e["category"] != "Income":
                    cat = e["category"]
                    cat_spend[cat] = cat_spend.get(cat, 0.0) + float(e["amount"])

            recommendations = []
            
            # Analyze food
            food_spend = cat_spend.get("Food", 0.0)
            food_ratio = food_spend / total_spend
            if food_ratio > 0.30:
                recommendations.append(
                    f"Food makes up {food_ratio*100:.1f}% of your budget (₹{food_spend:.2f}). "
                    "Consider cooking at home more often and planning meal splits with flatmates to save up to 25%."
                )

            # Analyze subscriptions
            sub_spend = cat_spend.get("Subscriptions", 0.0)
            sub_ratio = sub_spend / total_spend
            if sub_ratio > 0.10:
                recommendations.append(
                    f"Subscriptions represent {sub_ratio*100:.1f}% of your spending (₹{sub_spend:.2f}). "
                    "Audit your subscriptions (Netflix, Spotify, gym, etc.) and cancel any unused memberships."
                )

            # Analyze transport
            trans_spend = cat_spend.get("Transport", 0.0)
            trans_ratio = trans_spend / total_spend
            if trans_ratio > 0.20:
                recommendations.append(
                    f"Transport occupies {trans_ratio*100:.1f}% of your budget (₹{trans_spend:.2f}). "
                    "Consider public transit or ride-sharing pools instead of booking individual cabs."
                )

            # Default recommendation if list is small
            if len(recommendations) < 2:
                recommendations.append("Good job! Your category distributions look balanced. Keep tracking expenses.")
                recommendations.append("Build an emergency fund covering 3-6 months of expenses to ensure financial safety.")

            return {
                "agent": "Insights Agent",
                "status": "Success",
                "total_spend": round(total_spend, 2),
                "category_spend_distribution": {k: round(v, 2) for k, v in cat_spend.items()},
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"InsightsAgent error: {str(e)}")
            return {
                "agent": "Insights Agent",
                "status": "Error",
                "error_message": str(e)
            }
