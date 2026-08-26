"""Monthly markdown + PNG chart. Returns paths, never bytes (S12)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # noqa: E402  — non-interactive backend; required for headless
import matplotlib.pyplot as plt

from ledger.budget import budget_status, is_over_budget
from ledger.config import REPORTS_DIR
from ledger.db import connect

SPEND_HUE = "#3b82f6"


def _totals_by_category(month: str) -> dict[str, float]:
    with connect() as conn:
        cur = conn.execute(
            "SELECT category, COALESCE(SUM(amount), 0) AS total "
            "FROM transactions WHERE date LIKE ? GROUP BY category",
            (f"{month}%",),
        )
        rows = cur.fetchall()
    totals: dict[str, float] = {}
    for r in rows:
        cat = r["category"] or "other"
        totals[cat] = float(r["total"])
    return totals


def _render_chart(month: str, totals: dict[str, float], png_path: Path) -> None:
    spend = {c: -v for c, v in totals.items() if v < 0}
    income = {c: v for c, v in totals.items() if v > 0}
    items = sorted(spend.items(), key=lambda kv: kv[1], reverse=True)
    labels = [c for c, _ in items] or ["(no spend)"]
    values = [v for _, v in items] or [0.0]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(labels, values, color=SPEND_HUE)
    ax.set_title(f"Spend by category — {month}")
    ax.set_ylabel("Amount (spend, negative sign flipped)")
    ax.set_xlabel("Category")
    ax.tick_params(axis="x", labelrotation=30)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"£{v:,.2f}",
                ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(png_path, dpi=120)
    plt.close(fig)


def _render_markdown(month: str, totals: dict[str, float], md_path: Path) -> None:
    status = budget_status(month)
    spend_items = sorted(
        ((c, -v) for c, v in totals.items() if v < 0), key=lambda kv: kv[1], reverse=True
    )
    income_items = sorted(
        ((c, v) for c, v in totals.items() if v > 0), key=lambda kv: kv[1], reverse=True
    )
    total_spend = sum(v for _, v in spend_items)
    total_income = sum(v for _, v in income_items)

    lines = [
        f"# {month} — finance report",
        "",
        f"![Spend chart](./{md_path.stem}.png)",
        "",
        "## Totals",
        "",
        f"- Total spend: £{total_spend:,.2f}",
        f"- Total income: £{total_income:,.2f}",
        f"- Net: £{total_income - total_spend:,.2f}",
        "",
        "## Spend by category",
        "",
        "| Category | Amount |",
        "|---|---|",
    ]
    for cat, v in spend_items:
        lines.append(f"| {cat} | £{v:,.2f} |")
    if not spend_items:
        lines.append("| _(none)_ | — |")
    lines += [
        "",
        "## Income by category",
        "",
        "| Category | Amount |",
        "|---|---|",
    ]
    for cat, v in income_items:
        lines.append(f"| {cat} | £{v:,.2f} |")
    if not income_items:
        lines.append("| _(none)_ | — |")
    lines += [
        "",
        "## Token budget",
        "",
        f"- Month: {status['month']}",
        f"- Budget: {status['budget']:,} tokens",
        f"- Used: {status['used']:,} tokens",
        f"- Remaining: {status['remaining']:,} tokens",
        f"- Over budget: **{status['over_budget']}**",
        "",
        f"_Chart path: `{md_path.stem}.png` (relative; never inline bytes)._",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")


def monthly_report(month: str) -> dict:
    """Aggregate spend/income, write md + png, return paths only. Budget-gated."""
    if is_over_budget():
        return {"error": "over_budget"}
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    totals = _totals_by_category(month)
    md_path = REPORTS_DIR / f"{month}.md"
    png_path = REPORTS_DIR / f"{month}.png"
    _render_chart(month, totals, png_path)
    _render_markdown(month, totals, md_path)
    return {
        "md_path": str(md_path),
        "png_path": str(png_path),
        "totals_by_category": {k: round(v, 2) for k, v in totals.items()},
    }


__all__ = ["monthly_report"]