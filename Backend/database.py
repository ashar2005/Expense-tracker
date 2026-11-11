"""Database connection and initialization manager."""
import sqlite3
import os
from config import Config

def get_db_connection(db_path=None):
    """Factory function returning a row-configured SQLite connection."""
    target_path = db_path or Config.DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# Alias for backwards compatibility with app.py
get_connection = get_db_connection


def init_db(db_path=None):
    """Initialize database schema and seed default categories."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    note TEXT,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    month TEXT NOT NULL,
                    limit_amount REAL NOT NULL,
                    UNIQUE(category_id, month),
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )
            """)
            default_categories = ["Food", "Bills", "Transport", "Entertainment", "Salary", "Other"]
            for cat in default_categories:
                conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))
    finally:
        conn.close()