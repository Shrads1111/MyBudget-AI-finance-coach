from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.budget_service import BudgetService

budget_bp = Blueprint('budgets', __name__)

@budget_bp.route('/api/budgets', methods=['POST'])
@token_required
def create_budget():
    data = request.get_json() or {}
    budget = BudgetService.create_budget(g.uid, data)
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
    budget = BudgetService.update_budget(g.uid, id, data)
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
