import unittest
import io
import os
from Backend.app import create_app
from Backend.database import init_db

TEST_DB = "test_expensemate.db"


class TestIntegrationAndSystem(unittest.TestCase):

    def setUp(self):
        # Remove old test database file if present
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

        # Initialize schema with categories, transactions, and budgets
        init_db(TEST_DB)

        # Create Flask app instance configured with the test database
        self.app = create_app(db_path=TEST_DB)
        self.client = self.app.test_client()

    def tearDown(self):
        # Clean up temporary test DB after each test run
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    # --- INTEGRATION TESTS ---
    def test_integration_add_transaction_updates_budget_status(self):
        """Integration: Adding an expense transaction updates budget spent totals."""
        # 1. Create Category
        self.client.post("/api/categories", json={"name": "Food"})

        # 2. Set Monthly Budget Limit
        self.client.post("/api/budgets", json={"category": "Food", "limit": 2000, "month": "2026-09"})

        # 3. Add Expense Transaction
        self.client.post("/api/transactions", json={
            "amount": 500, "category": "Food", "type": "expense", "date": "2026-09-15"
        })

        # 4. Verify Budget Calculations
        res = self.client.get("/api/budgets?month=2026-09")
        self.assertEqual(res.status_code, 200)
        budgets = res.get_json()
        self.assertTrue(len(budgets) > 0)
        self.assertEqual(budgets[0]["spent"], 500.0)

    def test_integration_csv_export_import_flow(self):
        """Integration: Exporting transactions to CSV and re-importing."""
        # 1. Create Category & Add Transaction
        self.client.post("/api/categories", json={"name": "Utilities"})
        self.client.post("/api/transactions", json={
            "amount": 1200, "category": "Utilities", "type": "expense", "date": "2026-09-10"
        })

        # 2. Export CSV Data Stream
        export_res = self.client.get("/api/export?month=2026-09")
        self.assertEqual(export_res.status_code, 200)
        csv_data = export_res.data

        # 3. Import CSV Stream
        data = {'file': (io.BytesIO(csv_data), 'test.csv')}
        import_res = self.client.post('/api/import', data=data, content_type='multipart/form-data')
        self.assertEqual(import_res.status_code, 200)

    # --- SYSTEM TESTS ---
    def test_system_dashboard_aggregation_flow(self):
        """System: Complete dashboard data flow (Income - Expense = Net Balance)."""
        # Create categories
        self.client.post("/api/categories", json={"name": "Salary"})
        self.client.post("/api/categories", json={"name": "Rent"})

        # Add Income
        self.client.post("/api/transactions", json={
            "amount": 50000, "category": "Salary", "type": "income", "date": "2026-09-01"
        })
        # Add Expense
        self.client.post("/api/transactions", json={
            "amount": 15000, "category": "Rent", "type": "expense", "date": "2026-09-02"
        })

        # Query Aggregated Dashboard Data
        res = self.client.get("/api/dashboard?month=2026-09")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["income"], 50000.0)
        self.assertEqual(data["expense"], 15000.0)
        self.assertEqual(data["balance"], 35000.0)


if __name__ == "__main__":
    unittest.main()