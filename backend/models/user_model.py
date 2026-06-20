from datetime import datetime

class User:
    def __init__(self, uid, email, display_name=None, created_at=None, updated_at=None):
        self.uid = uid
        self.email = email
        self.display_name = display_name or ""
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "uid": self.uid,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            uid=data.get("uid"),
            email=data.get("email"),
            display_name=data.get("display_name"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
