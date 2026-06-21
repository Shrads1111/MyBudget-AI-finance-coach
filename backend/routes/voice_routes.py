from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
from services.voice_service import VoiceService
import logging

logger = logging.getLogger(__name__)

voice_bp = Blueprint('voice', __name__)


@voice_bp.route('/api/voice/parse', methods=['POST'])
@token_required
def parse_voice_transcript():
    """
    Parses a natural language voice transcript into a structured transaction.
    Requires authenticated user.

    Request body:
        { "transcript": "Spent 250 on lunch" }

    Response (success):
        {
            "amount": 250.0,
            "type": "expense",
            "category": "Food",
            "date": "2026-06-20",
            "note": "Lunch",
            "confidence": 0.97,
            "friend_name": null,
            "friend_owe_amount": null,
            "clarification_needed": false,
            "clarification_message": null
        }

    Response (clarification needed):
        {
            "clarification_needed": true,
            "clarification_message": "I couldn't find an amount..."
        }
    """
    data = request.get_json() or {}
    transcript = data.get("transcript", "").strip()

    if not transcript:
        return jsonify({
            "clarification_needed": True,
            "clarification_message": "No transcript provided."
        }), 200

    logger.info(f"Voice parse request from user {g.uid}: '{transcript}'")

    result = VoiceService.parse_transcript(transcript)
    return jsonify(result), 200
