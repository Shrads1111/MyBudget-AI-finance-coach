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

            def where_query(field, op, val):
                where_mock = MagicMock()
                
                def stream_docs():
                    docs = []
                    if col_name in self.firestore_db:
                        for d_id, data in self.firestore_db[col_name].items():
                            # Simple query logic mock
                            if field in data and data[field] == val:
                                d_mock = MagicMock()
                                d_mock.to_dict.return_value = data
                                d_mock.id = d_id
                                docs.append(d_mock)
                    return docs

                def sub_where(f, o, v):
                    # Chainable where filters
                    return where_query(f, o, v)

                where_mock.stream = stream_docs
                where_mock.where = sub_where
                return where_mock

            def stream_collection():
                docs = []
                if col_name in self.firestore_db:
                    for d_id, data in self.firestore_db[col_name].items():
                        d_mock = MagicMock()
                        d_mock.to_dict.return_value = data
                        d_mock.id = d_id
                        docs.append(d_mock)
                return docs

            col_mock.document = mock_document
            col_mock.where = where_query
            col_mock.stream = stream_collection
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

        # 2. Invite third member
        res_invite = self.client.post('/api/groups/invite', headers=self.headers, json={
            "group_id": group_id,
            "member": "roommate-riya"
        })
        self.assertEqual(res_invite.status_code, 200)
        self.assertEqual(len(json.loads(res_invite.data)["members"]), 3)

        # 3. Add group expense: Creator pays ₹300 for WiFi split with all 3 members
        exp_payload = {
            "group_id": group_id,
            "expense": {
                "amount": 300.0,
                "description": "WiFi Router Bill",
                "paid_by": "test-user-123",
                "split_with": ["test-user-123", "roommate-aman", "roommate-riya"]
            }
        }
        res_exp = self.client.post('/api/groups/expense', headers=self.headers, json=exp_payload)
        self.assertEqual(res_exp.status_code, 201)

        # 4. Get Summary
        res_sum = self.client.get(f'/api/groups/{group_id}/summary', headers=self.headers)
        data_sum = json.loads(res_sum.data)
        self.assertEqual(res_sum.status_code, 200)
        self.assertEqual(data_sum["total_spending"], 300.0)
        # test-user-123 paid 300, owes 100 -> balance +200
        # roommate-aman paid 0, owes 100 -> balance -100
        # roommate-riya paid 0, owes 100 -> balance -100
        self.assertEqual(data_sum["balances"]["test-user-123"], 200.0)
        self.assertEqual(data_sum["balances"]["roommate-aman"], -100.0)
        self.assertEqual(data_sum["balances"]["roommate-riya"], -100.0)
        
        # VerifySuggested settlements
        settlements = data_sum["suggested_settlements"]
        self.assertEqual(len(settlements), 2)
        self.assertEqual(settlements[0]["to"], "test-user-123")
        self.assertEqual(settlements[0]["amount"], 100.0)

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

if __name__ == '__main__':
    unittest.main()

