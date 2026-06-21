from services.expense_service import ExpenseService
from services.budget_service import BudgetService
from datetime import datetime, date
from utils.constants import is_income
import calendar
import logging

logger = logging.getLogger(__name__)

class ForecastingAgent:
    @staticmethod
    def analyze(uid):
        """
        Predict end-of-month expenses, future savings, and budget exhaustion dates.
        """
        try:
            expenses = ExpenseService.get_expenses(uid, limit=1000)["expenses"]
            budgets = BudgetService.get_budgets(uid)
            
            today = datetime.utcnow().date()
            current_month_str = today.strftime("%Y-%m")
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            current_day = today.day

            # 1. End of month expense forecasting
            month_expenses = [e for e in expenses if e["date"].startswith(current_month_str) and not is_income(e["category"])]
            current_month_total = sum(float(e["amount"]) for e in month_expenses)
            
            # Forecast end-of-month spend
            daily_run_rate = current_month_total / current_day if current_day > 0 else 0.0
            projected_month_end = daily_run_rate * days_in_month

            # 2. Budget exhaustion date forecasting
            exhaustion_forecasts = []
            for b in budgets:
                limit = float(b["limit"])
                spent = float(b["spent"])
                category = b["category"]
                
                if spent > 0 and limit > 0:
                    cat_daily_rate = spent / current_day
                    if cat_daily_rate > 0:
                        projected_days_to_exhaust = limit / cat_daily_rate
                        
                        if projected_days_to_exhaust < days_in_month:
                            exhaust_day = int(projected_days_to_exhaust)
                            exhaust_day = max(1, min(exhaust_day, days_in_month))
                            exhaust_date = date(today.year, today.month, exhaust_day).strftime("%Y-%m-%d")
                            
                            exhaustion_forecasts.append({
                                "category": category,
                                "limit": limit,
                                "spent": spent,
                                "projected_exhaustion_date": exhaust_date,
                                "warning": f"Based on spending pace, your '{category}' budget will exhaust around {exhaust_date}."
                            })

            # 3. Future savings forecasting (based on income vs expenses)
            all_income = sum(float(e["amount"]) for e in expenses if is_income(e["category"]))
            all_expense = sum(float(e["amount"]) for e in expenses if not is_income(e["category"]))
            
            # Compute net savings rate (historical or monthly)
            # We can compute average monthly net savings
            net_savings = all_income - all_expense
            
            # Project future savings over 3, 6, 12 months
            # If historical savings is negative, assume 0 or warn
            monthly_saving_rate = max(0.0, net_savings)
            # If history is short, default to basic rate
            if len(expenses) < 5:
                monthly_saving_rate = 2000.0 # Standard student fallback rate
                
            projected_3_months = monthly_saving_rate * 3
            projected_6_months = monthly_saving_rate * 6
            projected_12_months = monthly_saving_rate * 12

            findings = f"At your current spend rate of ₹{daily_run_rate:.2f}/day, your projected end-of-month expenses will reach ₹{projected_month_end:.2f}."

            return {
                "agent": "Forecasting Agent",
                "status": "Success",
                "current_month_spend": round(current_month_total, 2),
                "projected_month_end_spend": round(projected_month_end, 2),
                "exhaustion_forecasts": exhaustion_forecasts,
                "projected_savings": {
                    "monthly_saving_rate": round(monthly_saving_rate, 2),
                    "projected_3_months": round(projected_3_months, 2),
                    "projected_6_months": round(projected_6_months, 2),
                    "projected_12_months": round(projected_12_months, 2)
                },
                "findings": findings
            }
        except Exception as e:
            logger.error(f"ForecastingAgent error: {str(e)}")
            return {
                "agent": "Forecasting Agent",
                "status": "Error",
                "error_message": str(e)
            }
