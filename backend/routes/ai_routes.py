from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import token_required
# All AI agent and service imports are lazy (inside handlers) to prevent
# protobuf C-extension crash on Python 3.14 during blueprint import.
import logging

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/api/ai/analyze', methods=['POST'])
@token_required
def analyze_finances():
    """
    Analyzes user financial behavior and returns consolidated reports and recommendations.
    """
    try:
        from agents.health_score_agent import HealthScoreAgent
        from agents.forecasting_agent import ForecastingAgent
        from agents.insights_agent import InsightsAgent
        from services.ai_service import AIService

        health = HealthScoreAgent.analyze(g.uid)
        forecast = ForecastingAgent.analyze(g.uid)
        insights = InsightsAgent.analyze(g.uid)
        
        prompt = f"""
You are the AI Financial Advisor for MyBudget.
Here is the aggregated financial behavior analysis of the user:
- Health Score Report: {health}
- Forecasting Projections: {forecast}
- Spending Insights: {insights}

Please write a comprehensive, professional financial advisory report.
It must include:
1. Executive Summary of their financial behavior.
2. Areas of improvement & warnings.
3. Concrete, step-by-step recommendations.
Keep it encouraging, clean, and well-structured using Markdown.
"""
        advisory_report = AIService.generate_content(prompt)
        
        return jsonify({
            "health_analysis": health,
            "forecasting": forecast,
            "insights": insights,
            "advisory_report": advisory_report
        }), 200
    except Exception as e:
        logger.error(f"Error generating financial analysis: {str(e)}")
        return jsonify({
            "error": True,
            "message": "Failed to analyze financial logs"
        }), 500

@ai_bp.route('/api/ai/chat', methods=['POST'])
@token_required
def chat():
    """
    Orchestrated chat advisor endpoint.
    """
    from agents.orchestrator import OrchestratorAgent
    data = request.get_json() or {}
    user_query = data.get("query")
    if not user_query:
        return jsonify({
            "error": True,
            "message": "Field 'query' is required"
        }), 400
        
    result = OrchestratorAgent.chat(g.uid, user_query)
    return jsonify(result), 200
