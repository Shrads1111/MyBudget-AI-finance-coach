import uuid
from datetime import datetime
# FirebaseService will be imported lazily in methods
from models.expense_model import Expense
from utils.validator import Validator
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)

class ExpenseService:
    @staticmethod
    def get_collection():
        # Lazy import to avoid heavy FirebaseAdmin import at module load
        from services.firebase_service import FirebaseService
        db = FirebaseService.get_db()
        return db.collection("expenses")

    @staticmethod
    def create_expense(uid, data):
        amount = Validator.validate_amount(data.get("amount"))
        category = Validator.validate_expense_category(data.get("category"))
        date = Validator.validate_date(data.get("date"))
        description = data.get("description", "")
        account_id = data.get("account_id")
        type_val = data.get("type")

        expense_id = data.get("expense_id") or str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        expense = Expense(
            expense_id=expense_id,
            uid=uid,
            amount=amount,
            category=category,
            description=description,
            date=date,
            created_at=created_at,
            updated_at=created_at,
            account_id=account_id,
            type=type_val
        )

        try:
            ExpenseService.get_collection().document(expense_id).set(expense.to_dict())
            logger.info(f"Expense {expense_id} created for user {uid}")
            return expense.to_dict()
        except Exception as e:
            logger.error(f"Firestore save error: {str(e)}")
            raise APIError("Failed to save expense to database", status_code=500)

    @staticmethod
    def get_expenses(uid, category=None, month=None, year=None, sort_by="date", sort_order="desc", limit=10, offset=0):
        try:
            query = ExpenseService.get_collection().where("uid", "==", uid)
            
            if category:
                query = query.where("category", "==", category)
            
            if month:
                # Expect month format: YYYY-MM
                query = query.where("date", ">=", month).where("date", "<=", month + "\uf8ff")
            elif year:
                # Expect year format: YYYY
                query = query.where("date", ">=", str(year)).where("date", "<=", str(year) + "\uf8ff")

            # Determine sorting order
            direction = "DESCENDING" if sort_order.lower() == "desc" else "ASCENDING"
            
            # Firestore inequality filter rules: first sort by inequality field ("date")
            if (month or year) and sort_by != "date":
                query = query.order_by("date", direction=direction).order_by(sort_by, direction=direction)
            else:
                query = query.order_by(sort_by, direction=direction)

            # Get total count (using select([]) to avoid loading document fields)
            total_count = len(list(query.select([]).stream()))

            # Paginate natively
            paginated_query = query.offset(offset).limit(limit)
            docs = paginated_query.stream()
            
            expenses = []
            for doc in docs:
                expenses.append(doc.to_dict())

            return {
                "expenses": expenses,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"Firestore get error: {str(e)}")
            raise APIError("Failed to fetch expenses", status_code=500)

    @staticmethod
    def get_expense_by_id(uid, expense_id):
        try:
            doc_ref = ExpenseService.get_collection().document(expense_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Expense not found", status_code=404)
            
            expense_data = doc.to_dict()
            if expense_data.get("uid") != uid:
                raise APIError("Access denied", status_code=403)
                
            return expense_data
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore error: {str(e)}")
            raise APIError("Failed to fetch expense details", status_code=500)

    @staticmethod
    def update_expense(uid, expense_id, data):
        # Retrieve original
        expense_data = ExpenseService.get_expense_by_id(uid, expense_id)

        # Validate updates
        updates = {}
        if "amount" in data:
            updates["amount"] = Validator.validate_amount(data["amount"])
        if "category" in data:
            updates["category"] = Validator.validate_expense_category(data["category"])
        if "date" in data:
            updates["date"] = Validator.validate_date(data["date"])
        if "description" in data:
            updates["description"] = data["description"]
        if "account_id" in data:
            updates["account_id"] = data["account_id"]
        if "type" in data:
            updates["type"] = data["type"]
            
        if not updates:
            return expense_data

        updates["updated_at"] = datetime.utcnow().isoformat()

        try:
            doc_ref = ExpenseService.get_collection().document(expense_id)
            doc_ref.update(updates)
            logger.info(f"Expense {expense_id} updated for user {uid}")
            expense_data.update(updates)
            return expense_data
        except Exception as e:
            logger.error(f"Firestore update error: {str(e)}")
            raise APIError("Failed to update expense", status_code=500)

    @staticmethod
    def delete_expense(uid, expense_id):
        # Validate existence & ownership
        ExpenseService.get_expense_by_id(uid, expense_id)

        try:
            doc_ref = ExpenseService.get_collection().document(expense_id)
            doc_ref.delete()
            logger.info(f"Expense {expense_id} deleted for user {uid}")
            return {"success": True, "message": "Expense deleted successfully"}
        except Exception as e:
            logger.error(f"Firestore delete error: {str(e)}")
            raise APIError("Failed to delete expense", status_code=500)
