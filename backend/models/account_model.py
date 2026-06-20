from datetime import datetime

class Account:
    def __init__(self, account_id, uid, name, type, initial_balance, last_details, created_at=None):
        self.account_id = account_id
        self.uid = uid
        self.name = name
        self.type = type # Bank, Wallet, Card
        self.initial_balance = float(initial_balance)
        self.last_details = last_details # e.g. "•••• 4521"
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "account_id": self.account_id,
            "uid": self.uid,
            "name": self.name,
            "type": self.type,
            "initial_balance": self.initial_balance,
            "last_details": self.last_details,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            account_id=data.get("account_id"),
            uid=data.get("uid"),
            name=data.get("name"),
            type=data.get("type"),
            initial_balance=data.get("initial_balance", 0.0),
            last_details=data.get("last_details"),
            created_at=data.get("created_at")
        )
