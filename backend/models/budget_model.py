class Budget:
    def __init__(self, budget_id, uid, category, limit, month, spent=0.0):
        self.budget_id = budget_id
        self.uid = uid
        self.category = category
        self.limit = float(limit)
        self.month = month # Format YYYY-MM
        self.spent = float(spent)

    @property
    def remaining(self):
        return max(0.0, self.limit - self.spent)

    def to_dict(self):
        return {
            "budget_id": self.budget_id,
            "uid": self.uid,
            "category": self.category,
            "limit": self.limit,
            "month": self.month,
            "spent": self.spent,
            "remaining": self.remaining
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            budget_id=data.get("budget_id"),
            uid=data.get("uid"),
            category=data.get("category"),
            limit=data.get("limit", 0.0),
            month=data.get("month"),
            spent=data.get("spent", 0.0)
        )
