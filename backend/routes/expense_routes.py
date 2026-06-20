from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.expense_service import ExpenseService

expense_bp = Blueprint('expenses', __name__)

@expense_bp.route('/api/expenses', methods=['POST'])
@token_required
def create_expense():
    data = request.get_json() or {}
    expense = ExpenseService.create_expense(g.uid, data)
    return jsonify(expense), 201

@expense_bp.route('/api/expenses', methods=['GET'])
@token_required
def get_expenses():
    category = request.args.get('category')
    month = request.args.get('month') # YYYY-MM
    year = request.args.get('year') # YYYY
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'desc')
    
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
    except ValueError:
        limit = 10
        offset = 0
        
    result = ExpenseService.get_expenses(
        uid=g.uid,
        category=category,
        month=month,
        year=year,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    return jsonify(result), 200

@expense_bp.route('/api/expenses/<id>', methods=['GET'])
@token_required
def get_expense(id):
    expense = ExpenseService.get_expense_by_id(g.uid, id)
    return jsonify(expense), 200

@expense_bp.route('/api/expenses/<id>', methods=['PUT'])
@token_required
def update_expense(id):
    data = request.get_json() or {}
    expense = ExpenseService.update_expense(g.uid, id, data)
    return jsonify(expense), 200

@expense_bp.route('/api/expenses/<id>', methods=['DELETE'])
@token_required
def delete_expense(id):
    result = ExpenseService.delete_expense(g.uid, id)
    return jsonify(result), 200
