from flask import Blueprint, request, jsonify, g
from middleware.error_handler import APIError
from utils.validator import Validator
from middleware.auth_middleware import token_required
from services.budget_service import BudgetService

budget_bp = Blueprint('budgets', __name__)

@budget_bp.route('/api/budgets', methods=['POST'])
@token_required
def create_budget():
    data = request.get_json() or {}
    # Validate allowed fields
    allowed_fields = ['category', 'limit', 'month', 'description']
    Validator.validate_allowed_fields(data, allowed_fields)
    # Validate required fields using validator utilities
    category = Validator.validate_budget_category(data.get('category'))
    limit = Validator.validate_limit(data.get('limit'))
    month = Validator.validate_budget_month(data.get('month'))
    # Optional description
    description = data.get('description', '')
    # Rebuild sanitized data dict for service
    sanitized = {'category': category, 'limit': limit, 'month': month, 'description': description}
    budget = BudgetService.create_budget(g.uid, sanitized)
    return jsonify(budget), 201

@budget_bp.route('/api/budgets', methods=['GET'])
@token_required
def get_budgets():
    budgets = BudgetService.get_budgets(g.uid)
    return jsonify(budgets), 200

@budget_bp.route('/api/budgets/alerts', methods=['GET'])
@token_required
def get_budget_alerts():
    alerts = BudgetService.get_alerts(g.uid)
    return jsonify(alerts), 200

@budget_bp.route('/api/budgets/<id>', methods=['GET'])
@token_required
def get_budget(id):
    budget = BudgetService.get_budget_by_id(g.uid, id)
    return jsonify(budget), 200

@budget_bp.route('/api/budgets/<id>', methods=['PUT'])
@token_required
def update_budget(id):
    data = request.get_json() or {}
    # Validate allowed fields for update
    allowed_fields = ['limit', 'description']
    Validator.validate_allowed_fields(data, allowed_fields)
    updates = {}
    if 'limit' in data:
        updates['limit'] = Validator.validate_limit(data['limit'])
    if 'description' in data:
        updates['description'] = data['description']
    # Pass updates dict; service will merge with existing budget
    budget = BudgetService.update_budget(g.uid, id, updates)
    budget = BudgetService.update_budget(g.uid, id, updates)
    return jsonify(budget), 200

@budget_bp.route('/api/budgets/<id>', methods=['DELETE'])
@token_required
def delete_budget(id):
    result = BudgetService.delete_budget(g.uid, id)
    return jsonify(result), 200

@budget_bp.route('/api/budgets/<id>/remaining', methods=['GET'])
@token_required
def get_budget_remaining(id):
    budget = BudgetService.get_budget_by_id(g.uid, id)
    return jsonify({
        "budget_id": budget["budget_id"],
        "category": budget["category"],
        "limit": budget["limit"],
        "spent": budget["spent"],
        "remaining": budget["remaining"]
    }), 200
