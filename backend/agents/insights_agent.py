from services.expense_service import ExpenseService
from services.recurring_service import RecurringService
import logging

logger = logging.getLogger(__name__)

class InsightsAgent:
    @staticmethod
    def analyze(uid):
        """
        Generate spending recommendations and optimization strategies based on expense proportions and recurring commitments.
        """
        try:
            expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            
            try:
                recurring_payments = RecurringService.get_recurring(uid)
            except Exception as re:
                logger.error(f"Error fetching recurring payments in InsightsAgent: {str(re)}")
                recurring_payments = []
            
            # Calculate recurring commitments
            total_monthly_recurring = 0.0
            category_totals = {}
            for rp in recurring_payments:
                amt = float(rp.get("amount", 0.0))
                freq = rp.get("frequency", "Monthly").lower()
                cat = rp.get("category", "Custom")
                
                # Convert to monthly equivalent
                if freq == "daily":
                    m_equiv = amt * 30.0
                elif freq == "weekly":
                    m_equiv = amt * 4.33
                elif freq == "monthly":
                    m_equiv = amt
                elif freq == "quarterly":
                    m_equiv = amt / 3.0
                elif freq == "half-yearly":
                    m_equiv = amt / 6.0
                elif freq == "yearly":
                    m_equiv = amt / 12.0
                else:
                    m_equiv = amt
                    
                total_monthly_recurring += m_equiv
                category_totals[cat] = category_totals.get(cat, 0.0) + m_equiv

            if not expenses:
                recommendations = [
                    "Track your expenses daily to get personalized optimization tips.",
                    "Set up category budgets to limit unnecessary spending."
                ]
                if total_monthly_recurring > 0:
                    recommendations.append(
                        f"You have ₹{total_monthly_recurring:.2f} in monthly recurring commitments. "
                        "Make sure to track daily expenses alongside these commitments to get full insights."
                    )
                return {
                    "agent": "Insights Agent",
                    "status": "No data",
                    "total_monthly_recurring_commitments": round(total_monthly_recurring, 2),
                    "recurring_commitments_by_category": {k: round(v, 2) for k, v in category_totals.items()},
                    "recommendations": recommendations
                }

            total_spend = sum(float(e["amount"]) for e in expenses if e["category"] != "Income")
            
            if total_spend <= 0:
                recommendations = ["You have not spent anything yet. Keep up the high savings!"]
                if total_monthly_recurring > 0:
                    recommendations.append(
                        f"You have ₹{total_monthly_recurring:.2f} in monthly recurring commitments. "
                        "As you pay them, they will be logged as expenses automatically."
                    )
                return {
                    "agent": "Insights Agent",
                    "status": "No spending",
                    "total_monthly_recurring_commitments": round(total_monthly_recurring, 2),
                    "recurring_commitments_by_category": {k: round(v, 2) for k, v in category_totals.items()},
                    "recommendations": recommendations
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
                    "Consider cooking at home more often and planning meal splits with flatmates to save up to 25."
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

            # Analyze recurring payments
            if total_monthly_recurring > 0:
                recommendations.append(
                    f"Your monthly recurring commitments (SIPs, bills, subscriptions) are estimated at ₹{total_monthly_recurring:.2f}. "
                    "Ensure your linked bank accounts maintain a sufficient balance to avoid failed auto-debits."
                )
                
            sip_count = sum(1 for rp in recurring_payments if rp.get("category") in ["SIP", "Mutual Fund", "PPF", "RD"])
            if sip_count > 0:
                recommendations.append(
                    f"You have {sip_count} active investment/savings commitments (SIPs, Mutual Funds, etc.). "
                    "This disciplined approach to wealth accumulation is highly recommended. Keep it up!"
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
                "total_monthly_recurring_commitments": round(total_monthly_recurring, 2),
                "recurring_commitments_by_category": {k: round(v, 2) for k, v in category_totals.items()},
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"InsightsAgent error: {str(e)}")
            return {
                "agent": "Insights Agent",
                "status": "Error",
                "error_message": str(e)
            }
