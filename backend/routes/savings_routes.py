from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.savings_service import SavingsService

savings_bp = Blueprint('savings', __name__)

@savings_bp.route('/api/goals', methods=['POST'])
@token_required
def create_goal():
    data = request.get_json() or {}
    goal = SavingsService.create_goal(g.uid, data)
    return jsonify(goal), 201

@savings_bp.route('/api/goals', methods=['GET'])
@token_required
def get_goals():
    goals = SavingsService.get_goals(g.uid)
    return jsonify(goals), 200

@savings_bp.route('/api/goals/<id>', methods=['GET'])
@token_required
def get_goal(id):
    goal = SavingsService.get_goal_by_id(g.uid, id)
    return jsonify(goal), 200

@savings_bp.route('/api/goals/<id>', methods=['PUT'])
@token_required
def update_goal(id):
    data = request.get_json() or {}
    goal = SavingsService.update_goal(g.uid, id, data)
    return jsonify(goal), 200

@savings_bp.route('/api/goals/<id>', methods=['DELETE'])
@token_required
def delete_goal(id):
    result = SavingsService.delete_goal(g.uid, id)
    return jsonify(result), 200

@savings_bp.route('/api/goals/<id>/progress', methods=['GET'])
@token_required
def get_goal_progress(id):
    goal = SavingsService.get_goal_by_id(g.uid, id)
    return jsonify({
        "goal_id": goal["goal_id"],
        "goal_name": goal["goal_name"],
        "progress_percentage": goal["progress_percentage"],
        "remaining_amount": goal["remaining_amount"],
        "monthly_saving_needed": goal["monthly_saving_needed"]
    }), 200
