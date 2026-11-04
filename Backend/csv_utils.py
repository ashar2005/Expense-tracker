"""CSV export and import (FR-08, FR-09)."""
import pandas as pd
from Backend import models
from Backend.validators import validate_transaction

COLUMNS = ["date", "type", "category", "amount", "note"]


def export_csv_text(conn, start=None, end=None):
    """Return the transactions as CSV text."""
    rows = models.list_transactions(conn, start=start, end=end, sort="date", order="asc")
    frame = pd.DataFrame(rows, columns=["id"] + COLUMNS)[COLUMNS]
    return frame.to_csv(index=False)


def import_csv(conn, source):
    """Import rows from a CSV path or file object.

    Valid rows are saved; invalid rows are reported, never crash the import.
    Returns {"imported": int, "errors": [{"row": int, "problems": str}]}.
    """
    try:
        frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
        raise ValueError("file is not a valid CSV")
    missing = [c for c in COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError("missing columns: " + ", ".join(missing))

    imported, errors = 0, []
    for index, row in frame.iterrows():
        data = {c: row[c].strip() for c in COLUMNS}
        problems = validate_transaction(data)
        if not problems:
            try:
                models.add_transaction(conn, data)
                imported += 1
                continue
            except ValueError as exc:
                problems = [str(exc)]
        errors.append({"row": index + 2, "problems": "; ".join(problems)})
    return {"imported": imported, "errors": errors}
