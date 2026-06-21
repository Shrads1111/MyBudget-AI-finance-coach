from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.recurring_service import RecurringService

recurring_bp = Blueprint('recurring', __name__)

@recurring_bp.route('/api/recurring', methods=['GET'])
@token_required
def get_recurring():
    payments = RecurringService.get_recurring(g.uid)
    return jsonify(payments), 200

@recurring_bp.route('/api/recurring', methods=['POST'])
@token_required
def create_recurring():
    data = request.get_json() or {}
    payment = RecurringService.create_recurring(g.uid, data)
    return jsonify(payment), 201

@recurring_bp.route('/api/recurring/<id>', methods=['PUT'])
@token_required
def update_recurring(id):
    data = request.get_json() or {}
    payment = RecurringService.update_recurring(g.uid, id, data)
    return jsonify(payment), 200

@recurring_bp.route('/api/recurring/<id>', methods=['DELETE'])
@token_required
def delete_recurring(id):
    result = RecurringService.delete_recurring(g.uid, id)
    return jsonify(result), 200

@recurring_bp.route('/api/recurring/<id>/pay', methods=['POST'])
@token_required
def pay_recurring(id):
    result = RecurringService.mark_as_paid(g.uid, id)
    return jsonify(result), 200
