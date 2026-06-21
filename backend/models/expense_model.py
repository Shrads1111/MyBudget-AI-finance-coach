from datetime import datetime
from utils.constants import is_income

class Expense:
    def __init__(self, expense_id, uid, amount, category, description, date, created_at=None, updated_at=None, account_id=None, type=None):
        self.expense_id = expense_id
        self.uid = uid
        self.amount = float(amount)
        self.category = category
        self.description = description or ""
        self.date = date
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.account_id = account_id
        self.type = type or ("income" if is_income(category) else "expense")

    def to_dict(self):
        return {
            "expense_id": self.expense_id,
            "uid": self.uid,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "account_id": self.account_id,
            "type": self.type
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            expense_id=data.get("expense_id"),
            uid=data.get("uid"),
            amount=data.get("amount", 0.0),
            category=data.get("category"),
            description=data.get("description", ""),
            date=data.get("date"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            account_id=data.get("account_id"),
            type=data.get("type")
        )
