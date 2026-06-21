import uuid
from datetime import datetime
from services.firebase_service import FirebaseService
from models.expense_model import Expense
from utils.validator import Validator
from middleware.error_handler import APIError
import logging

logger = logging.getLogger(__name__)

class ExpenseService:
    @staticmethod
    def get_collection():
        db = FirebaseService.get_db()
        return db.collection("expenses")

    @staticmethod
    def create_expense(uid, data):
        amount = Validator.validate_amount(data.get("amount"))
        category = Validator.validate_expense_category(data.get("category"))
        date = Validator.validate_date(data.get("date"))
        description = data.get("description", "")

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
            updated_at=created_at
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
            # Query base by uid to isolate data
            query = ExpenseService.get_collection().where("uid", "==", uid)
            docs = query.stream()
            
            expenses = []
            for doc in docs:
                expenses.append(doc.to_dict())
                
            # Filter in Python to avoid complex Firestore composite indices
            if category:
                expenses = [e for e in expenses if e["category"] == category]
            
            if month:
                # Expect month format: YYYY-MM
                expenses = [e for e in expenses if e["date"].startswith(month)]
                
            if year:
                # Expect year format: YYYY
                expenses = [e for e in expenses if e["date"].startswith(str(year))]

            # Sort
            reverse_sort = (sort_order.lower() == "desc")
            if sort_by in ["amount", "date", "created_at", "updated_at"]:
                expenses.sort(key=lambda x: x.get(sort_by), reverse=reverse_sort)
            else:
                expenses.sort(key=lambda x: x.get("date"), reverse=reverse_sort)

            # Paginate
            total_count = len(expenses)
            paginated_expenses = expenses[offset : offset + limit]

            return {
                "expenses": paginated_expenses,
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
