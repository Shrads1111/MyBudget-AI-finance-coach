from datetime import datetime
import math

class SavingsGoal:
    def __init__(self, goal_id, uid, goal_name, target_amount, current_amount, deadline):
        self.goal_id = goal_id
        self.uid = uid
        self.goal_name = goal_name
        self.target_amount = float(target_amount)
        self.current_amount = float(current_amount)
        self.deadline = deadline # Format YYYY-MM-DD

    @property
    def progress_percentage(self):
        if self.target_amount <= 0:
            return 100.0
        return min(100.0, round((self.current_amount / self.target_amount) * 100.0, 2))

    @property
    def remaining_amount(self):
        return max(0.0, self.target_amount - self.current_amount)

    def get_monthly_saving_needed(self):
        """Calculates savings required monthly to reach target by deadline"""
        remaining = self.remaining_amount
        if remaining <= 0:
            return 0.0
        try:
            deadline_date = datetime.strptime(self.deadline, "%Y-%m-%d").date()
            today = datetime.utcnow().date()
            
            # Compute difference in months
            months_diff = (deadline_date.year - today.year) * 12 + (deadline_date.month - today.month)
            if months_diff <= 0:
                # Goal is in the current month or past, standard calculation
                return remaining
            return round(remaining / months_diff, 2)
        except Exception:
            return remaining

    def to_dict(self):
        return {
            "goal_id": self.goal_id,
            "uid": self.uid,
            "goal_name": self.goal_name,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "deadline": self.deadline,
            "progress_percentage": self.progress_percentage,
            "remaining_amount": self.remaining_amount,
            "monthly_saving_needed": self.get_monthly_saving_needed()
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            goal_id=data.get("goal_id"),
            uid=data.get("uid"),
            goal_name=data.get("goal_name"),
            target_amount=data.get("target_amount", 0.0),
            current_amount=data.get("current_amount", 0.0),
            deadline=data.get("deadline")
        )
