from agents.expense_agent import ExpenseAgent
from agents.budget_agent import BudgetAgent
from agents.savings_agent import SavingsAgent
from agents.insights_agent import InsightsAgent
from agents.finance_coach_agent import FinanceCoachAgent
from agents.forecasting_agent import ForecastingAgent
from agents.health_score_agent import HealthScoreAgent
from services.ai_service import AIService
from services.firebase_service import FirebaseService
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    @staticmethod
    def save_conversation(uid, user_message, agent_response):
        try:
            db = FirebaseService.get_db()
            conv_id = str(uuid.uuid4())
            db.collection("ai_conversations").document(conv_id).set({
                "conversation_id": conv_id,
                "uid": uid,
                "user_message": user_message,
                "agent_response": agent_response,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")

    @staticmethod
    def chat(uid, user_query):
        """
        Orchestration workflow:
        User Query -> Select Relevant Agents -> Combine Reports -> Gemini Synthesis -> Final Response
        """
        try:
            # 1. Determine relevant sub-agents based on query keywords
            query_lower = user_query.lower()
            selected_agents = []

            # Routing rules
            if any(k in query_lower for k in ["expense", "spend", "bought", "purchase", "anomaly", "pattern", "trend"]):
                selected_agents.append(ExpenseAgent)
            if any(k in query_lower for k in ["budget", "limit", "exceed", "exhaust", "spent"]):
                selected_agents.append(BudgetAgent)
            if any(k in query_lower for k in ["saving", "goal", "target", "deadline"]):
                selected_agents.append(SavingsAgent)
            if any(k in query_lower for k in ["insight", "recommend", "advice", "optimize", "save money"]):
                selected_agents.append(InsightsAgent)
            if any(k in query_lower for k in ["student", "hostel", "pocket", "roommate", "mess", "college", "campus"]):
                selected_agents.append(FinanceCoachAgent)
            if any(k in query_lower for k in ["forecast", "predict", "future", "end of month", "projection"]):
                selected_agents.append(ForecastingAgent)
            if any(k in query_lower for k in ["health", "score", "grade", "wellness", "rating"]):
                selected_agents.append(HealthScoreAgent)

            # If no agent was selected (broad or general query), run a general comprehensive scan
            if not selected_agents:
                # Default to main dashboards insights & score
                selected_agents = [HealthScoreAgent, InsightsAgent, ExpenseAgent]

            # 2. Coordinate responses
            agent_reports = []
            for agent in selected_agents:
                try:
                    report = agent.analyze(uid)
                    agent_reports.append(report)
                except Exception as ex:
                    logger.error(f"Failed analysis run on {agent.__name__}: {str(ex)}")

            # 3. Format the context for Gemini
            context_blocks = []
            for r in agent_reports:
                agent_name = r.get("agent", "Unknown Agent")
                context_blocks.append(f"### Report from {agent_name}:\n{str(r)}")

            combined_context = "\n\n".join(context_blocks)

            # 4. Generate final synthesized response from Gemini AI
            prompt = f"""
You are the advanced Agentic AI Financial Advisor for the 'MyBudget' app.
A user has asked a query, and we have run specialized database analysis agents to fetch relevant financial summaries.

User Query: "{user_query}"

Analyze the sub-agent reports below and synthesize a friendly, clear, and actionable response.

Formatting Rules:
1. Tone: Energetic, encouraging, and clear (like a friendly financial coach).
2. Emojis: Enrich the response with relevant emojis to make it highly engaging and visually appealing (e.g., 💸, 📊, 🎯, 🚀, 💡, 🛡️, ✅).
3. Bullet Points: Use clear bullet points and bold headers to break down recommendations. Avoid long paragraphs.
4. Further Related Questions: At the very end of your response, create a section titled "🔍 Further Questions You Can Ask:" with exactly 3 relevant, contextual follow-up questions that the user can ask next based on their current state and query.

Special Context:
{combined_context}

Format your response using Markdown.
"""
            final_response = AIService.generate_content(prompt)

            # 5. Store conversation memory
            OrchestratorAgent.save_conversation(uid, user_query, final_response)

            return {
                "user_query": user_query,
                "response": final_response,
                "triggered_agents": [agent.__name__ for agent in selected_agents]
            }
        except Exception as e:
            logger.error(f"Orchestrator chat workflow failure: {str(e)}")
            raise e
