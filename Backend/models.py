"""Database queries and business logic models for ExpenseMate."""
import sqlite3


def _category_id(conn, name):
    """Retrieve or automatically create category ID by name."""
    if not name:
        name = "Other"
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    cursor = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    return cursor.lastrowid


def list_categories(conn):
    """List all categories."""
    rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    return [r[0] for r in rows]


def add_category(conn, name):
    """Add a new category."""
    if not name or not name.strip():
        raise ValueError("Category name cannot be empty.")
    conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name.strip(),))
    conn.commit()


def delete_category(conn, name):
    """Delete a category."""
    conn.execute("DELETE FROM categories WHERE name = ?", (name,))
    conn.commit()


def add_transaction(conn, data):
    """Add a transaction with validated input (Fix 2: Corrective Maintenance)."""
    amount = float(data.get("amount") or 0.0)
    if amount <= 0:
        raise ValueError("Transaction amount must be greater than zero.")

    cat_id = _category_id(conn, data.get("category"))
    t_type = str(data.get("type", "expense")).lower()
    t_date = data.get("date") or data.get("transaction_date")
    note = data.get("description") or data.get("note") or ""

    cursor = conn.execute(
        "INSERT INTO transactions (type, amount, category_id, date, note) VALUES (?, ?, ?, ?, ?)",
        (t_type, amount, cat_id, t_date, note)
    )
    conn.commit()
    return cursor.lastrowid


def update_transaction(conn, tx_id, data):
    """Update existing transaction."""
    amount = float(data.get("amount") or 0.0)
    cat_id = _category_id(conn, data.get("category"))
    t_type = str(data.get("type", "expense")).lower()
    t_date = data.get("date") or data.get("transaction_date")
    note = data.get("description") or data.get("note") or ""

    conn.execute(
        "UPDATE transactions SET type = ?, amount = ?, category_id = ?, date = ?, note = ? WHERE id = ?",
        (t_type, amount, cat_id, t_date, note, tx_id)
    )
    conn.commit()


def delete_transaction(conn, tx_id):
    """Delete transaction by ID."""
    conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()


def list_transactions(conn, start=None, end=None, category=None, type_=None, sort="date", order="desc"):
    """List transactions with optional filtering."""
    where_clauses = []
    params = []

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
    direction = "ASC" if order.lower() == "asc" else "DESC"

    query = f"""
        SELECT t.id, t.type, t.amount, c.name AS category, t.date, t.note AS description
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        {where}
        ORDER BY t.date {direction}, t.id {direction}
    """
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def set_budget(conn, data):
    """Set or update category budget limit."""
    cat_id = _category_id(conn, data.get("category"))
    limit_amt = float(data.get("limit") or data.get("amount") or 0.0)
    month = data.get("month")

    conn.execute(
        """
        INSERT INTO budgets (category_id, month, limit_amount)
        VALUES (?, ?, ?)
        ON CONFLICT(category_id, month) DO UPDATE SET limit_amount = excluded.limit_amount
        """,
        (cat_id, month, limit_amt)
    )
    conn.commit()


def delete_budget(conn, budget_id):
    """Delete budget by ID."""
    conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()


def budget_status(conn, month):
    """Retrieve budget limits vs actual spent per category."""
    query = """
        SELECT b.id, c.name AS category, b.limit_amount AS amount,
               COALESCE(SUM(t.amount), 0.0) AS spent
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        LEFT JOIN transactions t ON t.category_id = b.category_id 
             AND LOWER(t.type) = 'expense' 
             AND strftime('%Y-%m', t.date) = b.month
        WHERE b.month = ?
        GROUP BY b.id, c.name, b.limit_amount
    """
    rows = conn.execute(query, (month,)).fetchall()
    res = []
    for r in rows:
        item = dict(r)
        limit = float(item["amount"] or 0.0)
        spent = float(item["spent"] or 0.0)
        item["remaining"] = limit - spent
        item["percent"] = (spent / limit * 100) if limit > 0 else 0.0
        item["alert"] = spent > limit if limit > 0 else False
        res.append(item)
    return res


def summary(conn, start=None, end=None):
    """Calculate aggregate income, expense, and net balance (Fix 1: Corrective Maintenance)."""
    where_clauses = []
    params = []
    if start:
        where_clauses.append("date >= ?")
        params.append(start)
    if end:
        where_clauses.append("date <= ?")
        params.append(end)

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        SELECT 
            COALESCE(SUM(CASE WHEN LOWER(type) = 'income' THEN amount ELSE 0 END), 0.0) AS income,
            COALESCE(SUM(CASE WHEN LOWER(type) = 'expense' THEN amount ELSE 0 END), 0.0) AS expense
        FROM transactions
        {where}
    """
    row = conn.execute(query, params).fetchone()
    inc = float(row[0] or 0.0)
    exp = float(row[1] or 0.0)
    return {"income": inc, "expense": exp, "balance": inc - exp}


def category_totals(conn, month):
    """Get category totals for monthly expenses."""
    query = """
        SELECT c.name AS category, COALESCE(SUM(t.amount), 0.0) AS amount
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE LOWER(t.type) = 'expense' AND strftime('%Y-%m', t.date) = ?
        GROUP BY c.name
        ORDER BY amount DESC
    """
    rows = conn.execute(query, (month,)).fetchall()
    return [dict(r) for r in rows]


def monthly_totals(conn):
    """Get monthly overall totals."""
    query = """
        SELECT strftime('%Y-%m', date) AS month,
               SUM(CASE WHEN LOWER(type) = 'income' THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN LOWER(type) = 'expense' THEN amount ELSE 0 END) AS expense
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
    """
    rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def check_alert(conn, category_name, date_str):
    """Check if adding an expense breached the budget limit."""
    if not category_name or not date_str:
        return None
    month = date_str[:7]
    budgets = budget_status(conn, month)
    for b in budgets:
        if b["category"].lower() == category_name.lower() and b["alert"]:
            return f"{b['category']} is over budget by Rs {abs(b['remaining']):,.2f}."
    return None