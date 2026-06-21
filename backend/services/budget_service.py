import uuid
# FirebaseService will be imported lazily in methods
from services.notification_service import NotificationService
from models.budget_model import Budget
from utils.validator import Validator
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)

class BudgetService:
    @staticmethod
    def get_collection():
        # Lazy import to avoid heavy Firebase import at module load
        from services.firebase_service import FirebaseService
        db = FirebaseService.get_db()
        return db.collection("budgets")

    @staticmethod
    def recalculate_spent(uid, category, month):
        """
        Dynamically computes the sum of expenses for this category and month,
        updates the budget doc spent amount, and triggers alerts if necessary.
        """
        try:
            from services.firebase_service import FirebaseService
            db = FirebaseService.get_db()
            expenses_ref = db.collection("expenses").where("uid", "==", uid).where("category", "==", category)
            expenses_docs = expenses_ref.stream()
            
            total_spent = 0.0
            for doc in expenses_docs:
                exp_data = doc.to_dict()
                # Check if expense belongs to the specific month (format YYYY-MM)
                if exp_data.get("date", "").startswith(month):
                    total_spent += float(exp_data.get("amount", 0.0))

            return total_spent
        except Exception as e:
            logger.error(f"Error recalculating budget spent: {str(e)}")
            return 0.0

    @staticmethod
    def check_and_trigger_alerts(uid, budget_data):
        limit = budget_data.get("limit", 0.0)
        spent = budget_data.get("spent", 0.0)
        category = budget_data.get("category")
        month = budget_data.get("month")
        
        if limit <= 0:
            return

        percentage = (spent / limit) * 100.0
        
        # Determine the severity and title
        title = None
        message = None
        severity = "info"
        
        if percentage >= 100.0:
            title = f"Budget Exhausted - {category}"
            message = f"You have exhausted 100% or more of your budget limit (₹{limit}) for {category} in {month}. Current spending: ₹{spent}."
            severity = "danger"
        elif percentage >= 90.0:
            title = f"Budget Alert (90%) - {category}"
            message = f"You have used 90% or more of your budget limit (₹{limit}) for {category} in {month}. Current spending: ₹{spent}."
            severity = "warning"
        elif percentage >= 80.0:
            title = f"Budget Alert (80%) - {category}"
            message = f"You have used 80% or more of your budget limit (₹{limit}) for {category} in {month}. Current spending: ₹{spent}."
            severity = "warning"

        if title and message:
            # Check if this alert has already been raised in the notifications log
            # to avoid duplicate notifications on every page load
            try:
                from services.firebase_service import FirebaseService
                db = FirebaseService.get_db()
                existing_alerts = db.collection("notifications") \
                    .where("uid", "==", uid) \
                    .where("title", "==", title) \
                    .stream()
                
                # Check if one was sent for this month
                already_sent = False
                for alert in existing_alerts:
                    alert_data = alert.to_dict()
                    # If notification message has the month context or was created recently
                    if month in alert_data.get("message", ""):
                        already_sent = True
                        break
                
                if not already_sent:
                    NotificationService.create_notification(
                        uid=uid,
                        title=title,
                        message=message,
                        category="Budget",
                        severity=severity
                    )
            except Exception as e:
                logger.error(f"Error checking existing alerts: {str(e)}")

    @staticmethod
    def create_budget(uid, data):
        category = Validator.validate_budget_category(data.get("category"))
        limit = Validator.validate_limit(data.get("limit"))
        month = Validator.validate_budget_month(data.get("month")) # YYYY-MM

        # Check if budget already exists for this category/month
        existing_ref = BudgetService.get_collection() \
            .where("uid", "==", uid) \
            .where("category", "==", category) \
            .where("month", "==", month) \
            .stream()
        
        if list(existing_ref):
            raise APIError(f"A budget for category '{category}' in month '{month}' already exists", status_code=400)

        budget_id = str(uuid.uuid4())
        spent = BudgetService.recalculate_spent(uid, category, month)

        budget = Budget(
            budget_id=budget_id,
            uid=uid,
            category=category,
            limit=limit,
            month=month,
            spent=spent
        )
        
        budget_dict = budget.to_dict()
        
        try:
            BudgetService.get_collection().document(budget_id).set(budget_dict)
            logger.info(f"Budget {budget_id} created for user {uid}")
            BudgetService.check_and_trigger_alerts(uid, budget_dict)
            return budget_dict
        except Exception as e:
            logger.error(f"Firestore save error: {str(e)}")
            raise APIError("Failed to save budget to database", status_code=500)

    @staticmethod
    def get_budgets(uid):
        try:
            docs = BudgetService.get_collection().where("uid", "==", uid).stream()
            budgets = []
            
            for doc in docs:
                b_data = doc.to_dict()
                # Dynamically sync/recalculate spent
                spent = BudgetService.recalculate_spent(uid, b_data["category"], b_data["month"])
                if spent != b_data.get("spent", 0.0):
                    b_data["spent"] = spent
                    BudgetService.get_collection().document(b_data["budget_id"]).update({"spent": spent})
                
                # Re-calculate remaining property in dictionary
                b_data["remaining"] = max(0.0, b_data["limit"] - spent)
                
                # Check and raise alerts
                BudgetService.check_and_trigger_alerts(uid, b_data)
                budgets.append(b_data)
                
            return budgets
        except Exception as e:
            logger.error(f"Firestore get error: {str(e)}")
            raise APIError("Failed to fetch budgets", status_code=500)

    @staticmethod
    def get_budget_by_id(uid, budget_id):
        try:
            doc_ref = BudgetService.get_collection().document(budget_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Budget not found", status_code=404)
            
            b_data = doc.to_dict()
            if b_data.get("uid") != uid:
                raise APIError("Access denied", status_code=403)

            # Sync spent
            spent = BudgetService.recalculate_spent(uid, b_data["category"], b_data["month"])
            if spent != b_data.get("spent", 0.0):
                b_data["spent"] = spent
                doc_ref.update({"spent": spent})
            
            b_data["remaining"] = max(0.0, b_data["limit"] - spent)
            
            BudgetService.check_and_trigger_alerts(uid, b_data)
            return b_data
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore error: {str(e)}")
            raise APIError("Failed to fetch budget details", status_code=500)

    @staticmethod
    def update_budget(uid, budget_id, data):
        # Validate existence & ownership
        budget_data = BudgetService.get_budget_by_id(uid, budget_id)

        updates = {}
        if "limit" in data:
            updates["limit"] = Validator.validate_limit(data["limit"])
            
        if not updates:
            return budget_data

        try:
            doc_ref = BudgetService.get_collection().document(budget_id)
            doc_ref.update(updates)
            logger.info(f"Budget {budget_id} updated for user {uid}")
            budget_data.update(updates)
            
            # Recalculate remaining
            budget_data["remaining"] = max(0.0, budget_data["limit"] - budget_data["spent"])
            BudgetService.check_and_trigger_alerts(uid, budget_data)
            
            return budget_data
        except Exception as e:
            logger.error(f"Firestore update error: {str(e)}")
            raise APIError("Failed to update budget", status_code=500)

    @staticmethod
    def delete_budget(uid, budget_id):
        # Validate existence & ownership
        BudgetService.get_budget_by_id(uid, budget_id)

        try:
            doc_ref = BudgetService.get_collection().document(budget_id)
            doc_ref.delete()
            logger.info(f"Budget {budget_id} deleted for user {uid}")
            return {"success": True, "message": "Budget deleted successfully"}
        except Exception as e:
            logger.error(f"Firestore delete error: {str(e)}")
            raise APIError("Failed to delete budget", status_code=500)

    @staticmethod
    def get_alerts(uid):
        """Returns all budgets that have triggered alerts (above 80% utilization)"""
        budgets = BudgetService.get_budgets(uid)
        alerts = []
        for b in budgets:
            pct = (b["spent"] / b["limit"]) * 100.0 if b["limit"] > 0 else 0
            if pct >= 80:
                alerts.append({
                    "budget_id": b["budget_id"],
                    "category": b["category"],
                    "limit": b["limit"],
                    "spent": b["spent"],
                    "percentage": round(pct, 2),
                    "remaining": b["remaining"],
                    "severity": "danger" if pct >= 100 else "warning"
                })
        return alerts
