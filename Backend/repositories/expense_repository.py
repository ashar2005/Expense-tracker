"""Data access repository for ExpenseMate database operations."""
from database import get_db_connection


class ExpenseRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _get_conn(self):
        return get_db_connection(self.db_path)

    def get_category_id(self, category_name):
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM categories WHERE LOWER(name) = LOWER(?)",
                (category_name.strip(),)
            ).fetchone()
            return row["id"] if row else None
        finally:
            conn.close()

    def add_transaction(self, t_type, amount, category_id, t_date, note):
        conn = self._get_conn()
        try:
            with conn:
                cursor = conn.execute(
                    "INSERT INTO transactions (type, amount, category_id, date, note) VALUES (?, ?, ?, ?, ?)",
                    (t_type, amount, category_id, t_date, note)
                )
                return cursor.lastrowid
        finally:
            conn.close()

    def list_transactions(self, start=None, end=None, category=None, type_=None, sort="date", order="desc"):
        where_clauses, params = [], []
        if start:
            where_clauses.append("t.date >= ?")
            params.append(start)
        if end:
            where_clauses.append("t.date <= ?")
            params.append(end)
        if category:
            where_clauses.append("c.name = ?")
            params.append(category)
        if type_:
            where_clauses.append("LOWER(t.type) = ?")
            params.append(type_.lower())

        where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        allowed_sort = {"date": "t.date", "amount": "t.amount", "category": "c.name", "type": "t.type", "id": "t.id"}
        sort_col = allowed_sort.get(str(sort).lower(), "t.date")
        direction = "ASC" if str(order).lower() == "asc" else "DESC"

        query = f"""
            SELECT t.id, t.type, t.amount, c.name AS category, t.date, t.note AS description, t.note AS note
            FROM transactions t
            JOIN categories c ON c.id = t.category_id
            {where}
            ORDER BY {sort_col} {direction}, t.id {direction}
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_budget_spending(self, category_name, month):
        query = """
            SELECT b.limit_amount AS [limit], COALESCE(SUM(t.amount), 0.0) AS spent
            FROM budgets b
            JOIN categories c ON c.id = b.category_id
            LEFT JOIN transactions t ON t.category_id = b.category_id 
                 AND LOWER(t.type) = 'expense' 
                 AND strftime('%Y-%m', t.date) = b.month
            WHERE LOWER(c.name) = LOWER(?) AND b.month = ?
            GROUP BY b.id, c.name, b.limit_amount
        """
        conn = self._get_conn()
        try:
            row = conn.execute(query, (category_name, month)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()