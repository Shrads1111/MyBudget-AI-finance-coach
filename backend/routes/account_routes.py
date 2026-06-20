from flask import Blueprint, jsonify, request, g
from middleware.auth_middleware import token_required
from services.account_service import AccountService
import logging

logger = logging.getLogger(__name__)

account_bp = Blueprint('accounts', __name__)

@account_bp.route('/api/accounts', methods=['GET'])
@token_required
def get_accounts():
    uid = g.uid
    accounts = AccountService.get_accounts(uid)
    return jsonify(accounts), 200

@account_bp.route('/api/accounts', methods=['POST'])
@token_required
def create_account():
    uid = g.uid
    data = request.get_json() or {}
    account = AccountService.create_account(uid, data)
    return jsonify(account), 201

@account_bp.route('/api/accounts/<account_id>', methods=['DELETE'])
@token_required
def delete_account(account_id):
    uid = g.uid
    result = AccountService.delete_account(uid, account_id)
    return jsonify(result), 200
