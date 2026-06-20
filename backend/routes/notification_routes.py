from flask import Blueprint, jsonify, g
from middleware.auth_middleware import token_required
from services.notification_service import NotificationService

notification_bp = Blueprint('notifications', __name__)

@notification_bp.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications():
    notifications = NotificationService.get_notifications(g.uid)
    return jsonify(notifications), 200

@notification_bp.route('/api/notifications/<id>/read', methods=['PUT'])
@token_required
def mark_notification_read(id):
    result = NotificationService.mark_as_read(g.uid, id)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code
