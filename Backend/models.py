"""Database queries and business logic models for ExpenseMate."""
import sqlite3

DEFAULT_CATEGORIES = ["Food", "Bills", "Transport", "Entertainment", "Salary", "Other"]


def init_db(db_input):
    """Initialize database tables and seed default categories."""
    if isinstance(db_input, str):
        conn = sqlite3.connect(db_input)
        conn.row_factory = sqlite3.Row
    else:
        conn = db_input

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            UNIQUE(category_id, month),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    """
    )

    for cat in DEFAULT_CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))

    conn.commit()
    if isinstance(db_input, str):
        conn.close()


def _category_id(conn, name):
    """Retrieve category ID by name or raise ValueError if unknown."""
    if not name or not str(name).strip():
        raise ValueError("Category name is required and cannot be empty.")
    clean_name = str(name).strip()
    row = conn.execute("SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (clean_name,)).fetchone()
    if row:
        return row[0]
    raise ValueError(f"Category '{clean_name}' does not exist.")


def list_categories(conn):
    """List all categories ordered by name."""
    rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    return [r[0] for r in rows]


def add_category(conn, name):
    """Add a new category."""
    if not name or not str(name).strip():
        raise ValueError("Category name is required and cannot be empty.")
    clean_name = str(name).strip()
    row = conn.execute("SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (clean_name,)).fetchone()
    if row:
        raise ValueError(f"Category '{clean_name}' already exists.")
    conn.execute("INSERT INTO categories (name) VALUES (?)", (clean_name,))
    conn.commit()


def delete_category(conn, name):
    """Delete a category if not in use by transactions or budgets."""
    if not name or not str(name).strip():
        raise ValueError("Category name is required and cannot be empty.")
    clean_name = str(name).strip()
    cat_row = conn.execute("SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (clean_name,)).fetchone()
    if not cat_row:
        raise ValueError(f"Category '{clean_name}' not found.")
    cat_id = cat_row[0]

    in_tx = conn.execute("SELECT 1 FROM transactions WHERE category_id = ?", (cat_id,)).fetchone()
    in_b = conn.execute("SELECT 1 FROM budgets WHERE category_id = ?", (cat_id,)).fetchone()
    if in_tx or in_b:
        raise ValueError(f"Cannot delete category '{clean_name}' because it is in use.")

    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()


def add_transaction(conn, data):
    """Add a transaction with validated input."""
    if not data:
        raise ValueError("Transaction data cannot be empty.")

    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            raise ValueError("Transaction amount must be greater than zero.")
    except (ValueError, TypeError):
        raise ValueError("Transaction amount must be a positive number.")

    cat_name = data.get("category")
    cat_id = _category_id(conn, cat_name)

    t_type = str(data.get("type", "expense")).lower()
    if t_type not in ("expense", "income"):
        raise ValueError("Transaction type must be 'expense' or 'income'.")

    t_date = data.get("date") or data.get("transaction_date")
    if not t_date:
        raise ValueError("Date is required.")

    note = data.get("note") if data.get("note") is not None else data.get("description", "")

    cursor = conn.execute(
        "INSERT INTO transactions (type, amount, category_id, date, note) VALUES (?, ?, ?, ?, ?)",
        (t_type, amount, cat_id, t_date, note),
    )
    conn.commit()
    return cursor.lastrowid


def update_transaction(conn, tx_id, data):
    """Update existing transaction."""
    tx_row = conn.execute("SELECT id FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not tx_row:
        raise ValueError(f"Transaction {tx_id} not found.")

    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            raise ValueError("Transaction amount must be greater than zero.")
    except (ValueError, TypeError):
        raise ValueError("Transaction amount must be a positive number.")

    cat_name = data.get("category")
    cat_id = _category_id(conn, cat_name)

    t_type = str(data.get("type", "expense")).lower()
    if t_type not in ("expense", "income"):
        raise ValueError("Transaction type must be 'expense' or 'income'.")

    t_date = data.get("date") or data.get("transaction_date")
    if not t_date:
        raise ValueError("Date is required.")

    note = data.get("note") if data.get("note") is not None else data.get("description", "")

    conn.execute(
        "UPDATE transactions SET type = ?, amount = ?, category_id = ?, date = ?, note = ? WHERE id = ?",
        (t_type, amount, cat_id, t_date, note, tx_id),
    )
    conn.commit()


def delete_transaction(conn, tx_id):
    """Delete transaction by ID."""
    cursor = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise ValueError(f"Transaction {tx_id} not found.")


def list_transactions(conn, start=None, end=None, category=None, type_=None, sort="date", order="desc"):
    """List transactions with optional filtering and SQL-injection-safe sorting."""
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

    ALLOWED_SORT = {
        "date": "t.date",
        "amount": "t.amount",
        "category": "c.name",
        "type": "t.type",
        "id": "t.id",
    }
    sort_col = ALLOWED_SORT.get(str(sort).lower(), "t.date")
    direction = "ASC" if str(order).lower() == "asc" else "DESC"

    query = f"""
        SELECT t.id, t.type, t.amount, c.name AS category, t.date, t.note AS description, t.note AS note
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        {where}
        ORDER BY {sort_col} {direction}, t.id {direction}
    """
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def set_budget(conn, data):
    """Set or update category budget limit."""
    if not data:
        raise ValueError("Budget data cannot be empty.")

    cat_name = data.get("category")
    if not cat_name:
        raise ValueError("category is required")
    cat_id = _category_id(conn, cat_name)

    month = data.get("month")
    if not month:
        raise ValueError("month is required")

    limit_val = data.get("limit") if "limit" in data else data.get("amount")
    if limit_val is None:
        raise ValueError("limit is required")
    try:
        limit_amt = float(limit_val)
        if limit_amt <= 0:
            raise ValueError("Budget limit must be positive.")
    except (ValueError, TypeError):
        raise ValueError("Budget limit must be a positive number.")

    conn.execute(
        """
        INSERT INTO budgets (category_id, month, limit_amount)
        VALUES (?, ?, ?)
        ON CONFLICT(category_id, month) DO UPDATE SET limit_amount = excluded.limit_amount
        """,
        (cat_id, month, limit_amt),
    )
    conn.commit()


def delete_budget(conn, budget_id):
    """Delete budget by ID."""
    cursor = conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise ValueError(f"Budget {budget_id} not found.")


def budget_status(conn, month):
    """Retrieve budget limits vs actual spent per category."""
    query = """
        SELECT b.id, c.name AS category, b.month, b.limit_amount AS [limit], b.limit_amount AS amount,
               COALESCE(SUM(t.amount), 0.0) AS spent
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        LEFT JOIN transactions t ON t.category_id = b.category_id 
             AND LOWER(t.type) = 'expense' 
             AND strftime('%Y-%m', t.date) = b.month
        WHERE b.month = ?
        GROUP BY b.id, c.name, b.month, b.limit_amount
    """
    rows = conn.execute(query, (month,)).fetchall()
    res = []
    for r in rows:
        item = dict(r)
        limit_val = float(item["limit"] or 0.0)
        spent_val = float(item["spent"] or 0.0)
        item["limit"] = limit_val
        item["amount"] = limit_val
        item["spent"] = spent_val
        item["remaining"] = limit_val - spent_val
        item["percent"] = (spent_val / limit_val * 100.0) if limit_val > 0 else 0.0

        if limit_val > 0:
            ratio = spent_val / limit_val
            if ratio >= 1.0:
                item["level"] = "exceeded"
                item["alert"] = True
            elif ratio >= 0.8:
                item["level"] = "warning"
                item["alert"] = True
            else:
                item["level"] = "ok"
                item["alert"] = False
        else:
            item["level"] = "ok"
            item["alert"] = False

        res.append(item)
    return res


def summary(conn, start=None, end=None):
    """Calculate aggregate income, expense, and net balance."""
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
        SELECT c.name AS category, COALESCE(SUM(t.amount), 0.0) AS total
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE LOWER(t.type) = 'expense' AND strftime('%Y-%m', t.date) = ?
        GROUP BY c.name
        ORDER BY total DESC
    """
    rows = conn.execute(query, (month,)).fetchall()
    return [{"category": r["category"], "total": float(r["total"])} for r in rows]


def monthly_totals(conn):
    """Get monthly overall totals in chronological order."""
    query = """
        SELECT strftime('%Y-%m', date) AS month,
               COALESCE(SUM(CASE WHEN LOWER(type) = 'income' THEN amount ELSE 0 END), 0.0) AS income,
               COALESCE(SUM(CASE WHEN LOWER(type) = 'expense' THEN amount ELSE 0 END), 0.0) AS expense
        FROM transactions
        GROUP BY month
        ORDER BY month ASC
    """
    rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def check_alert(conn, category_name, date_str):
    """Check if adding an expense breached or approached the budget limit."""
    if not category_name or not date_str:
        return None
    month = str(date_str)[:7]
    budgets = budget_status(conn, month)
    for b in budgets:
        if b["category"].lower() == category_name.lower():
            limit_val = b["limit"]
            spent_val = b["spent"]
            if limit_val <= 0:
                return None
            ratio = spent_val / limit_val
            if ratio >= 1.0:
                return {
                    "level": "exceeded",
                    "alert": True,
                    "category": b["category"],
                    "spent": spent_val,
                    "limit": limit_val,
                    "message": f"{b['category']} budget exceeded!",
                }
            elif ratio >= 0.8:
                return {
                    "level": "warning",
                    "alert": True,
                    "category": b["category"],
                    "spent": spent_val,
                    "limit": limit_val,
                    "message": f"{b['category']} budget warning threshold reached.",
                }
    return None