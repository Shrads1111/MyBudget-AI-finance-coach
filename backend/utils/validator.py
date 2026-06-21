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
            # Normalize to two decimal places
            return round(val, 2)
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
        # Accept any non-empty string — this allows custom user-defined categories
        # while still rejecting missing/null values.
        # Budget categories remain strictly validated separately.
        if not category or not str(category).strip():
            raise APIError("category is required", status_code=400)
        return str(category).strip()

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

    @staticmethod
    def validate_allowed_fields(data: dict, allowed_fields: list):
        """Reject any keys not explicitly allowed.
        Raises APIError if unknown fields are present.
        """
        unknown = set(data.keys()) - set(allowed_fields)
        if unknown:
            raise APIError(f"Unsupported field(s): {', '.join(unknown)}", status_code=400)
        return True

    @staticmethod
    def validate_positive_int(value, field_name="value"):
        try:
            iv = int(value)
            if iv < 0:
                raise APIError(f"{field_name} must be a non‑negative integer", status_code=400)
            return iv
        except (ValueError, TypeError):
            raise APIError(f"{field_name} must be an integer", status_code=400)

    @staticmethod
    def validate_sort_params(sort_by: str, sort_order: str, allowed_sort_fields=None):
        if allowed_sort_fields is None:
            allowed_sort_fields = ["date", "amount", "category"]
        if sort_by not in allowed_sort_fields:
            raise APIError(f"Invalid sort_by field. Allowed: {', '.join(allowed_sort_fields)}", status_code=400)
        if sort_order.lower() not in ["asc", "desc"]:
            raise APIError("sort_order must be 'asc' or 'desc'", status_code=400)
        return sort_by, sort_order.lower()
