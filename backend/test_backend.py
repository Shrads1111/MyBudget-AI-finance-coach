import unittest
from unittest.mock import patch, MagicMock
import json
from app import create_app
from services.firebase_service import FirebaseService

class MyBudgetBackendTestCase(unittest.TestCase):
    def setUp(self):
        # Set testing configuration
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Mock Firebase Firestore database references
        self.db_mock = MagicMock()
        FirebaseService._db = self.db_mock
        FirebaseService._initialized = True

        # Keep a registry of mocked firestore collections & documents
        self.firestore_db = {}

        class MockQuery:
            def __init__(self, col_name, db_data, filters=None, orders=None, limit_val=None, offset_val=None, select_fields=None):
                self.col_name = col_name
                self.db_data = db_data
                self.filters = filters or []
                self.orders = orders or []
                self.limit_val = limit_val
                self.offset_val = offset_val
                self.select_fields = select_fields

            def where(self, field, op, val):
                new_filters = list(self.filters)
                new_filters.append((field, op, val))
                return MockQuery(self.col_name, self.db_data, new_filters, self.orders, self.limit_val, self.offset_val, self.select_fields)

            def order_by(self, field, direction="ASCENDING"):
                new_orders = list(self.orders)
                new_orders.append((field, direction))
                return MockQuery(self.col_name, self.db_data, self.filters, new_orders, self.limit_val, self.offset_val, self.select_fields)

            def limit(self, count):
                return MockQuery(self.col_name, self.db_data, self.filters, self.orders, count, self.offset_val, self.select_fields)

            def offset(self, num):
                return MockQuery(self.col_name, self.db_data, self.filters, self.orders, self.limit_val, num, self.select_fields)

            def select(self, fields):
                return MockQuery(self.col_name, self.db_data, self.filters, self.orders, self.limit_val, self.offset_val, fields)

            def count(self):
                class MockCountQuery:
                    def __init__(self, count_val):
                        self.count_val = count_val
                    def get(self):
                        class MultiIndexMock:
                            def __init__(self, val):
                                self.value = val
                            def __getitem__(self, idx):
                                return self
                        return [MultiIndexMock(self.count_val)]
                matching_count = len(self._get_matching_docs())
                return MockCountQuery(matching_count)

            def _get_matching_docs(self):
                docs = []
                if self.col_name in self.db_data:
                    for d_id, data in self.db_data[self.col_name].items():
                        match = True
                        for field, op, val in self.filters:
                            if field not in data:
                                match = False
                                break
                            actual_val = data[field]
                            if op == "==":
                                if actual_val != val:
                                    match = False
                                    break
                            elif op == ">=":
                                if actual_val < val:
                                    match = False
                                    break
                            elif op == "<=":
                                if actual_val > val:
                                    match = False
                                    break
                            elif op == "array-contains":
                                if not isinstance(actual_val, list) or val not in actual_val:
                                    match = False
                                    break
                            elif op == "in":
                                if actual_val not in val:
                                    match = False
                                    break
                        if match:
                            docs.append((d_id, data))
                return docs

            def stream(self):
                docs = self._get_matching_docs()

                # Apply sorting (reverse sorting if DESCENDING)
                for field, direction in reversed(self.orders):
                    reverse_sort = (direction == "DESCENDING")
                    def get_sort_key(x):
                        val = x[1].get(field)
                        if val is None:
                            return ""
                        return val
                    docs.sort(key=get_sort_key, reverse=reverse_sort)

                # Wrap in MagicMock
                wrapped_docs = []
                for d_id, data in docs:
                    d_mock = MagicMock()
                    d_mock.to_dict.return_value = data
                    d_mock.id = d_id
                    wrapped_docs.append(d_mock)

                # Apply offset and limit
                if self.offset_val is not None:
                    wrapped_docs = wrapped_docs[self.offset_val:]
                if self.limit_val is not None:
                    wrapped_docs = wrapped_docs[:self.limit_val]

                return wrapped_docs

        # Set up a helper for firestore mocks
        def mock_collection(col_name):
            col_mock = MagicMock()
            
            def mock_document(doc_id=None):
                if not doc_id:
                    # Generate a random ID
                    import uuid
                    doc_id = str(uuid.uuid4())
                
                doc_mock = MagicMock()
                
                def set_data(data_dict, merge=False):
                    if col_name not in self.firestore_db:
                        self.firestore_db[col_name] = {}
                    self.firestore_db[col_name][doc_id] = data_dict
                    return MagicMock()
                
                def update_data(update_dict):
                    if col_name in self.firestore_db and doc_id in self.firestore_db[col_name]:
                        self.firestore_db[col_name][doc_id].update(update_dict)
                    return MagicMock()

                def delete_doc():
                    if col_name in self.firestore_db and doc_id in self.firestore_db[col_name]:
                        del self.firestore_db[col_name][doc_id]
                    return MagicMock()

                def get_doc():
                    get_mock = MagicMock()
                    exists = col_name in self.firestore_db and doc_id in self.firestore_db[col_name]
                    get_mock.exists = exists
                    if exists:
                        get_mock.to_dict.return_value = self.firestore_db[col_name][doc_id]
                    else:
                        get_mock.to_dict.return_value = {}
                    return get_mock

                doc_mock.set = set_data
                doc_mock.update = update_data
                doc_mock.delete = delete_doc
                doc_mock.get = get_doc
                return doc_mock

            col_mock.document = mock_document
            col_mock.where = lambda f, o, v: MockQuery(col_name, self.firestore_db).where(f, o, v)
            col_mock.order_by = lambda f, d="ASCENDING": MockQuery(col_name, self.firestore_db).order_by(f, d)
            col_mock.limit = lambda c: MockQuery(col_name, self.firestore_db).limit(c)
            col_mock.offset = lambda n: MockQuery(col_name, self.firestore_db).offset(n)
            col_mock.select = lambda f: MockQuery(col_name, self.firestore_db).select(f)
            col_mock.stream = lambda: MockQuery(col_name, self.firestore_db).stream()
            return col_mock

        self.db_mock.collection = mock_collection

        # Patch token verification so all requests have test-uid
        self.auth_patcher = patch('services.firebase_service.FirebaseService.verify_id_token')
        self.mock_verify = self.auth_patcher.start()
        self.mock_verify.return_value = {
            "uid": "test-user-123",
            "email": "test@student.edu"
        }

        # Header for client request authentication
        self.headers = {
            "Authorization": "Bearer test-valid-token"
        }

    def tearDown(self):
        self.auth_patcher.stop()

    def test_health_check(self):
        """Test health check route"""
        response = self.client.get('/health')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')

    def test_sync_user(self):
        """Test user sync route"""
        response = self.client.post('/api/users/sync', headers=self.headers)
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['uid'], 'test-user-123')
        self.assertEqual(data['email'], 'test@student.edu')

    def test_expenses_crud(self):
        """Test complete Expenses CRUD flow"""
        # Create
        expense_payload = {
            "amount": 250.0,
            "category": "Food",
            "description": "Lunch at hostel canteen",
            "date": "2026-06-20"
        }
        res_create = self.client.post('/api/expenses', headers=self.headers, json=expense_payload)
        data_create = json.loads(res_create.data)
        self.assertEqual(res_create.status_code, 201)
        self.assertIn("expense_id", data_create)
        self.assertEqual(data_create["amount"], 250.0)
        self.assertEqual(data_create["category"], "Food")
        
        expense_id = data_create["expense_id"]

        # Read detail
        res_get = self.client.get(f'/api/expenses/{expense_id}', headers=self.headers)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(json.loads(res_get.data)["description"], "Lunch at hostel canteen")

        # List
        res_list = self.client.get('/api/expenses', headers=self.headers)
        data_list = json.loads(res_list.data)
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(data_list["total"], 1)

        # Update
        res_update = self.client.put(f'/api/expenses/{expense_id}', headers=self.headers, json={"amount": 300.0})
        self.assertEqual(res_update.status_code, 200)
        self.assertEqual(json.loads(res_update.data)["amount"], 300.0)

        # Delete
        res_delete = self.client.delete(f'/api/expenses/{expense_id}', headers=self.headers)
        self.assertEqual(res_delete.status_code, 200)

        # Verify deletion
        res_get_deleted = self.client.get(f'/api/expenses/{expense_id}', headers=self.headers)
        self.assertEqual(res_get_deleted.status_code, 404)

    def test_budgets_crud_and_alerts(self):
        """Test Budgets CRUD, remaining limit checks, and utilization alerts"""
        # Create a budget
        budget_payload = {
            "category": "Food",
            "limit": 1000.0,
            "month": "2026-06"
        }
        res_create = self.client.post('/api/budgets', headers=self.headers, json=budget_payload)
        data_create = json.loads(res_create.data)
        self.assertEqual(res_create.status_code, 201)
        self.assertEqual(data_create["limit"], 1000.0)
        self.assertEqual(data_create["spent"], 0.0)
        self.assertEqual(data_create["remaining"], 1000.0)

        budget_id = data_create["budget_id"]

        # Add an expense of ₹850 to trigger 80% and 90% warnings
        expense_payload = {
            "amount": 850.0,
            "category": "Food",
            "description": "Weekly grocery list",
            "date": "2026-06-15"
        }
        self.client.post('/api/expenses', headers=self.headers, json=expense_payload)

        # Fetch budgets to check sync / alerts
        res_list = self.client.get('/api/budgets', headers=self.headers)
        data_list = json.loads(res_list.data)
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(data_list[0]["spent"], 850.0)
        self.assertEqual(data_list[0]["remaining"], 150.0)

        # Check remaining endpoint
        res_rem = self.client.get(f'/api/budgets/{budget_id}/remaining', headers=self.headers)
        data_rem = json.loads(res_rem.data)
        self.assertEqual(res_rem.status_code, 200)
        self.assertEqual(data_rem["remaining"], 150.0)

        # Check alerts endpoint
        res_alerts = self.client.get('/api/budgets/alerts', headers=self.headers)
        data_alerts = json.loads(res_alerts.data)
        self.assertEqual(res_alerts.status_code, 200)
        self.assertTrue(len(data_alerts) > 0)
        self.assertEqual(data_alerts[0]["category"], "Food")
        self.assertEqual(data_alerts[0]["percentage"], 85.0)

    def test_savings_goals(self):
        """Test Savings Goals progress estimation"""
        goal_payload = {
            "goal_name": "New Gaming Laptop",
            "target_amount": 50000.0,
            "current_amount": 10000.0,
            "deadline": "2026-12-25"
        }
        res_create = self.client.post('/api/goals', headers=self.headers, json=goal_payload)
        data_create = json.loads(res_create.data)
        self.assertEqual(res_create.status_code, 201)
        self.assertEqual(data_create["progress_percentage"], 20.0)
        self.assertEqual(data_create["remaining_amount"], 40000.0)
        
        goal_id = data_create["goal_id"]

        # Fetch progress details
        res_prog = self.client.get(f'/api/goals/{goal_id}/progress', headers=self.headers)
        data_prog = json.loads(res_prog.data)
        self.assertEqual(res_prog.status_code, 200)
        self.assertEqual(data_prog["remaining_amount"], 40000.0)
        self.assertGreater(data_prog["monthly_saving_needed"], 0)

    def test_group_budgets(self):
        """Test Group creations, adding members, splitting, and settle suggest algorithm"""
        # Seed test user profiles in the mocked firestore
        db = FirebaseService.get_db()
        db.collection("users").document("test-user-123").set({
            "uid": "test-user-123",
            "email": "test@student.edu",
            "display_name": "Test User"
        })
        db.collection("users").document("roommate-aman").set({
            "uid": "roommate-aman",
            "email": "aman@student.edu",
            "display_name": "Aman Roommate"
        })
        db.collection("users").document("roommate-riya").set({
            "uid": "roommate-riya",
            "email": "riya@student.edu",
            "display_name": "Riya Roommate"
        })

        # 1. Create group
        group_payload = {
            "group_name": "Flat 202 - Rent & WiFi",
            "members": ["test-user-123", "roommate-aman"]
        }
        res_create = self.client.post('/api/groups', headers=self.headers, json=group_payload)
        data_create = json.loads(res_create.data)
        self.assertEqual(res_create.status_code, 201)
        self.assertEqual(data_create["group_name"], "Flat 202 - Rent & WiFi")
        self.assertEqual(len(data_create["members"]), 2)

        group_id = data_create["group_id"]

        # 2. Invite third member (which resolves to roommate-riya)
        res_invite = self.client.post('/api/groups/invite', headers=self.headers, json={
            "group_id": group_id,
            "member": "roommate-riya"
        })
        self.assertEqual(res_invite.status_code, 200)
        self.assertEqual(len(json.loads(res_invite.data)["members"]), 3)

        # 3. Add group expense: Creator pays ₹300 for WiFi split with all 3 members equally
        exp_payload = {
            "group_id": group_id,
            "expense": {
                "amount": 300.0,
                "description": "WiFi Router Bill",
                "paid_by": "test-user-123",
                "split_type": "equal",
                "split_with": ["test-user-123", "roommate-aman", "roommate-riya"]
            }
        }
        res_exp = self.client.post('/api/groups/expense', headers=self.headers, json=exp_payload)
        data_exp = json.loads(res_exp.data)
        self.assertEqual(res_exp.status_code, 201)
        self.assertIn("splits", data_exp)
        self.assertEqual(len(data_exp["splits"]), 3)
        self.assertIn("expenseId", data_exp)
        self.assertIn("groupId", data_exp)
        self.assertIn("paidBy", data_exp)
        self.assertIn("participants", data_exp)
        self.assertIn("createdAt", data_exp)
        expense_id = data_exp["expense_id"]

        # Verify normal expense transaction was created for the payer
        res_expenses = self.client.get('/api/expenses', headers=self.headers)
        data_expenses = json.loads(res_expenses.data)
        self.assertTrue(any("WiFi Router Bill" in e.get("description", "") for e in data_expenses.get("expenses", [])))

        # 4. Get Summary - initial state (unpaid splits)
        res_sum = self.client.get(f'/api/groups/{group_id}/summary', headers=self.headers)
        data_sum = json.loads(res_sum.data)
        self.assertEqual(res_sum.status_code, 200)
        self.assertEqual(data_sum["total_spending"], 300.0)
        self.assertEqual(data_sum["per_person_share"], 100.0)
        # test-user-123 paid 300, owes 100 -> balance +200
        # roommate-aman paid 0, owes 100 -> balance -100
        # roommate-riya paid 0, owes 100 -> balance -100
        self.assertEqual(data_sum["balances"]["test-user-123"], 200.0)
        self.assertEqual(data_sum["balances"]["roommate-aman"], -100.0)
        self.assertEqual(data_sum["balances"]["roommate-riya"], -100.0)
        
        # Verify initial suggested settlements
        settlements = data_sum["suggested_settlements"]
        self.assertEqual(len(settlements), 2)

        # Verify dashboard summary calculations
        res_dash = self.client.get('/api/dashboard/summary', headers=self.headers)
        data_dash = json.loads(res_dash.data)
        self.assertEqual(res_dash.status_code, 200)
        self.assertEqual(data_dash["summary"]["friend_owe_you"], 200.0)
        self.assertEqual(data_dash["summary"]["friend_you_owe"], 0.0)
        self.assertEqual(data_dash["summary"]["friend_net"], 200.0)
        
        # 5. roommate-riya pays their share
        with patch('services.firebase_service.FirebaseService.verify_id_token', return_value={"uid": "roommate-riya", "email": "riya@student.edu"}):
            res_pay = self.client.post(f'/api/groups/{group_id}/expense/{expense_id}/pay', headers=self.headers)
            self.assertEqual(res_pay.status_code, 200)

        # 6. Get Summary again - roommate-riya is settled (0 balance), test-user-123 is owed +100
        res_sum2 = self.client.get(f'/api/groups/{group_id}/summary', headers=self.headers)
        data_sum2 = json.loads(res_sum2.data)
        self.assertEqual(data_sum2["balances"]["test-user-123"], 100.0)
        self.assertEqual(data_sum2["balances"]["roommate-riya"], 0.0)
        self.assertEqual(data_sum2["balances"]["roommate-aman"], -100.0)

        # 7. Creator (test-user-123) marks roommate-aman as paid
        res_mark = self.client.post(f'/api/groups/{group_id}/expense/{expense_id}/mark-paid', headers=self.headers, json={
            "member_uid": "roommate-aman"
        })
        self.assertEqual(res_mark.status_code, 200)

        # 8. Get Summary again - everyone is fully settled
        res_sum3 = self.client.get(f'/api/groups/{group_id}/summary', headers=self.headers)
        data_sum3 = json.loads(res_sum3.data)
        self.assertEqual(data_sum3["balances"]["test-user-123"], 0.0)
        self.assertEqual(data_sum3["balances"]["roommate-aman"], 0.0)
        self.assertEqual(data_sum3["balances"]["roommate-riya"], 0.0)
        self.assertEqual(len(data_sum3["suggested_settlements"]), 0)

    @patch('services.ai_service.AIService.generate_content')
    def test_group_expense_parse_ai(self, mock_gemini):
        """Test AI natural language parsing for group expense"""
        # Scenario 1: Clean parsing with exact name/email/UID matching
        mock_gemini.return_value = json.dumps({
            "payer": "Aman Roommate",
            "amount": 300,
            "category": "Food",
            "description": "lunch",
            "participants": ["Test User", "aman@student.edu"],
            "confidence": 0.9
        })
        
        # Seed test user profiles in the mocked firestore
        db = FirebaseService.get_db()
        db.collection("users").document("test-user-123").set({
            "uid": "test-user-123",
            "email": "test@student.edu",
            "display_name": "Test User"
        })
        db.collection("users").document("roommate-aman").set({
            "uid": "roommate-aman",
            "email": "aman@student.edu",
            "display_name": "Aman Roommate"
        })

        group_payload = {
            "group_name": "Goa Trip",
            "members": ["test-user-123", "roommate-aman"]
        }
        res_create = self.client.post('/api/groups', headers=self.headers, json=group_payload)
        group_id = json.loads(res_create.data)["group_id"]
        
        res_parse = self.client.post(f'/api/groups/{group_id}/parse-expense', headers=self.headers, json={
            "query": "Aman paid 300 for lunch"
        })
        self.assertEqual(res_parse.status_code, 200)
        data_parse = json.loads(res_parse.data)
        self.assertEqual(data_parse["payer"], "roommate-aman")  # Resolved Aman Roommate -> roommate-aman
        self.assertEqual(data_parse["amount"], 300)
        self.assertEqual(data_parse["category"], "Food")
        self.assertEqual(data_parse["description"], "lunch")
        self.assertEqual(set(data_parse["participants"]), {"test-user-123", "roommate-aman"})
        self.assertEqual(data_parse["needs_confirmation"], False)

        # Scenario 2: Substring matching and non-member exclusion/low confidence
        mock_gemini.return_value = json.dumps({
            "payer": "Aman",
            "amount": 300,
            "category": "Food",
            "description": "lunch",
            "participants": ["Test User", "Unknown Person"],
            "confidence": 0.5
        })
        res_parse2 = self.client.post(f'/api/groups/{group_id}/parse-expense', headers=self.headers, json={
            "query": "Aman paid 300 for lunch with Unknown"
        })
        self.assertEqual(res_parse2.status_code, 200)
        data_parse2 = json.loads(res_parse2.data)
        self.assertEqual(data_parse2["payer"], "roommate-aman")  # Resolved Aman -> roommate-aman
        self.assertEqual(data_parse2["participants"], ["test-user-123"])  # Unknown Person filtered out
        self.assertEqual(data_parse2["needs_confirmation"], True)  # Low confidence and missing/unresolved participants

    @patch('services.ai_service.AIService.generate_content')
    def test_ai_advisor_and_chat(self, mock_gemini):
        """Test AI advisor generation and coordinated chat endpoints with Mock Gemini"""
        mock_gemini.return_value = "This is a mocked AI response advising you to save more."

        # Test Analyze endpoint
        res_analyze = self.client.post('/api/ai/analyze', headers=self.headers)
        data_analyze = json.loads(res_analyze.data)
        self.assertEqual(res_analyze.status_code, 200)
        self.assertIn("advisory_report", data_analyze)
        self.assertEqual(data_analyze["advisory_report"], "This is a mocked AI response advising you to save more.")

        # Test Chat endpoint
        chat_payload = {
            "query": "How is my budget doing? Am I overspending?"
        }
        res_chat = self.client.post('/api/ai/chat', headers=self.headers, json=chat_payload)
        data_chat = json.loads(res_chat.data)
        self.assertEqual(res_chat.status_code, 200)
        self.assertEqual(data_chat["response"], "This is a mocked AI response advising you to save more.")
        self.assertTrue(len(data_chat["triggered_agents"]) > 0)

    @patch('services.ai_service.AIService.generate_content')
    def test_new_features_phase_4_5(self, mock_gemini):
        """Test Health Score, Goal Planner, Pattern Detection, Report and Simulator endpoints"""
        mock_gemini.return_value = "Mocked simulation explanation."

        # Setup base data (expense, budget, goal)
        self.client.post('/api/expenses', headers=self.headers, json={
            "amount": 5000.0,
            "category": "Income",
            "description": "Stipend",
            "date": "2026-06-01"
        })
        self.client.post('/api/expenses', headers=self.headers, json={
            "amount": 1000.0,
            "category": "Food",
            "description": "Groceries",
            "date": "2026-06-05"
        })
        res_goal = self.client.post('/api/goals', headers=self.headers, json={
            "goal_name": "New Laptop",
            "target_amount": 12000.0,
            "current_amount": 2000.0,
            "deadline": "2026-10-01"
        })
        goal_id = json.loads(res_goal.data)["goal_id"]

        # 1. Health Score
        res_health = self.client.get('/api/health-score', headers=self.headers)
        data_health = json.loads(res_health.data)
        self.assertEqual(res_health.status_code, 200)
        self.assertIn("score", data_health)
        self.assertIn("breakdown", data_health)

        # 2. Goal Planner
        res_plan = self.client.get(f'/api/goals/{goal_id}/planner', headers=self.headers)
        data_plan = json.loads(res_plan.data)
        self.assertEqual(res_plan.status_code, 200)
        self.assertIn("monthly_target", data_plan)
        self.assertEqual(data_plan["remaining_amount"], 10000.0)
        self.assertIn("ai_advice", data_plan)
        self.assertEqual(data_plan["ai_advice"], "Mocked simulation explanation.")

        # 3. Pattern Detection
        res_pattern = self.client.get('/api/analytics/patterns', headers=self.headers)
        data_pattern = json.loads(res_pattern.data)
        self.assertEqual(res_pattern.status_code, 200)
        self.assertTrue(len(data_pattern) > 0)

        # 4. Report PDF
        res_report = self.client.get('/api/reports/monthly?month=2026-06', headers=self.headers)
        self.assertEqual(res_report.status_code, 200)
        self.assertEqual(res_report.mimetype, 'application/pdf')

        # 5. AI Simulator
        res_sim = self.client.post('/api/ai/simulate', headers=self.headers, json={
            "query": "If I save 1000 per month, when will I reach 10000?"
        })
        data_sim = json.loads(res_sim.data)
        self.assertEqual(res_sim.status_code, 200)
        self.assertEqual(data_sim["type"], "savings_target")
        self.assertEqual(data_sim["result"]["months_required"], 10.0)

    def test_accounts_endpoints(self):
        # 1. Get accounts (starts empty)
        res = self.client.get('/api/accounts', headers=self.headers)
        data = json.loads(res.data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(data), 0)

        # 2. Add new account
        new_acc = {
            "name": "SBI Bank",
            "type": "Bank",
            "initial_balance": 12000.0,
            "last_details": "•••• 9988"
        }
        res_post = self.client.post('/api/accounts', headers=self.headers, json=new_acc)
        data_post = json.loads(res_post.data)
        self.assertEqual(res_post.status_code, 201)
        self.assertEqual(data_post["name"], "SBI Bank")
        self.assertIn("account_id", data_post)
        acc_id = data_post["account_id"]

        # Verify it is in the list
        res_list = self.client.get('/api/accounts', headers=self.headers)
        data_list = json.loads(res_list.data)
        self.assertEqual(len(data_list), 1)

        # 3. Delete account
        res_del = self.client.delete(f'/api/accounts/{acc_id}', headers=self.headers)
        self.assertEqual(res_del.status_code, 200)
        
        # Verify it is deleted
        res_list2 = self.client.get('/api/accounts', headers=self.headers)
        data_list2 = json.loads(res_list2.data)
        self.assertEqual(len(data_list2), 0)

    def test_group_expense_edit_and_delete(self):
        """Test editing and deleting group expenses and syncing with standard expenses"""
        # Seed users
        db = FirebaseService.get_db()
        db.collection("users").document("test-user-123").set({
            "uid": "test-user-123",
            "email": "test@student.edu",
            "display_name": "Test User"
        })
        db.collection("users").document("roommate-aman").set({
            "uid": "roommate-aman",
            "email": "aman@student.edu",
            "display_name": "Aman Roommate"
        })

        # Create group
        group_payload = {
            "group_name": "Edit Test Group",
            "members": ["test-user-123", "roommate-aman"]
        }
        res_create = self.client.post('/api/groups', headers=self.headers, json=group_payload)
        group_id = json.loads(res_create.data)["group_id"]

        # Add expense: test-user-123 pays 200
        exp_payload = {
            "group_id": group_id,
            "expense": {
                "amount": 200.0,
                "description": "Initial Bill",
                "paid_by": "test-user-123",
                "split_type": "equal",
                "split_with": ["test-user-123", "roommate-aman"]
            }
        }
        res_exp = self.client.post('/api/groups/expense', headers=self.headers, json=exp_payload)
        data_exp = json.loads(res_exp.data)
        self.assertEqual(res_exp.status_code, 201)
        expense_id = data_exp["expense_id"]

        # Verify normal expense exists for test-user-123
        res_expenses = self.client.get('/api/expenses', headers=self.headers)
        data_expenses = json.loads(res_expenses.data)
        self.assertTrue(any(e.get("expense_id") == expense_id for e in data_expenses.get("expenses", [])))

        # Edit expense: change amount to 400, split with aman, description to "Updated Bill"
        edit_payload = {
            "expense": {
                "amount": 400.0,
                "description": "Updated Bill",
                "paid_by": "test-user-123",
                "split_type": "equal",
                "split_with": ["test-user-123", "roommate-aman"]
            }
        }
        res_edit = self.client.put(f'/api/groups/{group_id}/expense/{expense_id}', headers=self.headers, json=edit_payload)
        self.assertEqual(res_edit.status_code, 200)

        # Get summary and verify total spending and per person share
        res_sum = self.client.get(f'/api/groups/{group_id}/summary', headers=self.headers)
        data_sum = json.loads(res_sum.data)
        self.assertEqual(data_sum["total_spending"], 400.0)
        self.assertEqual(data_sum["per_person_share"], 200.0)
        self.assertEqual(data_sum["balances"]["roommate-aman"], -200.0)
        self.assertEqual(data_sum["balances"]["test-user-123"], 200.0)
        # Settlements should explain the flow
        self.assertEqual(len(data_sum["settlements"]), 1)
        self.assertEqual(data_sum["settlements"][0]["from"], "roommate-aman")
        self.assertEqual(data_sum["settlements"][0]["to"], "test-user-123")
        self.assertEqual(data_sum["settlements"][0]["amount"], 200.0)

        # Verify normal expense transaction was updated
        res_expenses = self.client.get('/api/expenses', headers=self.headers)
        data_expenses = json.loads(res_expenses.data)
        updated_exp = next((e for e in data_expenses.get("expenses", []) if e.get("expense_id") == expense_id), None)
        self.assertIsNotNone(updated_exp)
        self.assertEqual(updated_exp["amount"], 400.0)
        self.assertEqual(updated_exp["description"], f"[Edit Test Group] Updated Bill")

        # Now, delete expense
        res_delete = self.client.delete(f'/api/groups/{group_id}/expense/{expense_id}', headers=self.headers)
        self.assertEqual(res_delete.status_code, 200)

        # Get summary again and verify reset
        res_sum2 = self.client.get(f'/api/groups/{group_id}/summary', headers=self.headers)
        data_sum2 = json.loads(res_sum2.data)
        self.assertEqual(data_sum2["total_spending"], 0.0)
        self.assertEqual(data_sum2["balances"]["roommate-aman"], 0.0)
        self.assertEqual(data_sum2["balances"]["test-user-123"], 0.0)

        # Verify normal expense transaction is deleted
        res_expenses2 = self.client.get('/api/expenses', headers=self.headers)
        data_expenses2 = json.loads(res_expenses2.data)
        self.assertFalse(any(e.get("expense_id") == expense_id for e in data_expenses2.get("expenses", [])))

    @patch('google.cloud.firestore.transactional', lambda f: f)
    def test_group_expense_concurrency_safety(self):
        """Test Firestore transaction safety for concurrent writes"""
        # Create a custom db wrapper whose class name doesn't contain 'MagicMock'
        class NonMockDB:
            def __init__(self, mock_collection_fn):
                self.mock_collection_fn = mock_collection_fn
                self.txn_mock = MagicMock()
            def collection(self, name):
                col = self.mock_collection_fn(name)
                # Wrap document get method to accept transaction parameter
                orig_document = col.document
                def wrap_document(*args, **kwargs):
                    doc_mock = orig_document(*args, **kwargs)
                    orig_get = doc_mock.get
                    def wrap_get(*a, **kw):
                        return orig_get()
                    doc_mock.get = wrap_get
                    return doc_mock
                col.document = wrap_document
                return col
            def transaction(self):
                return self.txn_mock

        orig_db = FirebaseService.get_db()
        custom_db = NonMockDB(orig_db.collection)
        FirebaseService._db = custom_db

        try:
            # Seed users
            custom_db.collection("users").document("test-user-123").set({
                "uid": "test-user-123",
                "email": "test@student.edu",
                "display_name": "Test User"
            })
            custom_db.collection("users").document("roommate-aman").set({
                "uid": "roommate-aman",
                "email": "aman@student.edu",
                "display_name": "Aman Roommate"
            })

            # Create group
            group_payload = {
                "group_name": "Concurrency Test Group",
                "members": ["test-user-123", "roommate-aman"]
            }
            res_create = self.client.post('/api/groups', headers=self.headers, json=group_payload)
            group_id = json.loads(res_create.data)["group_id"]

            # Add expense: test-user-123 pays 200
            exp_payload = {
                "group_id": group_id,
                "expense": {
                    "amount": 200.0,
                    "description": "Initial Bill",
                    "paid_by": "test-user-123",
                    "split_type": "equal",
                    "split_with": ["test-user-123", "roommate-aman"]
                }
            }
            res_exp = self.client.post('/api/groups/expense', headers=self.headers, json=exp_payload)
            self.assertEqual(res_exp.status_code, 201)

            # Verify that transaction was retrieved and update was called on the mock transaction
            self.assertTrue(custom_db.txn_mock.update.called)
        finally:
            FirebaseService._db = orig_db

    @patch('google.generativeai.GenerativeModel')
    def test_ai_service_fallback(self, mock_gen_model):
        from services.ai_service import AIService
        
        # Scenario: First model fails, fallback model succeeds
        mock_model_1 = MagicMock()
        mock_model_1.generate_content.side_effect = Exception("Quota Exceeded 429")
        mock_model_2 = MagicMock()
        mock_model_2.generate_content.return_value.text = "Fallback success response"
        
        def side_effect(model_name):
            if model_name == "gemini-2.5-flash":
                return mock_model_1
            elif model_name == "gemini-flash-lite-latest":
                return mock_model_2
            return MagicMock()
            
        mock_gen_model.side_effect = side_effect
        
        AIService._initialized = True
        response = AIService.generate_content("Hello")
        self.assertEqual(response, "Fallback success response")
        
        # Verify both models were instantiated
        mock_gen_model.assert_any_call("gemini-2.5-flash")
        mock_gen_model.assert_any_call("gemini-flash-lite-latest")

    @patch('google.generativeai.GenerativeModel')
    def test_ai_service_primary_success(self, mock_gen_model):
        from services.ai_service import AIService
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "Primary success"
        mock_gen_model.return_value = mock_model
        
        AIService._initialized = True
        response = AIService.generate_content("Hello")
        self.assertEqual(response, "Primary success")
        mock_gen_model.assert_called_once_with("gemini-2.5-flash")

    @patch('google.generativeai.GenerativeModel')
    def test_ai_service_all_fail(self, mock_gen_model):
        from services.ai_service import AIService
        mock_gen_model.return_value.generate_content.side_effect = Exception("Model error")
        
        AIService._initialized = True
        with self.assertRaises(Exception):
            AIService.generate_content("Hello")

    @patch('services.ai_service.AIService.generate_content')
    def test_goal_planner_ai_failure_fallback(self, mock_gemini):
        # Setup goal planner advice to fail
        mock_gemini.side_effect = Exception("Quota error")
        
        res_goal = self.client.post('/api/goals', headers=self.headers, json={
            "goal_name": "Car Goal",
            "target_amount": 50000.0,
            "current_amount": 10000.0,
            "deadline": "2026-12-01"
        })
        self.assertEqual(res_goal.status_code, 201, f"Failed: {res_goal.data}")
        goal_id = json.loads(res_goal.data)["goal_id"]
        
        res_plan = self.client.get(f'/api/goals/{goal_id}/planner', headers=self.headers)
        data_plan = json.loads(res_plan.data)
        self.assertEqual(res_plan.status_code, 200)
        self.assertIn("ai_advice", data_plan)
        self.assertTrue("low" in data_plan["ai_advice"] or "Keep saving" in data_plan["ai_advice"])

    def test_savings_defensive_parsing_missing_fields(self):
        # Directly inject corrupted goal in mock db
        goal_id = "corrupted-goal-123"
        if "savings_goals" not in self.firestore_db:
            self.firestore_db["savings_goals"] = {}
        self.firestore_db["savings_goals"][goal_id] = {
            "goal_id": goal_id,
            "uid": "test-user-123",
            # Missing goal_name, target_amount, current_amount, deadline
        }
        
        # Test that savings service fetch doesn't crash and defaults properties safely
        from services.savings_service import SavingsService
        goals = SavingsService.get_goals("test-user-123")
        corrupted = next(g for g in goals if g["goal_id"] == goal_id)
        self.assertEqual(corrupted["goal_name"], "Unnamed Goal")
        self.assertEqual(corrupted["target_amount"], 0.0)
        
        # Test that SavingsAgent analyze doesn't crash on this goal
        from agents.savings_agent import SavingsAgent
        report = SavingsAgent.analyze("test-user-123")
        self.assertEqual(report["status"], "Success")
        corrupted_summary = next(g for g in report["goals_summary"] if g["goal_name"] == "Unnamed Goal")
        self.assertEqual(corrupted_summary["target_amount"], 0.0)

    @patch('services.ai_service.AIService.generate_content')
    def test_goal_planner_empty_transactions(self, mock_gemini):
        mock_gemini.return_value = "Advice for empty transactions."
        
        res_goal = self.client.post('/api/goals', headers=self.headers, json={
            "goal_name": "Vacation Goal",
            "target_amount": 10000.0,
            "current_amount": 100.0,
            "deadline": "2026-12-01"
        })
        self.assertEqual(res_goal.status_code, 201, f"Failed: {res_goal.data}")
        goal_id = json.loads(res_goal.data)["goal_id"]
        
        # User has no transactions registered in self.firestore_db. Let's delete existing transactions
        self.firestore_db["expenses"] = {}
        
        res_plan = self.client.get(f'/api/goals/{goal_id}/planner', headers=self.headers)
        data_plan = json.loads(res_plan.data)
        self.assertEqual(res_plan.status_code, 200)
        self.assertEqual(data_plan["ai_advice"], "Advice for empty transactions.")
        
        # Check that prompt contains transaction default text
        args, kwargs = mock_gemini.call_args
        self.assertIn("- No recent transactions recorded yet.", args[0])

    def test_savings_agent_no_goals(self):
        from agents.savings_agent import SavingsAgent
        # Query for a user who has no goals
        report = SavingsAgent.analyze("user-with-no-goals")
        self.assertEqual(report["status"], "No goals set")
        self.assertEqual(report["goals_summary"], [])
        self.assertIn("No savings goals", report["findings"])

    @patch('services.notification_service.NotificationService.create_notification')
    def test_savings_agent_goal_completed(self, mock_notify):
        # Create a completed goal
        res_goal = self.client.post('/api/goals', headers=self.headers, json={
            "goal_name": "Completed Goal",
            "target_amount": 500.0,
            "current_amount": 500.0,
            "deadline": "2026-12-01"
        })
        self.assertEqual(res_goal.status_code, 201, f"Failed: {res_goal.data}")
        
        from agents.savings_agent import SavingsAgent
        report = SavingsAgent.analyze("test-user-123")
        self.assertEqual(report["status"], "Success")
        completed_goal = next(g for g in report["goals_summary"] if g["goal_name"] == "Completed Goal")
        self.assertEqual(completed_goal["status"], "Completed")
        self.assertIn("Completed! Goal achieved.", completed_goal["prediction"])

    def test_recurring_payments_flow(self):
        # 1. Create a recurring payment
        payload = {
            "title": "Netflix Subscription",
            "amount": 199.0,
            "category": "Subscription",
            "frequency": "Monthly",
            "start_date": "2026-06-01",
            "next_due_date": "2026-07-01",
            "notes": "Premium plan"
        }
        res_create = self.client.post('/api/recurring', headers=self.headers, json=payload)
        self.assertEqual(res_create.status_code, 201)
        data_create = json.loads(res_create.data)
        self.assertIn("recurring_id", data_create)
        recurring_id = data_create["recurring_id"]
        self.assertEqual(data_create["title"], "Netflix Subscription")
        self.assertEqual(data_create["amount"], 199.0)

        # 2. Get list of recurring payments
        res_list = self.client.get('/api/recurring', headers=self.headers)
        self.assertEqual(res_list.status_code, 200)
        data_list = json.loads(res_list.data)
        self.assertEqual(len(data_list), 1)
        self.assertEqual(data_list[0]["recurring_id"], recurring_id)

        # 3. Update the recurring payment
        update_payload = {
            "amount": 299.0,
            "notes": "Upgraded to 4K plan"
        }
        res_update = self.client.put(f'/api/recurring/{recurring_id}', headers=self.headers, json=update_payload)
        self.assertEqual(res_update.status_code, 200)
        data_update = json.loads(res_update.data)
        self.assertEqual(data_update["amount"], 299.0)
        self.assertEqual(data_update["notes"], "Upgraded to 4K plan")

        # 4. Mark as paid
        # This should log an expense (with category 'Subscriptions') and increment the date to 2026-08-01
        res_pay = self.client.post(f'/api/recurring/{recurring_id}/pay', headers=self.headers)
        self.assertEqual(res_pay.status_code, 200)
        data_pay = json.loads(res_pay.data)
        self.assertTrue(data_pay["success"])
        self.assertEqual(data_pay["next_due_date"], "2026-08-01")
        
        # Verify the expense was created in the firestore_db under "expenses"
        expenses_in_db = self.firestore_db.get("expenses", {})
        self.assertTrue(len(expenses_in_db) > 0)
        # Find the logged expense
        matching_expense = None
        for exp in expenses_in_db.values():
            if "Netflix Subscription" in exp.get("description", ""):
                matching_expense = exp
                break
        self.assertIsNotNone(matching_expense)
        self.assertEqual(matching_expense["amount"], 299.0)
        self.assertEqual(matching_expense["category"], "Subscriptions")
        self.assertEqual(matching_expense["date"], "2026-07-01") # original next_due_date

        # 5. Check InsightsAgent includes recurring payments
        from agents.insights_agent import InsightsAgent
        report = InsightsAgent.analyze("test-user-123")
        self.assertEqual(report["status"], "Success")
        self.assertEqual(report["total_monthly_recurring_commitments"], 299.0)
        self.assertIn("recurring_commitments_by_category", report)
        self.assertEqual(report["recurring_commitments_by_category"].get("Subscription"), 299.0)

        # 6. Delete the recurring payment
        res_delete = self.client.delete(f'/api/recurring/{recurring_id}', headers=self.headers)
        self.assertEqual(res_delete.status_code, 200)
        data_delete = json.loads(res_delete.data)
        self.assertTrue(data_delete["success"])

        # Check list is empty now
        res_list_after = self.client.get('/api/recurring', headers=self.headers)
        self.assertEqual(res_list_after.status_code, 200)
        data_list_after = json.loads(res_list_after.data)
        self.assertEqual(len(data_list_after), 0)
    @patch('services.ai_service.AIService.generate_content')
    def test_voice_parse_service_single_and_multi(self, mock_gemini):
        """Test voice transcript parsing for single and multi transactions"""
        from services.voice_service import VoiceService
        
        # Test Case 1: Multi-transaction response from AI
        mock_gemini.return_value = json.dumps({
            "transactions": [
                {
                    "amount": 100.0,
                    "type": "expense",
                    "category": "Food",
                    "date": "2026-06-20",
                    "note": "breakfast",
                    "merchant": None,
                    "friend_name": None,
                    "friend_owe_amount": None
                },
                {
                    "amount": 2000.0,
                    "type": "income",
                    "category": "Salary",
                    "date": "2026-06-21",
                    "note": "salary received",
                    "merchant": "Company",
                    "friend_name": None,
                    "friend_owe_amount": None
                }
            ],
            "clarification_needed": False,
            "clarification_message": None
        })

        result = VoiceService.parse_transcript("spent 100 on breakfast and got 2000 salary")
        self.assertFalse(result["clarification_needed"])
        self.assertEqual(len(result["transactions"]), 2)
        self.assertEqual(result["transactions"][0]["amount"], 100.0)
        self.assertEqual(result["transactions"][0]["category"], "Food")
        self.assertEqual(result["transactions"][1]["amount"], 2000.0)
        self.assertEqual(result["transactions"][1]["type"], "income")

        # Test Case 2: Clarification / failure handling
        mock_gemini.return_value = json.dumps({
            "transactions": [],
            "clarification_needed": True,
            "clarification_message": "Could not identify amount"
        })

        result_clarify = VoiceService.parse_transcript("lunch time")
        self.assertTrue(result_clarify["clarification_needed"])
        self.assertEqual(result_clarify["clarification_message"], "Could not identify amount")

    def test_income_calculation_multiple_categories(self):
        """Test is_income helper classifies multiple income categories correctly and is integrated with AnalyticsService"""
        from utils.constants import is_income
        from services.analytics_service import AnalyticsService

        # 1. Test helper directly
        self.assertTrue(is_income("Income"))
        self.assertTrue(is_income("Salary"))
        self.assertTrue(is_income("Freelancing"))
        self.assertTrue(is_income("Refund"))
        self.assertTrue(is_income("Interest"))
        self.assertTrue(is_income("Bonus"))
        self.assertTrue(is_income("Other Income"))
        self.assertTrue(is_income("salary"))
        self.assertTrue(is_income("  bonus  "))
        self.assertFalse(is_income("Food"))
        self.assertFalse(is_income("Entertainment"))
        self.assertFalse(is_income(None))

        # 2. Test integration with AnalyticsService calculations
        # Clear database and prepare test expenses/accounts
        self.firestore_db["accounts"] = {
            "acc-1": {
                "account_id": "acc-1",
                "uid": "test-user-123",
                "name": "Main Account",
                "type": "Bank",
                "initial_balance": 0.0,
                "last_details": ""
            }
        }

        self.firestore_db["expenses"] = {
            "tx-1": {
                "expense_id": "tx-1",
                "uid": "test-user-123",
                "amount": 5000.0,
                "category": "Salary", # income category
                "date": "2026-06-21",
                "description": "Stipend",
                "account_id": "acc-1"
            },
            "tx-2": {
                "expense_id": "tx-2",
                "uid": "test-user-123",
                "amount": 10000.0,
                "category": "Income", # income category
                "date": "2026-06-21",
                "description": "Papa sent",
                "account_id": "acc-1"
            },
            "tx-3": {
                "expense_id": "tx-3",
                "uid": "test-user-123",
                "amount": 2000.0,
                "category": "Food", # expense category
                "date": "2026-06-21",
                "description": "Dinner",
                "account_id": "acc-1"
            },
            "tx-4": {
                "expense_id": "tx-4",
                "uid": "test-user-123",
                "amount": 300.0,
                "category": "Other", # expense category
                "date": "2026-06-21",
                "description": "Stationery",
                "account_id": "acc-1"
            }
        }

        # Calculate dashboard summary
        res = AnalyticsService.get_dashboard_summary("test-user-123")
        summary = res["summary"]

        # Net balance = Income (Salary 5000 + Income 10000) - Expense (Food 2000 + Other 300)
        # = 15000 - 2300 = 12700
        self.assertEqual(summary["total_income"], 15000.0)
        self.assertEqual(summary["total_expenses"], 2300.0)
        self.assertEqual(summary["total_balance"], 12700.0)

if __name__ == '__main__':
    unittest.main()


