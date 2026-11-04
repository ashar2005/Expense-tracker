import pytest
from Backend.app import create_app
from Backend.database import get_connection, init_db


@pytest.fixture
def conn(tmp_path):
    """Fresh database with default categories for each test."""
    db = str(tmp_path / "test.db")
    init_db(db)
    connection = get_connection(db)
    yield connection
    connection.close()


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "api.db"))
    app.config["TESTING"] = True
    return app.test_client()


def make_tx(**overrides):
    data = {"type": "expense", "amount": 100, "category": "Food",
            "date": "2026-09-10", "note": "test"}
    data.update(overrides)
    return data
