import uuid
from datetime import datetime
# FirebaseService is imported lazily inside methods to avoid protobuf crash at import time.
from utils.constants import EXPENSE_CATEGORIES
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)


class CategoryService:
    @staticmethod
    def get_collection():
        from services.firebase_service import FirebaseService
        db = FirebaseService.get_db()
        return db.collection("user_categories")

    @staticmethod
    def get_categories(uid):
        """
        Returns a merged list of default categories + user's custom categories.
        Custom categories are fetched from Firestore user_categories collection
        and are scoped strictly to the given uid.
        """
        try:
            query = CategoryService.get_collection().where("userId", "==", uid)
            docs = query.stream()

            custom_names = []
            for doc in docs:
                data = doc.to_dict()
                name = data.get("name", "").strip()
                if name and name not in EXPENSE_CATEGORIES and name not in custom_names:
                    custom_names.append(name)

            # Default categories always come first (minus "Other" — moved to end)
            defaults_without_other = [c for c in EXPENSE_CATEGORIES if c != "Other"]
            result = defaults_without_other + sorted(custom_names) + ["Other"]

            return result
        except Exception as e:
            logger.error(f"Error fetching categories for user {uid}: {str(e)}")
            raise APIError("Failed to fetch categories", status_code=500)

    @staticmethod
    def add_category(uid, name):
        """
        Adds a new custom category for the given user.
        Silently skips if the category already exists (default or user's own custom).
        Returns the full updated category list.
        """
        if not name or not name.strip():
            raise APIError("Category name is required", status_code=400)

        name = name.strip()

        # Prevent duplicates against default list (case-insensitive)
        if name.lower() in [c.lower() for c in EXPENSE_CATEGORIES]:
            return CategoryService.get_categories(uid)

        # Prevent duplicates against user's existing custom categories
        try:
            query = (
                CategoryService.get_collection()
                .where("userId", "==", uid)
                .where("name", "==", name)
            )
            existing = list(query.stream())
            if existing:
                # Already exists — return current list without error
                return CategoryService.get_categories(uid)

            cat_id = str(uuid.uuid4())
            doc = {
                "id": cat_id,
                "userId": uid,
                "name": name,
                "createdAt": datetime.utcnow().isoformat()
            }
            CategoryService.get_collection().document(cat_id).set(doc)
            logger.info(f"Custom category '{name}' created for user {uid}")
            return CategoryService.get_categories(uid)
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Error creating category for user {uid}: {str(e)}")
            raise APIError("Failed to save custom category", status_code=500)
