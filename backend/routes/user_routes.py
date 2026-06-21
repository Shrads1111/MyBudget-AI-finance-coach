from flask import Blueprint, jsonify, g
from middleware.auth_middleware import token_required
from services.firebase_service import FirebaseService
from models.user_model import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('users', __name__)

@user_bp.route('/api/users/sync', methods=['POST'])
@token_required
def sync_user():
    """
    Syncs Firebase authenticated user profile into Firestore users collection.
    """
    uid = g.uid
    email = g.user_email
    name = g.user_name
    
    db = FirebaseService.get_db()
    user_ref = db.collection("users").document(uid)
    
    try:
        doc = user_ref.get()
        if doc.exists:
            user_data = doc.to_dict()
            updates = {}
            if user_data.get("email") != email:
                updates["email"] = email
            if name and user_data.get("display_name") != name:
                updates["display_name"] = name
            if updates:
                updates["updated_at"] = datetime.utcnow().isoformat()
                user_ref.update(updates)
                user_data.update(updates)
            return jsonify(user_data), 200
        else:
            new_user = User(
                uid=uid,
                email=email,
                display_name=name or (email.split("@")[0] if email else "User")
            )
            user_data = new_user.to_dict()
            user_ref.set(user_data)
            return jsonify(user_data), 201
    except Exception as e:
        logger.error(f"Error syncing user {uid}: {str(e)}")
        return jsonify({
            "error": True,
            "message": "Failed to sync user profile"
        }), 500


@user_bp.route('/api/users/lookup', methods=['POST'])
@token_required
def lookup_users():
    """
    Looks up user profiles for a list of emails and/or UIDs.
    Request body: {"uids": ["uid1", "uid2"], "emails": ["email1@example.com"]}
    """
    from flask import request
    data = request.get_json() or {}
    uids = data.get("uids", [])
    emails = data.get("emails", [])
    
    db = FirebaseService.get_db()
    profiles = {}
    
    # 1. Lookup by UID
    if uids:
        try:
            doc_refs = [db.collection("users").document(uid.strip()) for uid in uids if uid.strip()]
            if doc_refs:
                docs = db.get_all(doc_refs)
                for doc in docs:
                    if doc.exists:
                        val = doc.to_dict()
                        profiles[val["uid"]] = {
                            "uid": val["uid"],
                            "email": val.get("email", ""),
                            "display_name": val.get("display_name", "")
                        }
        except Exception as e:
            logger.error(f"Error looking up users by UID: {str(e)}")
            
    # 2. Lookup by Email
    if emails:
        cleaned_emails = [e.strip().lower() for e in emails if e.strip()]
        if cleaned_emails:
            try:
                # Firestore 'in' query supports up to 10 elements
                for i in range(0, len(cleaned_emails), 10):
                    chunk = cleaned_emails[i:i+10]
                    docs = db.collection("users").where("email", "in", chunk).stream()
                    for doc in docs:
                        val = doc.to_dict()
                        profiles[val["uid"]] = {
                            "uid": val["uid"],
                            "email": val.get("email", ""),
                            "display_name": val.get("display_name", "")
                        }
            except Exception as e:
                logger.error(f"Error looking up users by Email: {str(e)}")
                
    return jsonify(profiles), 200

