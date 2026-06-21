import datetime
from collections import defaultdict
from services.expense_service import ExpenseService
from utils.constants import is_income
import logging

logger = logging.getLogger(__name__)

class PatternDetectionService:
    @staticmethod
    def detect_patterns(uid):
        try:
            # 1. Fetch expenses
            expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            non_income = [e for e in expenses if not is_income(e["category"])]

            patterns = []

            if not non_income:
                return [
                    {
                        "type": "no_data",
                        "message": "Start tracking your daily expenses to enable AI-powered spending pattern insights."
                    }
                ]

            now = datetime.datetime.utcnow().date()
            current_month_str = now.strftime("%Y-%m")
            
            # Previous month string YYYY-MM
            first_day_current = now.replace(day=1)
            last_day_prev = first_day_current - datetime.timedelta(days=1)
            prev_month_str = last_day_prev.strftime("%Y-%m")

            # Grouping by month
            current_month_exp = [e for e in non_income if e.get("date", "").startswith(current_month_str)]
            prev_month_exp = [e for e in non_income if e.get("date", "").startswith(prev_month_str)]

            # ---- 1. Weekend vs Weekday Spending ----
            weekend_amounts = []
            weekday_amounts = []

            for exp in non_income:
                date_str = exp.get("date")
                if not date_str:
                    continue
                try:
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    # Saturday = 5, Sunday = 6
                    if dt.weekday() in [5, 6]:
                        weekend_amounts.append(float(exp["amount"]))
                    else:
                        weekday_amounts.append(float(exp["amount"]))
                except Exception:
                    pass

            if weekend_amounts and weekday_amounts:
                weekend_avg = sum(weekend_amounts) / len(weekend_amounts)
                weekday_avg = sum(weekday_amounts) / len(weekday_amounts)
                
                if weekend_avg > weekday_avg * 1.15:
                    pct_increase = round(((weekend_avg - weekday_avg) / weekday_avg) * 100)
                    patterns.append({
                        "type": "weekend_spending",
                        "message": f"You spend {pct_increase}% more on weekends. Try setting weekend dining out caps."
                    })

            # ---- 2. Category Growth (Current vs Prev Month) ----
            current_cat_totals = defaultdict(float)
            prev_cat_totals = defaultdict(float)

            for exp in current_month_exp:
                current_cat_totals[exp["category"]] += float(exp["amount"])

            for exp in prev_month_exp:
                prev_cat_totals[exp["category"]] += float(exp["amount"])

            for cat, curr_total in current_cat_totals.items():
                prev_total = prev_cat_totals.get(cat, 0.0)
                if prev_total > 100.0:  # Only track growth for substantial category spending
                    growth = (curr_total - prev_total) / prev_total
                    if growth >= 0.20:
                        patterns.append({
                            "type": "category_growth",
                            "message": f"{cat} spending increased by {round(growth * 100)}% compared to last month."
                        })

            # ---- 3. Shopping Surges (Large anomalous purchases) ----
            all_amounts = [float(e["amount"]) for e in non_income]
            all_amounts.sort()
            
            if len(all_amounts) >= 3:
                # Find median
                mid = len(all_amounts) // 2
                median_amount = all_amounts[mid]
                
                # Check for current month purchases > 3x median
                for exp in current_month_exp:
                    amount = float(exp["amount"])
                    if amount > median_amount * 3.0:
                        patterns.append({
                            "type": "shopping_surge",
                            "message": f"Detected a spending surge of ₹{round(amount)} on '{exp.get('description', exp['category'])}'."
                        })

            # ---- 4. Monthly Spending Trend ----
            curr_month_total = sum(float(e["amount"]) for e in current_month_exp)
            prev_month_total = sum(float(e["amount"]) for e in prev_month_exp)

            if curr_month_total > 0 and prev_month_total > 0:
                diff = curr_month_total - prev_month_total
                pct = round((abs(diff) / prev_month_total) * 100)
                
                if diff > 0:
                    patterns.append({
                        "type": "monthly_increase",
                        "message": f"Your monthly spending is up by {pct}% compared to last month."
                    })
                else:
                    patterns.append({
                        "type": "monthly_decrease",
                        "message": f"Great job! Your monthly spending is down by {pct}% compared to last month."
                    })

            # ---- 5. Frequent Merchant Detection ----
            merchants = defaultdict(int)
            for exp in current_month_exp:
                desc = exp.get("description", "").strip().lower()
                if desc and len(desc) > 2:
                    merchants[desc] += 1

            for merchant, count in merchants.items():
                if count >= 3:
                    patterns.append({
                        "type": "frequent_merchant",
                        "message": f"You made {count} transactions at '{merchant.title()}' this month."
                    })

            # Add default insight if no pattern triggers
            if not patterns:
                patterns.append({
                    "type": "steady_saving",
                    "message": "Your spending patterns look steady. Keep tracking to identify future optimization areas."
                })

            return patterns
        except Exception as e:
            logger.error(f"Error detecting spending patterns: {str(e)}")
            raise e
