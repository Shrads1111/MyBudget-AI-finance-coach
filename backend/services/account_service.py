import uuid
from datetime import datetime
from services.firebase_service import FirebaseService
from models.account_model import Account
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)

class AccountService:
    @staticmethod
    def get_collection():
        db = FirebaseService.get_db()
        return db.collection("accounts")

    @staticmethod
    def get_accounts(uid):
        try:
            query = AccountService.get_collection().where("uid", "==", uid)
            docs = query.stream()
            accounts = []
            for doc in docs:
                accounts.append(doc.to_dict())
            
            return accounts
        except Exception as e:
            logger.error(f"Firestore get accounts error: {str(e)}")
            raise APIError("Failed to fetch accounts", status_code=500)

    @staticmethod
    def create_account(uid, data):
        name = data.get("name")
        type = data.get("type", "Bank")
        initial_balance = float(data.get("initial_balance", 0.0))
        last_details = data.get("last_details", "")

        if not name:
            raise APIError("Account name is required", status_code=400)

        account_id = str(uuid.uuid4())
        acc = Account(
            account_id=account_id,
            uid=uid,
            name=name,
            type=type,
            initial_balance=initial_balance,
            last_details=last_details
        )

        try:
            AccountService.get_collection().document(account_id).set(acc.to_dict())
            logger.info(f"Account {account_id} created for user {uid}")
            return acc.to_dict()
        except Exception as e:
            logger.error(f"Firestore create account error: {str(e)}")
            raise APIError("Failed to create account", status_code=500)

    @staticmethod
    def delete_account(uid, account_id):
        try:
            doc_ref = AccountService.get_collection().document(account_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Account not found", status_code=404)
            
            acc_data = doc.to_dict()
            if acc_data.get("uid") != uid:
                raise APIError("Access denied", status_code=403)

            doc_ref.delete()
            logger.info(f"Account {account_id} deleted for user {uid}")
            return {"success": True, "message": "Account deleted successfully"}
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore delete account error: {str(e)}")
            raise APIError("Failed to delete account", status_code=500)
