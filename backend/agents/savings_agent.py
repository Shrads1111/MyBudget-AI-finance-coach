from services.savings_service import SavingsService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SavingsAgent:
    @staticmethod
    def analyze(uid):
        """
        Analyze savings goal progress and predict completion outcomes.
        """
        try:
            goals = SavingsService.get_goals(uid)
            
            if not goals:
                return {
                    "agent": "Savings Agent",
                    "status": "No goals set",
                    "goals_summary": [],
                    "findings": "No savings goals are configured. Setting up a savings goal keeps you motivated."
                }

            goals_summary = []
            completed_goals_count = 0
            on_track_count = 0
            behind_count = 0

            for g in goals:
                target = float(g["target_amount"])
                current = float(g["current_amount"])
                progress = float(g["progress_percentage"])
                remaining = float(g["remaining_amount"])
                monthly_saving_needed = float(g["monthly_saving_needed"])
                
                goal_item = {
                    "goal_name": g["goal_name"],
                    "target_amount": target,
                    "current_amount": current,
                    "progress_percentage": progress,
                    "remaining_amount": remaining,
                    "monthly_saving_needed": monthly_saving_needed,
                    "deadline": g["deadline"]
                }

                if progress >= 100.0:
                    goal_item["status"] = "Completed"
                    goal_item["prediction"] = "Completed! Goal achieved."
                    completed_goals_count += 1
                else:
                    # Basic projection
                    try:
                        deadline_date = datetime.strptime(g["deadline"], "%Y-%m-%d").date()
                        today = datetime.utcnow().date()
                        days_left = (deadline_date - today).days
                        
                        if days_left <= 0:
                            goal_item["status"] = "Overdue"
                            goal_item["prediction"] = "Deadline has passed. Need to revise goal deadline."
                            behind_count += 1
                        else:
                            # Assume active savings rate is based on current/days since creation
                            # (Simplification: if they have saved some amount already, we assume a basic trend,
                            # otherwise we warn that they need to save monthly_saving_needed)
                            goal_item["status"] = "Active"
                            goal_item["prediction"] = f"On track if you save ₹{monthly_saving_needed:.2f} per month until the deadline."
                            on_track_count += 1
                    except Exception:
                        goal_item["status"] = "Unknown"
                        goal_item["prediction"] = "Unable to estimate deadline status due to invalid date layout."
                
                goals_summary.append(goal_item)

            findings = f"You have {len(goals)} active savings goals. {completed_goals_count} completed, {on_track_count} on track."

            return {
                "agent": "Savings Agent",
                "status": "Success",
                "goals_summary": goals_summary,
                "completed_goals_count": completed_goals_count,
                "active_goals_count": len(goals) - completed_goals_count,
                "findings": findings
            }
        except Exception as e:
            logger.error(f"SavingsAgent error: {str(e)}")
            return {
                "agent": "Savings Agent",
                "status": "Error",
                "error_message": str(e)
            }
