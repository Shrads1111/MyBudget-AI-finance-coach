import uuid
from datetime import datetime, date, timedelta
import calendar
import logging
# FirebaseService will be imported lazily in methods
from models.recurring_model import RecurringPayment
from services.expense_service import ExpenseService
from utils.validator import Validator
from middleware.error_handler import APIError

logger = logging.getLogger(__name__)

def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def calculate_next_due_date(current_due_date_str, frequency):
    try:
        current_date = datetime.strptime(current_due_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise APIError("next_due_date must be in YYYY-MM-DD format", status_code=400)
        
    freq_lower = frequency.lower()
    if freq_lower == "daily":
        next_date = current_date + timedelta(days=1)
    elif freq_lower == "weekly":
        next_date = current_date + timedelta(weeks=1)
    elif freq_lower == "monthly":
        next_date = add_months(current_date, 1)
    elif freq_lower == "quarterly":
        next_date = add_months(current_date, 3)
    elif freq_lower == "half-yearly":
        next_date = add_months(current_date, 6)
    elif freq_lower == "yearly":
        next_date = add_months(current_date, 12)
    else:
        # Default or fallback, say 1 month
        next_date = add_months(current_date, 1)
    return next_date.strftime("%Y-%m-%d")

class RecurringService:
    @staticmethod
    def get_collection():
        # Lazy import to avoid import-time failures
        from services.firebase_service import FirebaseService
        db = FirebaseService.get_db()
        return db.collection("recurring_payments")

    @staticmethod
    def create_recurring(uid, data):
        title = data.get("title")
        if not title or not str(title).strip():
            raise APIError("title is required", status_code=400)
            
        amount = Validator.validate_amount(data.get("amount"))
        category = data.get("category", "Custom")
        frequency = data.get("frequency", "Monthly")
        
        start_date = Validator.validate_date(data.get("start_date"), "start_date")
        next_due_date = Validator.validate_date(data.get("next_due_date"), "next_due_date")
        notes = data.get("notes", "")
        
        recurring_id = data.get("recurring_id") or str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        recurring_payment = RecurringPayment(
            recurring_id=recurring_id,
            uid=uid,
            title=title.strip(),
            amount=amount,
            category=category,
            frequency=frequency,
            start_date=start_date,
            next_due_date=next_due_date,
            notes=notes,
            created_at=created_at
        )
        
        try:
            RecurringService.get_collection().document(recurring_id).set(recurring_payment.to_dict())
            logger.info(f"Recurring payment {recurring_id} created for user {uid}")
            return recurring_payment.to_dict()
        except Exception as e:
            logger.error(f"Firestore save error in recurring payments: {str(e)}")
            raise APIError("Failed to save recurring payment to database", status_code=500)

    @staticmethod
    def get_recurring(uid):
        try:
            query = RecurringService.get_collection().where("uid", "==", uid)
            docs = query.stream()
            payments = []
            for doc in docs:
                payments.append(doc.to_dict())
            return payments
        except Exception as e:
            logger.error(f"Firestore get error in recurring payments: {str(e)}")
            raise APIError("Failed to fetch recurring payments", status_code=500)

    @staticmethod
    def get_recurring_by_id(uid, recurring_id):
        try:
            doc_ref = RecurringService.get_collection().document(recurring_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Recurring payment not found", status_code=404)
            payment_data = doc.to_dict()
            if payment_data.get("uid") != uid:
                raise APIError("Access denied", status_code=403)
            return payment_data
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore error in recurring: {str(e)}")
            raise APIError("Failed to fetch recurring payment details", status_code=500)

    @staticmethod
    def update_recurring(uid, recurring_id, data):
        # Retrieve original
        payment_data = RecurringService.get_recurring_by_id(uid, recurring_id)

        updates = {}
        if "title" in data:
            title = data["title"]
            if not title or not str(title).strip():
                raise APIError("title is required", status_code=400)
            updates["title"] = str(title).strip()
            
        if "amount" in data:
            updates["amount"] = Validator.validate_amount(data["amount"])
            
        if "category" in data:
            updates["category"] = data["category"]
            
        if "frequency" in data:
            updates["frequency"] = data["frequency"]
            
        if "start_date" in data:
            updates["start_date"] = Validator.validate_date(data["start_date"], "start_date")
            
        if "next_due_date" in data:
            updates["next_due_date"] = Validator.validate_date(data["next_due_date"], "next_due_date")
            
        if "notes" in data:
            updates["notes"] = data["notes"]

        if not updates:
            return payment_data

        try:
            doc_ref = RecurringService.get_collection().document(recurring_id)
            doc_ref.update(updates)
            logger.info(f"Recurring payment {recurring_id} updated for user {uid}")
            payment_data.update(updates)
            return payment_data
        except Exception as e:
            logger.error(f"Firestore update error in recurring: {str(e)}")
            raise APIError("Failed to update recurring payment", status_code=500)

    @staticmethod
    def delete_recurring(uid, recurring_id):
        # Validate existence & ownership
        RecurringService.get_recurring_by_id(uid, recurring_id)

        try:
            doc_ref = RecurringService.get_collection().document(recurring_id)
            doc_ref.delete()
            logger.info(f"Recurring payment {recurring_id} deleted for user {uid}")
            return {"success": True, "message": "Recurring payment deleted successfully"}
        except Exception as e:
            logger.error(f"Firestore delete error in recurring: {str(e)}")
            raise APIError("Failed to delete recurring payment", status_code=500)

    @staticmethod
    def mark_as_paid(uid, recurring_id):
        # Retrieve original
        payment_data = RecurringService.get_recurring_by_id(uid, recurring_id)
        
        current_due = payment_data.get("next_due_date")
        frequency = payment_data.get("frequency", "Monthly")
        
        # 1. Calculate next due date
        next_due = calculate_next_due_date(current_due, frequency)
        
        # 2. Map category to Expense category
        category = payment_data.get("category", "Custom")
        expense_category = "Bills"
        
        # Custom mapping based on requirements
        category_mapping = {
            "SIP": "Other",
            "Mutual Fund": "Other",
            "PPF": "Other",
            "RD": "Other",
            "Subscription": "Subscriptions",
            "Rent": "Bills",
            "EMI": "Bills",
            "Insurance": "Bills",
            "Internet": "Bills",
            "Mobile Recharge": "Bills",
            "Electricity": "Bills",
            "Food": "Food",
            "Transport": "Transport",
            "Entertainment": "Entertainment",
            "Education": "Education",
        }
        
        if category in category_mapping:
            expense_category = category_mapping[category]
        elif category in ["Food", "Transport", "Subscriptions", "Entertainment", "Education", "Bills", "Other"]:
            expense_category = category
            
        # 3. Create expense log
        expense_data = {
            "amount": payment_data.get("amount"),
            "category": expense_category,
            "date": current_due, # Record the expense on the date it was due (or current_due)
            "description": f"Paid recurring commitment: {payment_data.get('title')} ({category})"
        }
        
        # Call ExpenseService to log the payment as a regular expense
        created_expense = ExpenseService.create_expense(uid, expense_data)
        
        # 4. Update the next due date in Firestore
        updates = {
            "next_due_date": next_due
        }
        
        try:
            doc_ref = RecurringService.get_collection().document(recurring_id)
            doc_ref.update(updates)
            logger.info(f"Recurring payment {recurring_id} marked as paid. Next due is {next_due}.")
            
            payment_data.update(updates)
            return {
                "success": True,
                "message": "Payment marked as paid and expense logged",
                "next_due_date": next_due,
                "expense": created_expense,
                "recurring_payment": payment_data
            }
        except Exception as e:
            logger.error(f"Firestore update error in mark_as_paid: {str(e)}")
            raise APIError("Failed to update recurring payment due date", status_code=500)
