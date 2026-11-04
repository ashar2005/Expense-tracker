import io
import pytest
from Backend import csv_utils, models
from tests.conftest import make_tx

HEADER = "date,type,category,amount,note\n"


def test_export_contains_header_and_rows(conn):
    models.add_transaction(conn, make_tx(note="lunch"))
    text = csv_utils.export_csv_text(conn)
    assert text.splitlines()[0] == "date,type,category,amount,note"
    assert "2026-09-10,expense,Food,100.0,lunch" in text


def test_export_empty_database_is_header_only(conn):
    assert csv_utils.export_csv_text(conn).strip() == "date,type,category,amount,note"


def test_export_then_import_round_trip(conn, tmp_path):
    models.add_transaction(conn, make_tx(amount=42))
    text = csv_utils.export_csv_text(conn)
    result = csv_utils.import_csv(conn, io.StringIO(text))
    assert result["imported"] == 1 and result["errors"] == []
    assert len(models.list_transactions(conn)) == 2


def test_import_valid_rows(conn):
    csv_text = HEADER + "2026-09-01,expense,Food,50,a\n2026-09-02,income,Salary,900,b\n"
    result = csv_utils.import_csv(conn, io.StringIO(csv_text))
    assert result == {"imported": 2, "errors": []}


def test_import_reports_bad_rows_but_keeps_good_ones(conn):
    csv_text = (HEADER + "2026-09-01,expense,Food,50,ok\n"
                "not-a-date,expense,Food,50,bad date\n"
                "2026-09-03,expense,Food,abc,bad amount\n"
                "2026-09-04,expense,Ghost,10,bad category\n")
    result = csv_utils.import_csv(conn, io.StringIO(csv_text))
    assert result["imported"] == 1
    assert [e["row"] for e in result["errors"]] == [3, 4, 5]


def test_import_missing_columns_rejected(conn):
    with pytest.raises(ValueError, match="missing columns"):
        csv_utils.import_csv(conn, io.StringIO("date,amount\n2026-09-01,5\n"))


def test_import_garbage_file_rejected(conn):
    with pytest.raises(ValueError):
        csv_utils.import_csv(conn, io.StringIO(""))
