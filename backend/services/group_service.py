import uuid
from datetime import datetime
from services.firebase_service import FirebaseService
from middleware.error_handler import APIError
from utils.validator import Validator
import logging


logger = logging.getLogger(__name__)

class GroupService:
    @staticmethod
    def get_collection():
        db = FirebaseService.get_db()
        return db.collection("group_budgets")

    @staticmethod
    def get_user_groups(uid):
        try:
            docs = GroupService.get_collection().where("members", "array_contains", uid).stream()
            groups = []
            for doc in docs:
                groups.append(doc.to_dict())
            return groups
        except Exception as e:
            logger.error(f"Firestore query error: {str(e)}")
            raise APIError("Failed to fetch user groups", status_code=500)

    @staticmethod
    def create_group(uid, name, members=None):

        if not name:
            raise APIError("group_name is required", status_code=400)
            
        group_id = str(uuid.uuid4())
        
        # Ensure the creator is in the members list
        member_list = members or []
        if uid not in member_list:
            member_list.append(uid)

        group_data = {
            "group_id": group_id,
            "group_name": name,
            "created_by": uid,
            "members": member_list,
            "expenses": [] # Array of dicts
        }

        try:
            GroupService.get_collection().document(group_id).set(group_data)
            logger.info(f"Group {group_id} created by user {uid}")
            return group_data
        except Exception as e:
            logger.error(f"Firestore save error: {str(e)}")
            raise APIError("Failed to create group", status_code=500)

    @staticmethod
    def invite_member(uid, group_id, member_email_or_uid):
        if not member_email_or_uid:
            raise APIError("member is required", status_code=400)

        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            # Verify requesting user is currently a member
            if uid not in group_data.get("members", []):
                raise APIError("Access denied", status_code=403)

            current_members = list(group_data.get("members", []))
            if member_email_or_uid in current_members:
                raise APIError("User is already a member of this group", status_code=400)

            current_members.append(member_email_or_uid)
            doc_ref.update({"members": current_members})
            
            logger.info(f"User {member_email_or_uid} added to group {group_id}")
            group_data["members"] = current_members
            return group_data
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore update error: {str(e)}")
            raise APIError("Failed to add member to group", status_code=500)

    @staticmethod
    def add_expense(uid, group_id, expense_data):
        amount = Validator.validate_amount(expense_data.get("amount"))
        description = expense_data.get("description")
        if not description:
            raise APIError("description is required", status_code=400)
            
        paid_by = expense_data.get("paid_by", uid)
        date = expense_data.get("date", datetime.utcnow().date().isoformat())

        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            members = group_data.get("members", [])
            
            if uid not in members:
                raise APIError("Access denied", status_code=403)
                
            if paid_by not in members:
                raise APIError(f"Paying user '{paid_by}' must be a member of the group", status_code=400)

            # Define split members list
            split_with = expense_data.get("split_with")
            if not split_with:
                # Default to split among all members
                split_with = list(members)
            else:
                # Validate split_with members exist in group
                for m in split_with:
                    if m not in members:
                        raise APIError(f"Split user '{m}' must be a member of the group", status_code=400)

            new_expense = {
                "expense_id": str(uuid.uuid4()),
                "amount": float(amount),
                "description": description,
                "paid_by": paid_by,
                "date": date,
                "split_with": split_with
            }

            current_expenses = list(group_data.get("expenses", []))
            current_expenses.append(new_expense)
            
            doc_ref.update({"expenses": current_expenses})
            logger.info(f"Group expense {new_expense['expense_id']} added to group {group_id}")
            
            return new_expense
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore update error: {str(e)}")
            raise APIError("Failed to add group expense", status_code=500)

    @staticmethod
    def get_group_details(uid, group_id):
        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            if uid not in group_data.get("members", []):
                raise APIError("Access denied", status_code=403)
                
            return group_data
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore error: {str(e)}")
            raise APIError("Failed to fetch group details", status_code=500)

    @staticmethod
    def get_group_summary(uid, group_id):
        group_data = GroupService.get_group_details(uid, group_id)
        members = group_data.get("members", [])
        expenses = group_data.get("expenses", [])

        # Initialize balances
        balances = {m: 0.0 for m in members}
        total_group_spending = 0.0

        for exp in expenses:
            amount = float(exp.get("amount", 0.0))
            paid_by = exp.get("paid_by")
            split_with = exp.get("split_with", members)
            
            total_group_spending += amount

            if not split_with:
                continue

            share = amount / len(split_with)

            # Decrease balance for split_with members
            for m in split_with:
                if m in balances:
                    balances[m] -= share

            # Increase balance for the payer
            if paid_by in balances:
                balances[paid_by] += amount

        # Round balances
        rounded_balances = {m: round(bal, 2) for m, bal in balances.items()}

        # Generate debt settlement steps
        # Find who owes whom
        debtors = [] # Negative balances (owes money)
        creditors = [] # Positive balances (is owed money)

        for m, bal in rounded_balances.items():
            if bal < -0.01:
                debtors.append({"member": m, "amount": -bal})
            elif bal > 0.01:
                creditors.append({"member": m, "amount": bal})

        # Sort to simplify matching
        debtors.sort(key=lambda x: x["amount"], reverse=True)
        creditors.sort(key=lambda x: x["amount"], reverse=True)

        settlements = []
        d_idx = 0
        c_idx = 0

        while d_idx < len(debtors) and c_idx < len(creditors):
            deb = debtors[d_idx]
            cred = creditors[c_idx]

            settled_amount = min(deb["amount"], cred["amount"])
            settlements.append({
                "from": deb["member"],
                "to": cred["member"],
                "amount": round(settled_amount, 2)
            })

            deb["amount"] -= settled_amount
            cred["amount"] -= settled_amount

            if deb["amount"] <= 0.01:
                d_idx += 1
            if cred["amount"] <= 0.01:
                c_idx += 1

        return {
            "group_id": group_id,
            "group_name": group_data.get("group_name"),
            "total_spending": round(total_group_spending, 2),
            "members": members,
            "balances": rounded_balances,
            "suggested_settlements": settlements
        }
