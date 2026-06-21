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
                try:
                    target = float(g.get("target_amount") or 0.0)
                    current = float(g.get("current_amount") or 0.0)
                    progress = float(g.get("progress_percentage") or 0.0)
                    remaining = float(g.get("remaining_amount") or 0.0)
                    monthly_saving_needed = float(g.get("monthly_saving_needed") or 0.0)
                    
                    goal_item = {
                        "goal_name": g.get("goal_name") or "Unnamed Goal",
                        "target_amount": target,
                        "current_amount": current,
                        "progress_percentage": progress,
                        "remaining_amount": remaining,
                        "monthly_saving_needed": monthly_saving_needed,
                        "deadline": g.get("deadline") or ""
                    }

                    if progress >= 100.0:
                        goal_item["status"] = "Completed"
                        goal_item["prediction"] = "Completed! Goal achieved."
                        completed_goals_count += 1
                    else:
                        # Basic projection
                        deadline_str = g.get("deadline")
                        if not deadline_str:
                            goal_item["status"] = "Active"
                            goal_item["prediction"] = f"On track if you save ₹{monthly_saving_needed:.2f} per month."
                            on_track_count += 1
                        else:
                            try:
                                deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                                today = datetime.utcnow().date()
                                days_left = (deadline_date - today).days
                                
                                if days_left <= 0:
                                    goal_item["status"] = "Overdue"
                                    goal_item["prediction"] = "Deadline has passed. Need to revise goal deadline."
                                    behind_count += 1
                                else:
                                    goal_item["status"] = "Active"
                                    goal_item["prediction"] = f"On track if you save ₹{monthly_saving_needed:.2f} per month until the deadline."
                                    on_track_count += 1
                            except Exception:
                                goal_item["status"] = "Unknown"
                                goal_item["prediction"] = "Unable to estimate deadline status due to invalid date layout."
                    
                    goals_summary.append(goal_item)
                except Exception as inner_ex:
                    logger.error(f"Failed to process individual goal in agent analysis: {str(inner_ex)}")
                    continue

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
