import math
from services.expense_service import ExpenseService
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class ExpenseAgent:
    @staticmethod
    def analyze(uid):
        """
        Analyze user spending patterns, category trends, and anomalies.
        """
        try:
            # Fetch user expenses
            expenses_data = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            
            if not expenses_data:
                return {
                    "agent": "Expense Agent",
                    "status": "No data available",
                    "anomalies": [],
                    "category_trends": {},
                    "patterns": "No spending patterns can be recognized due to lack of transaction history."
                }

            amounts = [float(e["amount"]) for e in expenses_data if e["category"] != "Income"]
            
            if not amounts:
                return {
                    "agent": "Expense Agent",
                    "status": "No expenses recorded",
                    "anomalies": [],
                    "category_trends": {},
                    "patterns": "No expense transactions recorded."
                }

            # Basic stats using standard python
            avg_amount = sum(amounts) / len(amounts)
            
            variance = sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)
            std_amount = math.sqrt(variance) if len(amounts) > 1 else 0.0

            
            # 1. Identify anomalies (transactions > average + 2*std, or general high spikes)
            anomalies = []
            threshold = avg_amount + (2 * std_amount) if std_amount > 0 else avg_amount * 3
            
            for exp in expenses_data:
                if exp["category"] != "Income" and float(exp["amount"]) > threshold:
                    anomalies.append({
                        "expense_id": exp["expense_id"],
                        "category": exp["category"],
                        "amount": exp["amount"],
                        "description": exp["description"],
                        "date": exp["date"],
                        "reason": f"Amount is significantly higher than average transaction size (₹{avg_amount:.2f})"
                    })

            # 2. Category trends
            cat_totals = defaultdict(float)
            cat_counts = defaultdict(int)
            for exp in expenses_data:
                if exp["category"] != "Income":
                    cat_totals[exp["category"]] += float(exp["amount"])
                    cat_counts[exp["category"]] += 1

            category_trends = {}
            for cat, total in cat_totals.items():
                category_trends[cat] = {
                    "total_amount": round(total, 2),
                    "transaction_count": cat_counts[cat],
                    "average_transaction": round(total / cat_counts[cat], 2)
                }

            # 3. Text patterns summary
            top_category = max(cat_totals, key=cat_totals.get) if cat_totals else "None"
            patterns = f"Your highest spending category is {top_category} with total spend of ₹{cat_totals.get(top_category, 0):.2f}. " \
                       f"Your average purchase size across all categories is ₹{avg_amount:.2f}."

            return {
                "agent": "Expense Agent",
                "status": "Success",
                "average_transaction": round(avg_amount, 2),
                "anomalies": anomalies,
                "category_trends": category_trends,
                "patterns": patterns
            }
        except Exception as e:
            logger.error(f"ExpenseAgent error: {str(e)}")
            return {
                "agent": "Expense Agent",
                "status": "Error",
                "error_message": str(e)
            }
