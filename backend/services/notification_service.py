import uuid
from datetime import datetime
# FirebaseService is imported lazily inside methods to avoid protobuf crash at import time.
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def get_collection():
        from services.firebase_service import FirebaseService
        db = FirebaseService.get_db()
        return db.collection("notifications")

    @staticmethod
    def create_notification(uid, title, message, category="General", severity="info"):
        """
        Creates a notification document in Firestore.
        Severity can be: info, warning, danger
        """
        notification_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        notification = {
            "notification_id": notification_id,
            "uid": uid,
            "title": title,
            "message": message,
            "category": category,
            "severity": severity,
            "read": False,
            "created_at": created_at
        }

        try:
            NotificationService.get_collection().document(notification_id).set(notification)
            logger.info(f"Notification created for {uid}: {title}")
            return notification
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            # Fail silently to not disrupt the main business transaction
            return None

    @staticmethod
    def get_notifications(uid, limit=20):
        try:
            docs = NotificationService.get_collection().where("uid", "==", uid).stream()
            notifications = [d.to_dict() for d in docs]
            notifications.sort(key=lambda x: x.get("created_at"), reverse=True)
            return notifications[:limit]
        except Exception as e:
            logger.error(f"Error fetching notifications: {str(e)}")
            return []

    @staticmethod
    def mark_as_read(uid, notification_id):
        try:
            doc_ref = NotificationService.get_collection().document(notification_id)
            doc = doc_ref.get()
            if not doc.exists or doc.to_dict().get("uid") != uid:
                return {"success": False, "message": "Notification not found or access denied"}
            doc_ref.update({"read": True})
            return {"success": True}
        except Exception as e:
            logger.error(f"Error updating notification: {str(e)}")
            return {"success": False, "message": str(e)}
