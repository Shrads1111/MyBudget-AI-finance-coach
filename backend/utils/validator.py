import datetime
from middleware.error_handler import APIError
from utils.constants import EXPENSE_CATEGORIES, BUDGET_CATEGORIES

class Validator:
    @staticmethod
    def validate_amount(amount, field_name="amount"):
        try:
            val = float(amount)
            if val <= 0:
                raise APIError(f"{field_name} must be greater than zero", status_code=400)
            return val
        except (ValueError, TypeError):
            raise APIError(f"{field_name} must be a valid number", status_code=400)

    @staticmethod
    def validate_date(date_str, field_name="date"):
        if not date_str:
            raise APIError(f"{field_name} is required", status_code=400)
        try:
            # Expect YYYY-MM-DD
            datetime.datetime.strptime(str(date_str), "%Y-%m-%d")
            return str(date_str)
        except ValueError:
            raise APIError(f"{field_name} must be in YYYY-MM-DD format", status_code=400)

    @staticmethod
    def validate_expense_category(category):
        if not category:
            raise APIError("category is required", status_code=400)
        if category not in EXPENSE_CATEGORIES:
            raise APIError(f"Invalid category. Allowed: {', '.join(EXPENSE_CATEGORIES)}", status_code=400)
        return category

    @staticmethod
    def validate_budget_category(category):
        if not category:
            raise APIError("category is required", status_code=400)
        if category not in BUDGET_CATEGORIES:
            raise APIError(f"Invalid budget category. Allowed: {', '.join(BUDGET_CATEGORIES)}", status_code=400)
        return category

    @staticmethod
    def validate_limit(limit):
        return Validator.validate_amount(limit, "limit")

    @staticmethod
    def validate_budget_month(month_str):
        if not month_str:
            raise APIError("month is required", status_code=400)
        try:
            # Expect YYYY-MM
            datetime.datetime.strptime(str(month_str), "%Y-%m")
            return str(month_str)
        except ValueError:
            raise APIError("month must be in YYYY-MM format", status_code=400)
