import uuid
from datetime import datetime
from services.firebase_service import FirebaseService
from services.notification_service import NotificationService
from models.goal_model import SavingsGoal
from utils.validator import Validator
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)

class SavingsService:
    @staticmethod
    def get_collection():
        db = FirebaseService.get_db()
        return db.collection("savings_goals")

    @staticmethod
    def check_and_trigger_goal_notifications(uid, goal_data):
        target = goal_data.get("target_amount", 0.0)
        current = goal_data.get("current_amount", 0.0)
        name = goal_data.get("goal_name")
        deadline = goal_data.get("deadline")
        
        if target <= 0:
            return

        # Check completed
        if current >= target:
            title = f"Goal Completed! 🎉"
            message = f"Congratulations! You have achieved your savings goal '{name}' by saving ₹{current} of your ₹{target} target!"
            try:
                db = FirebaseService.get_db()
                existing = db.collection("notifications") \
                    .where("uid", "==", uid) \
                    .where("title", "==", title) \
                    .stream()
                
                already_notified = False
                for n in existing:
                    if name in n.to_dict().get("message", ""):
                        already_notified = True
                        break
                
                if not already_notified:
                    NotificationService.create_notification(
                        uid=uid,
                        title=title,
                        message=message,
                        category="Goal",
                        severity="info"
                    )
            except Exception as e:
                logger.error(f"Error checking completion alert: {str(e)}")

        # Check nearing deadline
        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
            today = datetime.utcnow().date()
            days_left = (deadline_date - today).days
            
            if 0 < days_left <= 30 and current < target:
                title = f"Goal Deadline Nearing"
                message = f"Your goal '{name}' is due in {days_left} days on {deadline}. You need ₹{target - current} more to complete it."
                
                db = FirebaseService.get_db()
                existing = db.collection("notifications") \
                    .where("uid", "==", uid) \
                    .where("title", "==", title) \
                    .stream()
                
                already_notified = False
                for n in existing:
                    if name in n.to_dict().get("message", ""):
                        already_notified = True
                        break
                        
                if not already_notified:
                    NotificationService.create_notification(
                        uid=uid,
                        title=title,
                        message=message,
                        category="Goal",
                        severity="warning"
                    )
        except Exception as e:
            logger.error(f"Error checking goal deadline alert: {str(e)}")

    @staticmethod
    def create_goal(uid, data):
        name = data.get("goal_name")
        if not name:
            raise APIError("goal_name is required", status_code=400)
            
        target_amount = Validator.validate_amount(data.get("target_amount"), "target_amount")
        current_amount = Validator.validate_amount(data.get("current_amount", 0.0), "current_amount")
        deadline = Validator.validate_date(data.get("deadline"), "deadline")

        goal_id = str(uuid.uuid4())

        goal = SavingsGoal(
            goal_id=goal_id,
            uid=uid,
            goal_name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            deadline=deadline
        )
        
        goal_dict = goal.to_dict()

        try:
            SavingsService.get_collection().document(goal_id).set(goal_dict)
            logger.info(f"Savings goal {goal_id} created for user {uid}")
            SavingsService.check_and_trigger_goal_notifications(uid, goal_dict)
            return goal_dict
        except Exception as e:
            logger.error(f"Firestore save error: {str(e)}")
            raise APIError("Failed to save savings goal", status_code=500)

    @staticmethod
    def get_goals(uid):
        try:
            docs = SavingsService.get_collection().where("uid", "==", uid).stream()
            goals = []
            for doc in docs:
                g_data = doc.to_dict()
                
                # Re-calculate read properties dynamically and apply model defaults
                goal_obj = SavingsGoal.from_dict(g_data)
                g_data = goal_obj.to_dict()
                
                SavingsService.check_and_trigger_goal_notifications(uid, g_data)
                goals.append(g_data)
            return goals
        except Exception as e:
            logger.error(f"Firestore get error: {str(e)}")
            raise APIError("Failed to fetch savings goals", status_code=500)

    @staticmethod
    def get_goal_by_id(uid, goal_id):
        try:
            doc_ref = SavingsService.get_collection().document(goal_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Savings goal not found", status_code=404)
            
            g_data = doc.to_dict()
            if g_data.get("uid") != uid:
                raise APIError("Access denied", status_code=403)
            
            # Apply model defaults and calculate properties
            goal_obj = SavingsGoal.from_dict(g_data)
            g_data = goal_obj.to_dict()
            
            SavingsService.check_and_trigger_goal_notifications(uid, g_data)
            return g_data
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore error: {str(e)}")
            raise APIError("Failed to fetch savings goal details", status_code=500)

    @staticmethod
    def update_goal(uid, goal_id, data):
        # Validate existence & ownership
        goal_data = SavingsService.get_goal_by_id(uid, goal_id)

        updates = {}
        if "goal_name" in data:
            updates["goal_name"] = data["goal_name"]
        if "target_amount" in data:
            updates["target_amount"] = Validator.validate_amount(data["target_amount"], "target_amount")
        if "current_amount" in data:
            updates["current_amount"] = Validator.validate_amount(data["current_amount"], "current_amount")
        if "deadline" in data:
            updates["deadline"] = Validator.validate_date(data["deadline"], "deadline")
            
        if not updates:
            return goal_data

        try:
            doc_ref = SavingsService.get_collection().document(goal_id)
            doc_ref.update(updates)
            logger.info(f"Savings goal {goal_id} updated for user {uid}")
            goal_data.update(updates)
            
            # Recalculate
            goal_obj = SavingsGoal.from_dict(goal_data)
            goal_data["progress_percentage"] = goal_obj.progress_percentage
            goal_data["remaining_amount"] = goal_obj.remaining_amount
            goal_data["monthly_saving_needed"] = goal_obj.get_monthly_saving_needed()
            
            SavingsService.check_and_trigger_goal_notifications(uid, goal_data)
            
            return goal_data
        except Exception as e:
            logger.error(f"Firestore update error: {str(e)}")
            raise APIError("Failed to update savings goal", status_code=500)

    @staticmethod
    def delete_goal(uid, goal_id):
        # Validate existence & ownership
        SavingsService.get_goal_by_id(uid, goal_id)

        try:
            doc_ref = SavingsService.get_collection().document(goal_id)
            doc_ref.delete()
            logger.info(f"Savings goal {goal_id} deleted for user {uid}")
            return {"success": True, "message": "Savings goal deleted successfully"}
        except Exception as e:
            logger.error(f"Firestore delete error: {str(e)}")
            raise APIError("Failed to delete savings goal", status_code=500)
