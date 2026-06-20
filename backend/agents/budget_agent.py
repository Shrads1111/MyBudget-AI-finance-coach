from services.budget_service import BudgetService
import logging

logger = logging.getLogger(__name__)

class BudgetAgent:
    @staticmethod
    def analyze(uid):
        """
        Analyze budget utilization, overspending risks, and exhaustion risks.
        """
        try:
            budgets = BudgetService.get_budgets(uid)
            
            if not budgets:
                return {
                    "agent": "Budget Agent",
                    "status": "No budgets set",
                    "overspending_risks": [],
                    "overall_utilization": 0.0,
                    "findings": "No budget categories configured. Setting budget limits helps control spending."
                }

            total_limit = 0.0
            total_spent = 0.0
            overspending_risks = []
            safe_categories = []

            for b in budgets:
                limit = float(b["limit"])
                spent = float(b["spent"])
                total_limit += limit
                total_spent += spent
                
                util_pct = (spent / limit) * 100.0 if limit > 0 else 0.0
                
                risk_item = {
                    "category": b["category"],
                    "limit": limit,
                    "spent": spent,
                    "remaining": b["remaining"],
                    "utilization_percentage": round(util_pct, 2)
                }

                if util_pct >= 100.0:
                    risk_item["risk_level"] = "Exhausted"
                    risk_item["advice"] = "Budget fully exhausted! Stop non-essential spending immediately in this category."
                    overspending_risks.append(risk_item)
                elif util_pct >= 80.0:
                    risk_item["risk_level"] = "High"
                    risk_item["advice"] = "High risk of exceeding budget limit soon. Reduce variable spending."
                    overspending_risks.append(risk_item)
                else:
                    risk_item["risk_level"] = "Low"
                    safe_categories.append(risk_item)

            overall_util = (total_spent / total_limit) * 100.0 if total_limit > 0 else 0.0
            findings = f"You have spent ₹{total_spent:.2f} out of a total budget limit of ₹{total_limit:.2f} ({overall_util:.1f}% utilized)."

            return {
                "agent": "Budget Agent",
                "status": "Success",
                "total_limit": total_limit,
                "total_spent": total_spent,
                "overall_utilization_percentage": round(overall_util, 2),
                "overspending_risks": overspending_risks,
                "safe_categories": safe_categories,
                "findings": findings
            }
        except Exception as e:
            logger.error(f"BudgetAgent error: {str(e)}")
            return {
                "agent": "Budget Agent",
                "status": "Error",
                "error_message": str(e)
            }
