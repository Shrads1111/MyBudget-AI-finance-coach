from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.group_service import GroupService

group_bp = Blueprint('groups', __name__)

@group_bp.route('/api/groups', methods=['GET'])
@token_required
def get_user_groups():
    groups = GroupService.get_user_groups(g.uid)
    return jsonify(groups), 200

@group_bp.route('/api/groups', methods=['POST'])
@token_required
def create_group():

    data = request.get_json() or {}
    group_name = data.get("group_name")
    members = data.get("members", [])
    group = GroupService.create_group(g.uid, group_name, members)
    return jsonify(group), 201

@group_bp.route('/api/groups/invite', methods=['POST'])
@token_required
def invite_member():
    data = request.get_json() or {}
    group_id = data.get("group_id")
    member = data.get("member")
    
    group = GroupService.invite_member(g.uid, group_id, member)
    return jsonify(group), 200

@group_bp.route('/api/groups/expense', methods=['POST'])
@token_required
def add_group_expense():
    data = request.get_json() or {}
    group_id = data.get("group_id")
    expense_data = data.get("expense", {})
    
    expense = GroupService.add_expense(g.uid, group_id, expense_data)
    return jsonify(expense), 201

@group_bp.route('/api/groups/<id>', methods=['GET'])
@token_required
def get_group_details(id):
    group = GroupService.get_group_details(g.uid, id)
    return jsonify(group), 200

@group_bp.route('/api/groups/<id>/summary', methods=['GET'])
@token_required
def get_group_summary(id):
    summary = GroupService.get_group_summary(g.uid, id)
    return jsonify(summary), 200
