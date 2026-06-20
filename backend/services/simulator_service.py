import re
import datetime
from services.expense_service import ExpenseService
from services.ai_service import AIService
import logging

logger = logging.getLogger(__name__)

class SimulatorService:
    @staticmethod
    def parse_amount(text):
        """Helper to extract numbers like 5000, 100000, 1 lakh, 5k from query"""
        # Look for lakh
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|L)', text, re.IGNORECASE)
        if lakh_match:
            return float(lakh_match.group(1)) * 100000

        # Look for k (thousand)
        k_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|K)', text, re.IGNORECASE)
        if k_match:
            return float(k_match.group(1)) * 1000

        # Standard digits
        digit_match = re.search(r'(?:₹|rs|rs\.|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)', text, re.IGNORECASE)
        if digit_match:
            val_str = digit_match.group(1).replace(',', '')
            try:
                return float(val_str)
            except ValueError:
                pass
        return None

    @staticmethod
    def simulate(uid, query):
        try:
            # Gather base numbers to validate calculations
            expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            income_total = sum(float(e["amount"]) for e in expenses if e["category"] == "Income")
            expense_total = sum(float(e["amount"]) for e in expenses if e["category"] != "Income")

            # Default fallbacks for student cash flows
            est_monthly_income = max(10000.0, income_total)
            est_monthly_expense = max(4000.0, expense_total)
            est_monthly_savings = max(1000.0, est_monthly_income - est_monthly_expense)

            query_lower = query.lower()
            sim_type = "general_projection"
            math_results = {}

            # ---- Pattern 1: Savings Goal Simulation (save X, reach Y) ----
            # "If I save 5000 per month, when will I reach 1 lakh?"
            if "reach" in query_lower or "target" in query_lower or "accumulate" in query_lower:
                sim_type = "savings_target"
                
                matches = re.findall(r'(\d+(?:\.\d+)?)\s*(lakh|lakhs|L|k|K)?', query, re.IGNORECASE)
                parsed_vals = []
                for num_str, suffix in matches:
                    try:
                        val = float(num_str.replace(',', ''))
                        suffix_lower = suffix.lower() if suffix else ""
                        if suffix_lower in ['lakh', 'lakhs', 'l']:
                            val *= 100000
                        elif suffix_lower in ['k']:
                            val *= 1000
                        parsed_vals.append(val)
                    except ValueError:
                        pass
                
                if len(parsed_vals) >= 2:
                    target = max(parsed_vals)
                    monthly = min(parsed_vals)
                elif len(parsed_vals) == 1:
                    target = parsed_vals[0]
                    monthly = target * 0.05  # Assume saving 5% of target per month
                else:
                    target = 100000.0
                    monthly = 5000.0
                
                if not monthly or monthly <= 0:
                    monthly = 5000.0

                months_needed = target / monthly
                math_results = {
                    "monthly_savings": round(monthly, 2),
                    "target_amount": round(target, 2),
                    "months_required": round(months_needed, 1),
                    "projected_savings": round(target, 2)
                }


            # ---- Pattern 2: Category Expense Reduction (reduce category X by P%) ----
            # "If I reduce food spending by 20%, how much money will I save annually?"
            elif "reduce" in query_lower or "cut" in query_lower or "lower" in query_lower:
                sim_type = "expense_reduction"
                
                # Find category
                category = "Food"
                for cat in ["food", "transport", "subscriptions", "entertainment", "education", "bills"]:
                    if cat in query_lower:
                        category = cat.title()
                        break
                
                # Find percentage
                pct_match = re.search(r'(\d+)\s*%', query)
                pct = 20.0
                if pct_match:
                    pct = float(pct_match.group(1))
                else:
                    # Look for digits
                    numbers = re.findall(r'\d+', query)
                    if numbers:
                        pct = float(numbers[0])

                # Get actual monthly spend in category
                cat_expenses = [float(e["amount"]) for e in expenses if e["category"].lower() == category.lower()]
                monthly_cat_spend = sum(cat_expenses) if cat_expenses else 3500.0 # student default fallback
                
                monthly_savings = monthly_cat_spend * (pct / 100.0)
                annual_savings = monthly_savings * 12.0

                math_results = {
                    "category": category,
                    "reduction_percentage": pct,
                    "monthly_category_spend": round(monthly_cat_spend, 2),
                    "monthly_savings": round(monthly_savings, 2),
                    "annual_savings": round(annual_savings, 2)
                }

            # ---- Pattern 3: Savings Rate Increase (increase savings by P%) ----
            # "If I increase my savings rate by 10%, what happens after one year?"
            elif "increase" in query_lower or "raise" in query_lower:
                sim_type = "savings_rate_increase"
                
                # Find percentage
                pct_match = re.search(r'(\d+)\s*%', query)
                pct = 10.0
                if pct_match:
                    pct = float(pct_match.group(1))
                else:
                    numbers = re.findall(r'\d+', query)
                    if numbers:
                        pct = float(numbers[0])

                extra_monthly_savings = est_monthly_income * (pct / 100.0)
                annual_extra_savings = extra_monthly_savings * 12.0
                projected_total = (est_monthly_savings + extra_monthly_savings) * 12.0

                math_results = {
                    "increase_percentage": pct,
                    "estimated_monthly_income": round(est_monthly_income, 2),
                    "monthly_extra": round(extra_monthly_savings, 2),
                    "annual_extra": round(annual_extra_savings, 2),
                    "projected_total_savings_1yr": round(projected_total, 2)
                }

            # ---- Pattern 4: Fallback General Projection ----
            else:
                math_results = {
                    "current_monthly_savings": round(est_monthly_savings, 2),
                    "projected_savings_3m": round(est_monthly_savings * 3, 2),
                    "projected_savings_6m": round(est_monthly_savings * 6, 2),
                    "projected_savings_12m": round(est_monthly_savings * 12, 2)
                }

            # 5. Build prompt for Gemini explanation
            prompt = f"""
You are the AI Financial Simulator for MyBudget.
The user submitted a future simulation scenario.
User Query: "{query}"

Here are the EXACT mathematical results we calculated deterministically from our backend:
Simulation Type: {sim_type}
Calculations: {math_results}

Write a clean, encouraging, student-focused explanation of these results.
NEVER alter or recalculate the math. Always cite the exact values from 'Calculations' (e.g. months required, monthly savings, annual extra).
Focus on budgeting impact, compounding habits, and tips to achieve this goal. Keep it under 150 words.
"""
            explanation = AIService.generate_content(prompt)

            return {
                "type": sim_type,
                "result": math_results,
                "explanation": explanation
            }
        except Exception as e:
            logger.error(f"Error executing AI financial simulation: {str(e)}")
            raise e
