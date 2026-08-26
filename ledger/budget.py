"""Per-month token accounting and budget gate."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ledger.config import DEFAULT_MONTHLY_TOKEN_BUDGET
from ledger.db import connect


def _now() -> float:
    return datetime.now(timezone.utc).timestamp()


def record_usage(model: str, prompt_tokens: int, eval_tokens: int, month: str | None = None) -> None:
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    with connect() as conn:
        conn.execute(
            "INSERT INTO token_usage (ts, month, model, prompt_tokens, eval_tokens) VALUES (?, ?, ?, ?, ?)",
            (_now(), month, model, int(prompt_tokens), int(eval_tokens)),
        )


def month_usage(month: str) -> tuple[int, int]:
    with connect() as conn:
        cur = conn.execute(
            "SELECT COALESCE(SUM(prompt_tokens),0) AS p, COALESCE(SUM(eval_tokens),0) AS e "
            "FROM token_usage WHERE month = ?",
            (month,),
        )
        row = cur.fetchone()
        return int(row["p"]), int(row["e"])


def set_budget(month: str, tokens: int) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO budgets (month, token_budget) VALUES (?, ?) "
            "ON CONFLICT(month) DO UPDATE SET token_budget = excluded.token_budget",
            (month, int(tokens)),
        )


def _budget_for(month: str) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT token_budget FROM budgets WHERE month = ?", (month,)
        ).fetchone()
        if row:
            return int(row["token_budget"])
    return DEFAULT_MONTHLY_TOKEN_BUDGET


def budget_status(month: str | None = None) -> dict:
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    budget = _budget_for(month)
    prompt, eval_ = month_usage(month)
    used = prompt + eval_
    remaining = max(0, budget - used)
    return {
        "month": month,
        "budget": budget,
        "used": used,
        "remaining": remaining,
        "over_budget": used > budget,
    }


def is_over_budget(month: str | None = None) -> bool:
    return budget_status(month)["over_budget"]


__all__ = [
    "record_usage",
    "month_usage",
    "set_budget",
    "budget_status",
    "is_over_budget",
]