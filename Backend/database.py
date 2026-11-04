"""Database setup and SQLite initialization for ExpenseMate."""
import sqlite3

DEFAULT_DB = "expensemate.db"


def get_connection(db_path=DEFAULT_DB):
    """Establish and return a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DEFAULT_DB):
    """Initialize database tables if they do not exist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Categories Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    # 2. Transactions Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(LOWER(type) IN ('income', 'expense')),
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        )
        """
    )

    # 3. Budgets Table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            UNIQUE(category_id, month),
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()