import sqlite3
import pytest
import models
from app import create_app


@pytest.fixture
def conn(tmp_path):
    """Fixture providing an initialized SQLite database connection for unit tests."""
    db_file = str(tmp_path / "test_model.db")
    connection = sqlite3.connect(db_file)
    connection.row_factory = sqlite3.Row
    models.init_db(connection)
    yield connection
    connection.close()


@pytest.fixture
def client(tmp_path):
    """Fixture providing a Flask test client with an initialized temporary database file."""
    db_file = str(tmp_path / "test_api.db")
    models.init_db(db_file)
    app = create_app(db_file)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_tx(amount=100.0, category="Food", description="", date="2026-09-10", tx_type="expense", **kwargs):
    """Helper function to construct valid test transaction payloads."""
    tx = {
        "amount": amount,
        "category": category,
        "description": description,
        "note": description,
        "date": date,
        "type": tx_type,
    }
    tx.update(kwargs)
    if "note" in kwargs and not tx.get("description"):
        tx["description"] = kwargs["note"]
    if "description" in kwargs and not tx.get("note"):
        tx["note"] = kwargs["description"]
    return tx