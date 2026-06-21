import uuid
from datetime import datetime
from services.firebase_service import FirebaseService
from middleware.error_handler import APIError
from utils.validator import Validator
from services.notification_service import NotificationService
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

        now_iso = datetime.utcnow().isoformat()
        group_data = {
            "group_id": group_id,
            "groupId": group_id,
            "group_name": name,
            "groupName": name,
            "created_by": uid,
            "createdBy": uid,
            "members": member_list,
            "created_at": now_iso,
            "createdAt": now_iso,
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

        db = FirebaseService.get_db()
        target_uid = None
        
        member_clean = member_email_or_uid.strip()
        if "@" in member_clean:
            # Query users collection by email
            user_docs = db.collection("users").where("email", "==", member_clean.lower()).limit(1).get()
            if not user_docs:
                raise APIError(f"User with email '{member_clean}' is not registered on MyBudget yet. Ask them to sign up first!", status_code=404)
            target_uid = user_docs[0].to_dict().get("uid")
        else:
            # Assume UID, verify it exists
            user_doc = db.collection("users").document(member_clean).get()
            if not user_doc.exists:
                raise APIError(f"User with UID '{member_clean}' not found", status_code=404)
            target_uid = user_doc.to_dict().get("uid")

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
            if target_uid in current_members:
                raise APIError("User is already a member of this group", status_code=400)

            current_members.append(target_uid)
            doc_ref.update({"members": current_members})
            
            logger.info(f"User {target_uid} added to group {group_id}")
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
        category = expense_data.get("category", "Other")

        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            members = group_data.get("members", [])
            group_name = group_data.get("group_name", "Group")
            
            if uid not in members:
                raise APIError("Access denied", status_code=403)
                
            if paid_by not in members:
                raise APIError(f"Paying user '{paid_by}' must be a member of the group", status_code=400)

            # Determine split type
            split_type = expense_data.get("split_type", "equal")
            if split_type not in ["equal", "custom"]:
                split_type = "equal"

            splits = []
            if split_type == "equal":
                # Define split members list
                split_with = expense_data.get("split_with")
                if not split_with:
                    split_with = list(members)
                else:
                    for m in split_with:
                        if m not in members:
                            raise APIError(f"Split user '{m}' must be a member of the group", status_code=400)
                
                num_members = len(split_with)
                if num_members == 0:
                    raise APIError("Split must include at least one member", status_code=400)
                
                share = round(amount / num_members, 2)
                diff = round(amount - (share * num_members), 2)
                
                for i, m in enumerate(split_with):
                    member_share = share
                    if i == num_members - 1:
                        member_share = round(share + diff, 2)
                    
                    is_paid = (m == paid_by)
                    splits.append({
                        "member": m,
                        "amount": member_share,
                        "paid": is_paid,
                        "paid_at": datetime.utcnow().isoformat() if is_paid else None
                    })
            else: # custom
                custom_splits = expense_data.get("splits")
                if not custom_splits or not isinstance(custom_splits, list):
                    raise APIError("Splits list is required for custom split type", status_code=400)
                
                sum_amount = 0.0
                for s in custom_splits:
                    m = s.get("member")
                    if m not in members:
                        raise APIError(f"Split user '{m}' must be a member of the group", status_code=400)
                    
                    s_amt = Validator.validate_amount(s.get("amount"), f"Share amount for {m}")
                    sum_amount += s_amt
                    
                    is_paid = (m == paid_by)
                    splits.append({
                        "member": m,
                        "amount": round(s_amt, 2),
                        "paid": is_paid,
                        "paid_at": datetime.utcnow().isoformat() if is_paid else None
                    })
                
                if abs(sum_amount - amount) > 0.05:
                    raise APIError(f"Sum of custom splits (₹{sum_amount}) must equal total amount (₹{amount})", status_code=400)
                
                diff = round(amount - sum_amount, 2)
                if diff != 0 and len(splits) > 0:
                    splits[-1]["amount"] = round(splits[-1]["amount"] + diff, 2)

            expense_id = str(uuid.uuid4())
            now_iso = datetime.utcnow().isoformat()
            new_expense = {
                "expense_id": expense_id,
                "expenseId": expense_id,
                "group_id": group_id,
                "groupId": group_id,
                "amount": float(amount),
                "description": description,
                "paid_by": paid_by,
                "paidBy": paid_by,
                "date": date,
                "category": category,
                "split_type": split_type,
                "splits": splits,
                "participants": [s["member"] for s in splits],
                "created_at": now_iso,
                "createdAt": now_iso
            }

            db = FirebaseService.get_db()
            is_mock = hasattr(db, "mock_collection") or "MagicMock" in str(type(db))

            if not is_mock:
                from google.cloud import firestore
                transaction = db.transaction()

                @firestore.transactional
                def add_txn(txn):
                    snap = doc_ref.get(transaction=txn)
                    g_data = snap.to_dict()
                    curr_expenses = list(g_data.get("expenses", []))
                    curr_expenses.append(new_expense)
                    txn.update(doc_ref, {"expenses": curr_expenses})

                add_txn(transaction)
            else:
                current_expenses = list(group_data.get("expenses", []))
                current_expenses.append(new_expense)
                doc_ref.update({"expenses": current_expenses})

            logger.info(f"Group expense {new_expense['expense_id']} added to group {group_id}")

            # Create normal expense transaction for the payer to sync dashboard/analytics/health score
            try:
                from services.expense_service import ExpenseService
                ExpenseService.create_expense(paid_by, {
                    "expense_id": expense_id,
                    "amount": float(amount),
                    "category": category,
                    "date": date,
                    "description": f"[{group_name}] {description}"
                })
            except Exception as txn_err:
                logger.error(f"Failed to create normal expense transaction: {str(txn_err)}")

            # Notify members
            try:
                db = FirebaseService.get_db()
                payer_doc = db.collection("users").document(paid_by).get()
                payer_name = paid_by
                if payer_doc.exists:
                    payer_name = payer_doc.to_dict().get("display_name") or payer_doc.to_dict().get("email") or paid_by

                for s in splits:
                    m = s["member"]
                    if m != paid_by:
                        s_amt = s["amount"]
                        NotificationService.create_notification(
                            uid=m,
                            title=f"New Split Request in {group_name}",
                            message=f"{payer_name} requested ₹{s_amt} for '{description}'",
                            category="Group Bills",
                            severity="info"
                        )
            except Exception as notify_err:
                logger.error(f"Error sending split notifications: {str(notify_err)}")
            
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
            total_group_spending += amount
            
            splits = exp.get("splits")
            if splits:
                for s in splits:
                    m = s.get("member")
                    s_amt = float(s.get("amount", 0.0))
                    is_paid = s.get("paid", False)
                    
                    if m == paid_by:
                        continue
                    
                    if not is_paid:
                        if m in balances:
                            balances[m] -= s_amt
                        if paid_by in balances:
                            balances[paid_by] += s_amt
            else:
                # Backwards compatibility for old expenses
                split_with = exp.get("split_with", members)
                if not split_with:
                    continue
                share = amount / len(split_with)
                for m in split_with:
                    if m == paid_by:
                        continue
                    if m in balances:
                        balances[m] -= share
                    if paid_by in balances:
                        balances[paid_by] += share

        # Round balances
        rounded_balances = {m: round(bal, 2) for m, bal in balances.items()}

        # Delegate settlement calculation to SettlementService
        from services.settlement_service import SettlementService
        settlements = SettlementService.simplify_debts(rounded_balances)

        per_person_share = round(total_group_spending / len(members), 2) if members else 0.0

        return {
            "group_id": group_id,
            "group_name": group_data.get("group_name"),
            "total_spending": round(total_group_spending, 2),
            "total_expenses": round(total_group_spending, 2),
            "member_count": len(members),
            "per_person_share": per_person_share,
            "members": members,
            "balances": rounded_balances,
            "suggested_settlements": settlements,
            "settlements": settlements
        }

    @staticmethod
    def pay_expense_share(uid, group_id, expense_id):
        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            members = group_data.get("members", [])
            group_name = group_data.get("group_name", "Group")
            if uid not in members:
                raise APIError("Access denied", status_code=403)
                
            expenses = list(group_data.get("expenses", []))
            found_expense = None
            for exp in expenses:
                if exp.get("expense_id") == expense_id:
                    found_expense = exp
                    break
            
            if not found_expense:
                raise APIError("Expense not found", status_code=404)
                
            # Find uid's split and mark as paid
            splits = found_expense.get("splits", [])
            updated = False
            paid_amount = 0.0
            for s in splits:
                if s.get("member") == uid:
                    if s.get("paid"):
                        raise APIError("Your share for this expense is already paid", status_code=400)
                    s["paid"] = True
                    s["paid_at"] = datetime.utcnow().isoformat()
                    paid_amount = s.get("amount", 0.0)
                    updated = True
                    break
                    
            if not updated:
                raise APIError("You are not part of this expense split", status_code=400)
                
            doc_ref.update({"expenses": expenses})
            logger.info(f"User {uid} paid their share of expense {expense_id} in group {group_id}")

            # Notify the payer
            try:
                paid_by = found_expense.get("paid_by")
                db = FirebaseService.get_db()
                payer_doc = db.collection("users").document(uid).get()
                payer_name = uid
                if payer_doc.exists:
                    payer_name = payer_doc.to_dict().get("display_name") or payer_doc.to_dict().get("email") or uid
                
                NotificationService.create_notification(
                    uid=paid_by,
                    title="Split Payment Received",
                    message=f"{payer_name} paid their share of ₹{paid_amount} for '{found_expense.get('description')}' in {group_name}",
                    category="Group Bills",
                    severity="success"
                )
            except Exception as notify_err:
                logger.error(f"Error sending payment notification: {str(notify_err)}")

            return found_expense
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore pay error: {str(e)}")
            raise APIError("Failed to pay expense share", status_code=500)

    @staticmethod
    def mark_expense_share_paid(uid, group_id, expense_id, member_uid):
        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            members = group_data.get("members", [])
            group_name = group_data.get("group_name", "Group")
            if uid not in members:
                raise APIError("Access denied", status_code=403)
                
            expenses = list(group_data.get("expenses", []))
            found_expense = None
            for exp in expenses:
                if exp.get("expense_id") == expense_id:
                    found_expense = exp
                    break
            
            if not found_expense:
                raise APIError("Expense not found", status_code=404)
                
            # Verify caller is the payer
            if found_expense.get("paid_by") != uid:
                raise APIError("Only the creator/payer of this bill can mark members as paid", status_code=403)
                
            # Find member_uid's split and mark as paid
            splits = found_expense.get("splits", [])
            updated = False
            paid_amount = 0.0
            for s in splits:
                if s.get("member") == member_uid:
                    if s.get("paid"):
                        raise APIError("This member's share is already marked as paid", status_code=400)
                    s["paid"] = True
                    s["paid_at"] = datetime.utcnow().isoformat()
                    paid_amount = s.get("amount", 0.0)
                    updated = True
                    break
                    
            if not updated:
                raise APIError(f"Member '{member_uid}' is not part of this expense split", status_code=400)
                
            doc_ref.update({"expenses": expenses})
            logger.info(f"User {uid} marked member {member_uid} as paid for expense {expense_id} in group {group_id}")

            # Notify the member
            try:
                db = FirebaseService.get_db()
                payer_doc = db.collection("users").document(uid).get()
                payer_name = uid
                if payer_doc.exists:
                    payer_name = payer_doc.to_dict().get("display_name") or payer_doc.to_dict().get("email") or uid

                NotificationService.create_notification(
                    uid=member_uid,
                    title="Split Marked as Paid",
                    message=f"{payer_name} marked your share of ₹{paid_amount} for '{found_expense.get('description')}' as Paid in {group_name}",
                    category="Group Bills",
                    severity="success"
                )
            except Exception as notify_err:
                logger.error(f"Error sending mark-paid notification: {str(notify_err)}")

            return found_expense
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore update error: {str(e)}")
            raise APIError("Failed to mark share as paid", status_code=500)

    @staticmethod
    def remind_member(uid, group_id, expense_id, member_uid):
        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            members = group_data.get("members", [])
            group_name = group_data.get("group_name", "Group")
            if uid not in members:
                raise APIError("Access denied", status_code=403)
                
            expenses = list(group_data.get("expenses", []))
            found_expense = None
            for exp in expenses:
                if exp.get("expense_id") == expense_id:
                    found_expense = exp
                    break
            
            if not found_expense:
                raise APIError("Expense not found", status_code=404)
                
            # Verify caller is the payer
            if found_expense.get("paid_by") != uid:
                raise APIError("Only the creator/payer of this bill can remind members", status_code=403)
                
            # Find member_uid's split and verify unpaid
            splits = found_expense.get("splits", [])
            target_split = None
            for s in splits:
                if s.get("member") == member_uid:
                    target_split = s
                    break
                    
            if not target_split:
                raise APIError(f"Member '{member_uid}' is not part of this expense split", status_code=400)
                
            if target_split.get("paid"):
                raise APIError("This member has already paid their share", status_code=400)
                
            # Send reminder notification
            db = FirebaseService.get_db()
            payer_doc = db.collection("users").document(uid).get()
            payer_name = uid
            if payer_doc.exists:
                payer_name = payer_doc.to_dict().get("display_name") or payer_doc.to_dict().get("email") or uid

            remind_amount = target_split.get("amount", 0.0)
            NotificationService.create_notification(
                uid=member_uid,
                title=f"Payment Reminder in {group_name}",
                message=f"{payer_name} reminded you to pay ₹{remind_amount} for '{found_expense.get('description')}'",
                category="Group Bills",
                severity="warning"
            )
            logger.info(f"User {uid} sent payment reminder to {member_uid} for {expense_id}")
            return {"success": True, "message": "Reminder sent successfully"}
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Firestore remind error: {str(e)}")
            raise APIError("Failed to send reminder notification", status_code=500)

    @staticmethod
    def edit_expense(uid, group_id, expense_id, expense_data):
        amount = Validator.validate_amount(expense_data.get("amount"))
        description = expense_data.get("description")
        if not description:
            raise APIError("description is required", status_code=400)
            
        paid_by = expense_data.get("paid_by", uid)
        date = expense_data.get("date", datetime.utcnow().date().isoformat())
        category = expense_data.get("category", "Other")

        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            members = group_data.get("members", [])
            group_name = group_data.get("group_name", "Group")
            
            if uid not in members:
                raise APIError("Access denied", status_code=403)
            if paid_by not in members:
                raise APIError(f"Paying user '{paid_by}' must be a member of the group", status_code=400)

            # Determine split type
            split_type = expense_data.get("split_type", "equal")
            if split_type not in ["equal", "custom"]:
                split_type = "equal"

            splits = []
            if split_type == "equal":
                # Define split members list
                split_with = expense_data.get("split_with")
                if not split_with:
                    split_with = list(members)
                else:
                    for m in split_with:
                        if m not in members:
                            raise APIError(f"Split user '{m}' must be a member of the group", status_code=400)
                
                num_members = len(split_with)
                if num_members == 0:
                    raise APIError("Split must include at least one member", status_code=400)
                
                share = round(amount / num_members, 2)
                diff = round(amount - (share * num_members), 2)
                
                for i, m in enumerate(split_with):
                    member_share = share
                    if i == num_members - 1:
                        member_share = round(share + diff, 2)
                    
                    is_paid = (m == paid_by)
                    splits.append({
                        "member": m,
                        "amount": member_share,
                        "paid": is_paid,
                        "paid_at": datetime.utcnow().isoformat() if is_paid else None
                    })
            else: # custom
                custom_splits = expense_data.get("splits")
                if not custom_splits or not isinstance(custom_splits, list):
                    raise APIError("Splits list is required for custom split type", status_code=400)
                
                sum_amount = 0.0
                for s in custom_splits:
                    m = s.get("member")
                    if m not in members:
                        raise APIError(f"Split user '{m}' must be a member of the group", status_code=400)
                    
                    s_amt = Validator.validate_amount(s.get("amount"), f"Share amount for {m}")
                    sum_amount += s_amt
                    
                    is_paid = (m == paid_by)
                    splits.append({
                        "member": m,
                        "amount": round(s_amt, 2),
                        "paid": is_paid,
                        "paid_at": datetime.utcnow().isoformat() if is_paid else None
                    })
                
                if abs(sum_amount - amount) > 0.05:
                    raise APIError(f"Sum of custom splits (₹{sum_amount}) must equal total amount (₹{amount})", status_code=400)
                
                diff = round(amount - sum_amount, 2)
                if diff != 0 and len(splits) > 0:
                    splits[-1]["amount"] = round(splits[-1]["amount"] + diff, 2)

            now_iso = datetime.utcnow().isoformat()
            
            # Find the old expense in group_data to see its payer
            expenses = list(group_data.get("expenses", []))
            target_idx = -1
            old_expense = None
            for idx, exp in enumerate(expenses):
                if exp.get("expense_id") == expense_id:
                    target_idx = idx
                    old_expense = exp
                    break
            
            if target_idx == -1:
                raise APIError("Expense not found", status_code=404)

            # Preserve split paid states if members match
            old_splits = old_expense.get("splits", [])
            for s in splits:
                old_s = next((os for os in old_splits if os.get("member") == s["member"]), None)
                if old_s and old_s.get("paid"):
                    s["paid"] = True
                    s["paid_at"] = old_s.get("paid_at")

            edited_expense = {
                "expense_id": expense_id,
                "expenseId": expense_id,
                "group_id": group_id,
                "groupId": group_id,
                "amount": float(amount),
                "description": description,
                "paid_by": paid_by,
                "paidBy": paid_by,
                "date": date,
                "category": category,
                "split_type": split_type,
                "splits": splits,
                "participants": [s["member"] for s in splits],
                "created_at": old_expense.get("created_at", now_iso),
                "createdAt": old_expense.get("createdAt", now_iso)
            }

            db = FirebaseService.get_db()
            is_mock = hasattr(db, "mock_collection") or "MagicMock" in str(type(db))

            if not is_mock:
                from google.cloud import firestore
                transaction = db.transaction()

                @firestore.transactional
                def edit_txn(txn):
                    snap = doc_ref.get(transaction=txn)
                    g_data = snap.to_dict()
                    curr_expenses = list(g_data.get("expenses", []))
                    t_idx = -1
                    for idx, exp in enumerate(curr_expenses):
                        if exp.get("expense_id") == expense_id:
                            t_idx = idx
                            break
                    if t_idx != -1:
                        curr_expenses[t_idx] = edited_expense
                        txn.update(doc_ref, {"expenses": curr_expenses})

                edit_txn(transaction)
            else:
                expenses[target_idx] = edited_expense
                doc_ref.update({"expenses": expenses})

            logger.info(f"Group expense {expense_id} edited in group {group_id}")

            # Sync normal expense transaction for the payer
            try:
                from services.expense_service import ExpenseService
                old_paid_by = old_expense.get("paid_by")
                if old_paid_by != paid_by:
                    # Payer changed: delete old and create new
                    try:
                        ExpenseService.delete_expense(old_paid_by, expense_id)
                    except Exception:
                        pass
                    ExpenseService.create_expense(paid_by, {
                        "expense_id": expense_id,
                        "amount": float(amount),
                        "category": category,
                        "date": date,
                        "description": f"[{group_name}] {description}"
                    })
                else:
                    # Payer did not change: update existing
                    try:
                        ExpenseService.update_expense(paid_by, expense_id, {
                            "amount": float(amount),
                            "category": category,
                            "date": date,
                            "description": f"[{group_name}] {description}"
                        })
                    except Exception:
                        # If not found, create it
                        ExpenseService.create_expense(paid_by, {
                            "expense_id": expense_id,
                            "amount": float(amount),
                            "category": category,
                            "date": date,
                            "description": f"[{group_name}] {description}"
                        })
            except Exception as txn_err:
                logger.error(f"Failed to sync edited expense to transaction: {str(txn_err)}")

            return edited_expense
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Group expense edit failed: {str(e)}")
            raise APIError("Failed to edit group expense", status_code=500)

    @staticmethod
    def delete_expense(uid, group_id, expense_id):
        try:
            doc_ref = GroupService.get_collection().document(group_id)
            doc = doc_ref.get()
            if not doc.exists:
                raise APIError("Group not found", status_code=404)
            
            group_data = doc.to_dict()
            members = group_data.get("members", [])
            if uid not in members:
                raise APIError("Access denied", status_code=403)

            expenses = list(group_data.get("expenses", []))
            target_expense = None
            for exp in expenses:
                if exp.get("expense_id") == expense_id:
                    target_expense = exp
                    break
            
            if not target_expense:
                raise APIError("Expense not found", status_code=404)

            db = FirebaseService.get_db()
            is_mock = hasattr(db, "mock_collection") or "MagicMock" in str(type(db))

            if not is_mock:
                from google.cloud import firestore
                transaction = db.transaction()

                @firestore.transactional
                def delete_txn(txn):
                    snap = doc_ref.get(transaction=txn)
                    g_data = snap.to_dict()
                    curr_expenses = list(g_data.get("expenses", []))
                    updated_expenses = [exp for exp in curr_expenses if exp.get("expense_id") != expense_id]
                    txn.update(doc_ref, {"expenses": updated_expenses})

                delete_txn(transaction)
            else:
                updated_expenses = [exp for exp in expenses if exp.get("expense_id") != expense_id]
                doc_ref.update({"expenses": updated_expenses})

            logger.info(f"Group expense {expense_id} deleted from group {group_id}")

            # Delete the linked transaction from standard expenses
            try:
                from services.expense_service import ExpenseService
                payer = target_expense.get("paid_by")
                ExpenseService.delete_expense(payer, expense_id)
            except Exception as txn_err:
                logger.error(f"Failed to delete linked transaction {expense_id}: {str(txn_err)}")

            return {"success": True, "message": "Group expense deleted successfully"}
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Group expense delete failed: {str(e)}")
            raise APIError("Failed to delete group expense", status_code=500)

    @staticmethod
    def parse_expense_ai(uid, group_id, query):
        """
        Uses Gemini to parse natural language expense query against the group members.
        Returns extracted structure: payer, amount, category, description, participants, and confirmation checks.
        """
        import json
        import re
        # Validate that the user is member of the group
        group_data = GroupService.get_group_details(uid, group_id)
        members_uids = group_data.get("members", [])
        
        db = FirebaseService.get_db()
        members_list = []
        for m_uid in members_uids:
            doc = db.collection("users").document(m_uid).get()
            if doc.exists:
                members_list.append(doc.to_dict())
            else:
                members_list.append({"uid": m_uid})
                    
        members_str = "\n".join([f"- UID: {m['uid']}, Name: {m.get('display_name') or ''}, Email: {m.get('email') or ''}" for m in members_list])
        
        prompt = f"""You are a smart financial assistant for MyBudget, parsing a natural language group expense entry.

Your job is to parse the user's natural language input and extract:
1. Payer: Who paid for the expense? (Match them to one of the group members provided below).
2. Amount: The numeric amount spent.
3. Category: The expense category. Choose from: Food, Utilities, Travel, Shopping, Entertainment, Other.
4. Description: A clean, short description of the expense (e.g., "lunch", "petrol").
5. Participants: Who is split with? (List of member UIDs or names). If specific people are mentioned (e.g., "with Sai"), include only them and the payer. If no specific participants are mentioned, include all group members.
6. Confidence: A float from 0.0 to 1.0 indicating how confident you are in this parsing.

Group members list:
{members_str}

Current user's UID: {uid}

RULES:
1. Return ONLY valid JSON. No markdown, no code fences, no explanation.
2. Match name/payer/participants using display names, first names, or emails.
3. Ensure category is exactly one of: Food, Utilities, Travel, Shopping, Entertainment, Other.

User input: "{query}"

Return exactly this JSON structure:
{{
  "payer": "<uid_or_name_of_payer>",
  "amount": <number_or_null>,
  "category": "<Food|Utilities|Travel|Shopping|Entertainment|Other>",
  "description": "<string>",
  "participants": ["<uid_or_name1>", "<uid_or_name2>"],
  "confidence": <float>
}}"""

        try:
            from services.ai_service import AIService
            raw = AIService.generate_content(prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?\s*", "", raw).strip("`\n ")
            parsed = json.loads(raw)
            
            parsed_payer = parsed.get("payer")
            parsed_amount = parsed.get("amount")
            parsed_category = parsed.get("category", "Other")
            parsed_description = parsed.get("description", "")
            parsed_participants = parsed.get("participants", [])
            parsed_confidence = parsed.get("confidence", 0.8)
            
            # Helper to map name or UID to group member
            def find_member_uid(name_or_uid):
                if not name_or_uid:
                    return None
                name_or_uid_clean = str(name_or_uid).strip().lower()
                # 1. Direct UID match
                for m in members_list:
                    if m["uid"].lower() == name_or_uid_clean:
                        return m["uid"]
                # 2. Case-insensitive exact name/email match
                for m in members_list:
                    disp = str(m.get("display_name") or "").strip().lower()
                    email = str(m.get("email") or "").strip().lower()
                    if disp == name_or_uid_clean or email == name_or_uid_clean:
                        return m["uid"]
                # 3. Substring match on name/email
                for m in members_list:
                    disp = str(m.get("display_name") or "").strip().lower()
                    email = str(m.get("email") or "").strip().lower()
                    if name_or_uid_clean in disp or name_or_uid_clean in email:
                        return m["uid"]
                return None

            resolved_payer = find_member_uid(parsed_payer)
            needs_confirmation = False
            
            if not resolved_payer:
                resolved_payer = uid  # Default to caller
                needs_confirmation = True
                
            resolved_participants = []
            for p in parsed_participants:
                r_uid = find_member_uid(p)
                if r_uid:
                    resolved_participants.append(r_uid)
                else:
                    needs_confirmation = True
            
            # Remove duplicates and ensure participants are group members
            resolved_participants = list(set(resolved_participants))
            resolved_participants = [p for p in resolved_participants if p in members_uids]
            
            if not resolved_participants:
                resolved_participants = list(members_uids)
                
            try:
                confidence = float(parsed_confidence)
            except (ValueError, TypeError):
                confidence = 0.8
                
            if confidence < 0.7 or parsed_amount is None or float(parsed_amount) <= 0:
                needs_confirmation = True
                
            return {
                "payer": resolved_payer,
                "amount": float(parsed_amount) if parsed_amount is not None else None,
                "category": parsed_category if parsed_category in ["Food", "Utilities", "Travel", "Shopping", "Entertainment", "Other"] else "Other",
                "description": parsed_description,
                "participants": resolved_participants,
                "confidence": confidence,
                "needs_confirmation": needs_confirmation
            }
        except Exception as e:
            logger.error(f"Gemini group expense parsing failed: {str(e)}")
            raise APIError("Failed to parse group expense with AI. Please fill in details manually.", status_code=500)
