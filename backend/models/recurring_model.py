from datetime import datetime

class RecurringPayment:
    def __init__(self, recurring_id, uid, title, amount, category, frequency, start_date, next_due_date, notes="", created_at=None):
        self.recurring_id = recurring_id
        self.uid = uid
        self.title = title
        self.amount = float(amount)
        self.category = category # SIP, Mutual Fund, PPF, RD, Subscription, Rent, EMI, Insurance, Internet, Mobile Recharge, Electricity, Custom
        self.frequency = frequency # Daily, Weekly, Monthly, Quarterly, Half-Yearly, Yearly
        self.start_date = start_date # Format: YYYY-MM-DD
        self.next_due_date = next_due_date # Format: YYYY-MM-DD
        self.notes = notes
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "recurring_id": self.recurring_id,
            "uid": self.uid,
            "title": self.title,
            "amount": self.amount,
            "category": self.category,
            "frequency": self.frequency,
            "start_date": self.start_date,
            "next_due_date": self.next_due_date,
            "notes": self.notes,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            recurring_id=data.get("recurring_id"),
            uid=data.get("uid"),
            title=data.get("title"),
            amount=data.get("amount", 0.0),
            category=data.get("category", "Custom"),
            frequency=data.get("frequency", "Monthly"),
            start_date=data.get("start_date"),
            next_due_date=data.get("next_due_date"),
            notes=data.get("notes", ""),
            created_at=data.get("created_at")
        )
