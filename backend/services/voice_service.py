import json
import re
import logging
from datetime import datetime, timedelta
from services.ai_service import AIService

logger = logging.getLogger(__name__)


def _build_prompt(transcript: str, today_str: str) -> str:
    return f"""You are a financial transaction parser for MyBudget, an Indian budgeting app.

Parse the user's natural language voice transcript and extract transaction details.
The transcript may contain one or multiple transactions, daily summaries, weekly spending, mixed income and expense narration, or long conversations.
Supports English, Hindi, and Hinglish (mixed).

Today's date is: {today_str}

RULES:
1. Return ONLY valid JSON. No markdown, no code fences (like ```json), no explanation.
2. Under "transactions", return an array of transaction objects.
3. For each transaction object, extract:
   - "amount": positive number. If the amount is missing or unclear for a particular transaction, set it to null.
   - "type": "expense" (for spent/paid/kharch/kharcha/bought/lent/borrowed/loss) or "income" (for salary/received/mila/aaya/credited/earned).
   - "category": choose the best match from:
     * Expense categories: [Food, Travel, Shopping, Bills, Health, Entertainment, Education, Investment, Others]
     * Income categories: [Salary, Freelancing, Refund, Interest, Bonus, Other Income]
     or infer a sensible category name if none fit perfectly.
   - "date": output as YYYY-MM-DD. Resolve relative terms:
     "today"/"aaj" → {today_str}.
     "yesterday"/"kal" → {(datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")}.
     Convert any other relative days (e.g. "day before yesterday", "last Friday") relative to {today_str}.
     If no date is mentioned in a transaction, default to {today_str}.
   - "note": short human-readable description of what was bought or received. E.g. "breakfast", "auto ride", "books", "money from dad".
   - "merchant": the merchant or payee if mentioned (e.g. "Amazon", "Swiggy", "Zomato", "Starbucks", "Dad", "Uber"), otherwise null.
   - "friend_name": if someone owes the user money, their first name. Else null.
   - "friend_owe_amount": the amount that friend owes. Else null.
4. If no transactions are found or the input is completely unintelligible, set "clarification_needed": true and provide a helpful "clarification_message". Otherwise, set "clarification_needed": false.

User input: "{transcript}"

Return exactly this JSON structure (fill in all fields):
{{
  "transactions": [
    {{
      "amount": <number or null>,
      "type": "expense",
      "category": "<string>",
      "date": "<YYYY-MM-DD>",
      "note": "<string>",
      "merchant": "<string or null>",
      "friend_name": "<string or null>",
      "friend_owe_amount": <number or null>
    }}
  ],
  "clarification_needed": false,
  "clarification_message": null
}}"""


class VoiceService:

    @staticmethod
    def parse_transcript(transcript: str) -> dict:
        """
        Parses a natural language transcript into structured transactions.
        Returns a dict containing 'transactions', 'clarification_needed', and 'clarification_message'.
        """
        if not transcript or not transcript.strip():
            return {
                "transactions": [],
                "clarification_needed": True,
                "clarification_message": "No speech was detected. Please try speaking again."
            }

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        prompt = _build_prompt(transcript.strip(), today_str)

        try:
            raw = AIService.generate_content(prompt, model_name="gemini-2.5-flash")
            raw = raw.strip()

            # Strip markdown code fences if Gemini wraps its response
            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?\s*", "", raw).strip("`\n ")

            parsed = json.loads(raw)
            if isinstance(parsed, list):
                parsed = {
                    "transactions": parsed,
                    "clarification_needed": False,
                    "clarification_message": None
                }
            elif isinstance(parsed, dict) and "transactions" not in parsed:
                if "amount" in parsed or "note" in parsed or "type" in parsed:
                    parsed = {
                        "transactions": [parsed],
                        "clarification_needed": parsed.get("clarification_needed", False),
                        "clarification_message": parsed.get("clarification_message")
                    }
                else:
                    parsed = {
                        "transactions": [],
                        "clarification_needed": parsed.get("clarification_needed", True),
                        "clarification_message": parsed.get("clarification_message")
                    }
        except json.JSONDecodeError:
            logger.error(f"Voice parse: Gemini returned non-JSON response for transcript: '{transcript}'")
            return {
                "transactions": [],
                "clarification_needed": True,
                "clarification_message": "I couldn't understand that. Please try again or use manual entry."
            }
        except Exception as e:
            logger.error(f"Voice parse: AI call failed: {str(e)}")
            return {
                "transactions": [],
                "clarification_needed": True,
                "clarification_message": "Voice parsing is temporarily unavailable. Please use manual entry."
            }

        # If AI itself flagged clarification needed
        if parsed.get("clarification_needed"):
            return {
                "transactions": [],
                "clarification_needed": True,
                "clarification_message": parsed.get("clarification_message") or
                    "I couldn't identify the transaction details. Please describe them more clearly."
            }

        txs = parsed.get("transactions", [])
        if not txs:
            return {
                "transactions": [],
                "clarification_needed": True,
                "clarification_message": "I couldn't find any transaction details. Please specify an amount and category."
            }

        validated_txs = []
        for tx in txs:
            # Validate amount
            amount_raw = tx.get("amount")
            amount = None
            if amount_raw is not None:
                try:
                    amount = float(amount_raw)
                    if amount <= 0:
                        amount = None
                except (TypeError, ValueError):
                    amount = None

            # Normalize type
            txn_type = str(tx.get("type", "expense")).lower()
            if txn_type not in ("income", "expense"):
                txn_type = "expense"

            # Normalize category
            category = str(tx.get("category", "Others")).strip() or "Others"

            # Normalize date
            date_val = str(tx.get("date", today_str)).strip()
            relative_map = {
                "today": today_str, "aaj": today_str,
                "yesterday": (datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d"),
                "kal": (datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d"),
            }
            date_val = relative_map.get(date_val.lower(), date_val)
            try:
                datetime.strptime(date_val, "%Y-%m-%d")
            except ValueError:
                date_val = today_str

            note = str(tx.get("note", "")).strip() or "Voice Transaction"
            merchant = tx.get("merchant") or None
            if merchant:
                merchant = str(merchant).strip()

            # Friend details
            friend_name = tx.get("friend_name") or None
            if friend_name:
                friend_name = str(friend_name).strip()
            friend_owe_raw = tx.get("friend_owe_amount")
            friend_owe_amount = None
            if friend_owe_raw is not None:
                try:
                    friend_owe_amount = float(friend_owe_raw)
                except (TypeError, ValueError):
                    friend_owe_amount = None

            validated_txs.append({
                "amount": amount,
                "type": txn_type,
                "category": category,
                "date": date_val,
                "note": note,
                "merchant": merchant,
                "friend_name": friend_name,
                "friend_owe_amount": friend_owe_amount
            })

        return {
            "transactions": validated_txs,
            "clarification_needed": False,
            "clarification_message": None
        }

