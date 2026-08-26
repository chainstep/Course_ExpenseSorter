"""CSV → mapped rows → SQLite. Imports are idempotent via the hash UNIQUE."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Iterable

from ledger.db import connect, init_db
from ledger.embeddings import embed, store_embedding

DEFAULT_MAPPING = {"date": "Date", "merchant": "Merchant", "amount": "Amount"}


def _row_hash(date: str, merchant: str, amount: float) -> str:
    h = hashlib.sha256()
    h.update(f"{date}|{merchant}|{amount:.2f}".encode("utf-8"))
    return h.hexdigest()


def import_csv(path: Path | str, mapping: dict | None = None) -> dict:
    """Parse a CSV and insert rows. Returns a small summary dict only.

    Never returns raw merchant strings (S7/S12). Stores them verbatim
    (provenance) but exposes only counts + date range.
    """
    init_db()
    path = Path(path)
    mapping = mapping or DEFAULT_MAPPING
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    imported = 0
    skipped = 0
    dates: list[str] = []

    with connect() as conn:
        cur = conn.cursor()
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    date = (row[mapping["date"]] or "").strip()
                    merchant = (row[mapping["merchant"]] or "").strip()
                    amount = float(str(row[mapping["amount"]]).replace(",", "").strip())
                except (KeyError, ValueError):
                    skipped += 1
                    continue
                if not date or not merchant:
                    skipped += 1
                    continue
                digest = _row_hash(date, merchant, amount)
                cur.execute(
                    "INSERT OR IGNORE INTO transactions "
                    "(date, merchant, amount, import_file, hash) VALUES (?, ?, ?, ?, ?)",
                    (date, merchant, amount, path.name, digest),
                )
                if cur.lastrowid == 0:
                    skipped += 1
                    continue
                tx_id = cur.lastrowid
                vec = embed(sanitize_for_embed(merchant))
                store_embedding(cur, tx_id, vec)
                imported += 1
                dates.append(date)

    return {
        "imported": imported,
        "skipped_duplicates": skipped,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "path": path.name,
    }


def sanitize_for_embed(merchant: str) -> str:
    """Embedding uses the sanitised merchant so similar strings cluster."""
    from ledger.sanitize import sanitize_merchant
    return sanitize_merchant(merchant)


__all__ = ["import_csv", "DEFAULT_MAPPING"]