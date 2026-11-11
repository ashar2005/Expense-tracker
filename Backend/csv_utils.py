"""Rewritten CSV export and import utility module."""
import csv
import io
import models
from validators import validate_transaction

COLUMNS = ["date", "type", "category", "amount", "note"]


def export_csv_text(conn, start=None, end=None):
    """Generates clean CSV text formatted string for transaction exports."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\r\n")
    writer.writeheader()

    transactions = models.list_transactions(conn, start=start, end=end, sort="date", order="asc")
    for tx in transactions:
        writer.writerow({
            "date": tx.get("date", ""),
            "type": tx.get("type", ""),
            "category": tx.get("category", ""),
            "amount": float(tx.get("amount") or 0.0),
            "note": tx.get("description") or tx.get("note") or ""
        })
    return output.getvalue()


def import_csv(conn, source):
    """Imports transactions from a CSV file stream or path.
    
    Valid rows are stored in SQLite; invalid rows generate structured error reports.
    Returns dict: {"imported": int, "errors": [{"row": int, "problems": str}]}
    """
    if hasattr(source, "read"):
        content = source.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        stream = io.StringIO(content)
    else:
        stream = open(source, "r", encoding="utf-8")

    try:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("file is not a valid CSV")
    except Exception:
        raise ValueError("file is not a valid CSV")

    missing = [c for c in COLUMNS if c not in reader.fieldnames]
    if missing:
        raise ValueError("missing columns: " + ", ".join(missing))

    imported = 0
    errors = []

    for row_idx, row in enumerate(reader, start=2):
        data = {
            "amount": row.get("amount", "").strip(),
            "category": row.get("category", "").strip(),
            "description": row.get("note", "").strip(),
            "note": row.get("note", "").strip(),
            "date": row.get("date", "").strip(),
            "type": row.get("type", "").strip()
        }

        problems = validate_transaction(data)
        if not problems:
            try:
                models.add_transaction(conn, data)
                imported += 1
            except ValueError as exc:
                errors.append({"row": row_idx, "problems": str(exc)})
        else:
            errors.append({"row": row_idx, "problems": "; ".join(problems)})

    return {"imported": imported, "errors": errors}