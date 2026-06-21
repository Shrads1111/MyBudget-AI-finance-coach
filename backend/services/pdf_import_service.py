import os
import re
import json
import logging
from datetime import datetime
import pdfplumber
import fitz  # PyMuPDF
from services.ai_service import AIService
from services.expense_service import ExpenseService

logger = logging.getLogger(__name__)

class PDFImportService:
    @staticmethod
    def extract_text(file_path):
        """
        Attempts to extract text from a PDF file using:
        1. pdfplumber (native text)
        2. fitz/PyMuPDF (native text fallback)
        3. easyocr (OCR fallback for scanned/image PDFs)
        """
        text = ""

        # 1. Try pdfplumber
        try:
            logger.info("Attempting text extraction with pdfplumber...")
            with pdfplumber.open(file_path) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                text = "\n".join(pages_text).strip()
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}")

        # 2. Try fitz (PyMuPDF) if pdfplumber failed or yielded very little text
        if len(text) < 50:
            try:
                logger.info("Attempting text extraction with PyMuPDF...")
                doc = fitz.open(file_path)
                pages_text = []
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        pages_text.append(page_text)
                text = "\n".join(pages_text).strip()
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {str(e)}")

        # 3. Try EasyOCR fallback if text is still empty
        if len(text) < 50:
            try:
                logger.info("Attempting OCR fallback with EasyOCR...")
                import easyocr
                import numpy as np

                reader = easyocr.Reader(['en'], gpu=False) # run on CPU
                doc = fitz.open(file_path)
                ocr_pages = []
                
                for i, page in enumerate(doc):
                    logger.info(f"OCRing page {i+1}/{len(doc)}...")
                    pix = page.get_pixmap(dpi=150) # render page image
                    # Convert to numpy array directly from pixels
                    img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
                    # EasyOCR can read from numpy array directly
                    result = reader.readtext(img_data, detail=0)
                    page_text = " ".join(result)
                    if page_text:
                        ocr_pages.append(page_text)
                text = "\n".join(ocr_pages).strip()
            except ImportError:
                logger.warning("EasyOCR is not installed. Skipping OCR fallback.")
            except Exception as e:
                logger.error(f"EasyOCR fallback failed: {str(e)}")

        return text

    @staticmethod
    def parse_transactions(text):
        """
        Sends extracted PDF text to Gemini to parse transactions.
        """
        if not text or len(text) < 10:
            return []

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        prompt = f"""You are a financial transaction parser for MyBudget.
Parse the following raw text extracted from a PDF statement and extract all transactions.

Today's date is: {today_str}

RULES:
1. Return ONLY a valid JSON array of objects. No markdown fences, no explanation, no headers.
2. Each object MUST have these exact fields:
   - "date": YYYY-MM-DD format (infer the year from statement context if missing).
   - "description": Description/merchant name (e.g. Swiggy, Uber, Amazon, Salary, Rent).
   - "amount": Positive float/integer representing the amount.
   - "type": "expense" or "income".
   - "category": Match the category to one of these:
     - For expense: Food, Travel, Shopping, Bills, Health, Entertainment, Education, Investment, Others
     - For income: Salary, Freelancing, Refund, Interest, Bonus, Other Income
3. Do not include balance updates, summary totals, account numbers, or failure logs.
4. If no transactions are found, return an empty array: [].

Text to parse:
\"\"\"{text[:50000]}\"\"\"
"""

        try:
            # Use gemini-flash-lite-latest for high rate limit capacity
            raw_response = AIService.generate_content(prompt, model_name="gemini-flash-lite-latest")
            raw_response = raw_response.strip()

            # Clean markdown code block wraps if Gemini returns them
            if raw_response.startswith("```"):
                raw_response = re.sub(r"```(?:json)?\s*", "", raw_response).strip("`\n ")

            transactions = json.loads(raw_response)
            if not isinstance(transactions, list):
                return []
            
            # Normalize and filter
            cleaned = []
            for tx in transactions:
                amount_raw = tx.get("amount")
                try:
                    amount = float(amount_raw)
                    if amount <= 0:
                        continue
                except (TypeError, ValueError):
                    continue

                desc = str(tx.get("description", "")).strip()
                if not desc:
                    desc = "Transaction"

                date_val = str(tx.get("date", today_str)).strip()
                try:
                    datetime.strptime(date_val, "%Y-%m-%d")
                except ValueError:
                    date_val = today_str

                txn_type = str(tx.get("type", "expense")).lower()
                if txn_type not in ("income", "expense"):
                    txn_type = "expense"

                category = str(tx.get("category", "Others")).strip()
                
                cleaned.append({
                    "date": date_val,
                    "description": desc,
                    "amount": round(amount, 2),
                    "type": txn_type,
                    "category": category
                })
            return cleaned
        except Exception as e:
            logger.error(f"Failed to parse transactions with AI: {str(e)}")
            return []

    @staticmethod
    def detect_duplicates(uid, transactions):
        """
        Compares each parsed transaction against user's existing Firestore transactions.
        Matches on same date, amount, and similar description.
        """
        if not transactions:
            return []

        try:
            # Fetch user's existing transactions
            existing = ExpenseService.get_expenses(uid, limit=10000)["expenses"]
        except Exception as e:
            logger.error(f"Duplicate check failed: could not fetch expenses: {str(e)}")
            existing = []

        # Index existing transactions by (date, amount) for O(1) checks
        existing_map = {}
        for ext in existing:
            key = (ext["date"], float(ext["amount"]))
            existing_map.setdefault(key, []).append(ext["description"].lower())

        for tx in transactions:
            key = (tx["date"], float(tx["amount"]))
            is_possible = False
            if key in existing_map:
                desc_lower = tx["description"].lower()
                for ext_desc in existing_map[key]:
                    # Flag if descriptions are identical or contain each other
                    if desc_lower == ext_desc or desc_lower in ext_desc or ext_desc in desc_lower or desc_lower[:10] == ext_desc[:10]:
                        is_possible = True
                        break
            tx["is_possible_duplicate"] = is_possible

        return transactions
