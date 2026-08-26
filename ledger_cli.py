"""`ledger` CLI — every subcommand goes through the MCP server.

Hard rule (per PLAN.md §5.9 and starter-agents.md): the CLI must NOT
import `ledger.db`, `ledger.importer`, etc. directly. It spawns the
FastMCP server as a stdio child process and uses the MCP client. This
proves the CLI is "powered through the MCP, not bypassing it".
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


PROJECT_ROOT = Path(__file__).resolve().parent


def _server_command() -> tuple[str, list[str]]:
    """Resolve the command that runs the MCP server.

    Prefers .venv/bin/python (clean stdlib) so the subprocess inherits the
    same installed packages; falls back to `python3` on PATH.
    """
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python), ["-m", "ledger.mcp_server"]
    return sys.executable, ["-m", "ledger.mcp_server"]


def _client() -> Client:
    cmd, args = _server_command()
    transport = StdioTransport(command=cmd, args=args, cwd=str(PROJECT_ROOT), keep_alive=False)
    return Client(transport)


async def _call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    async with _client() as client:
        result = await client.call_tool(name, arguments or {})
        # FastMCP wraps the payload in CallToolResult. data is the structured payload.
        payload = getattr(result, "data", None)
        if payload is None:
            payload = result
        return payload


async def _read_resource(uri: str) -> str:
    async with _client() as client:
        contents = await client.read_resource(uri)
        if not contents:
            return ""
        first = contents[0]
        return getattr(first, "text", str(first))


def _print(obj: Any) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    else:
        print(obj)


async def cmd_import(args: argparse.Namespace) -> int:
    payload = await _call_tool("import_csv_tool", {"path": args.path})
    if isinstance(payload, dict) and payload.get("error"):
        print(f"error={payload['error']} message={payload.get('message')}", file=sys.stderr)
        return 2
    summary = (
        f"imported={payload.get('imported')} "
        f"skipped_duplicates={payload.get('skipped_duplicates')} "
        f"range={payload.get('date_min')}..{payload.get('date_max')} "
        f"path={payload.get('path')}"
    )
    print(summary)
    return 0


async def cmd_categorise(args: argparse.Namespace) -> int:
    payload = await _call_tool("categorize_pending_tool", {"limit": args.limit})
    if isinstance(payload, dict) and payload.get("error") == "over_budget":
        print("error=over_budget", file=sys.stderr)
        return 2
    _print(payload)
    return 0


async def cmd_query(args: argparse.Namespace) -> int:
    payload = await _call_tool(
        "query_transactions_tool",
        {"month": args.month, "category": args.category, "limit": args.limit},
    )
    _print(payload)
    return 0


async def cmd_report(args: argparse.Namespace) -> int:
    payload = await _call_tool("monthly_report_tool", {"month": args.month})
    if isinstance(payload, dict) and payload.get("error") == "over_budget":
        print("error=over_budget", file=sys.stderr)
        return 2
    _print(payload)
    return 0


async def cmd_budget(args: argparse.Namespace) -> int:
    if args.set is not None:
        payload = await _call_tool(
            "set_budget_tool",
            {"month": args.month or "", "tokens": args.set},
        )
        _print(payload)
        return 0
    payload = await _call_tool("get_budget_status_tool", {"month": args.month})
    _print(payload)
    return 0


async def cmd_status(_: argparse.Namespace) -> int:
    text = await _read_resource("budget://status")
    print(text, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ledger", description="Local-only finance sorter (MCP-powered)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_import = sub.add_parser("import", help="Import a bank CSV via the ledger MCP")
    p_import.add_argument("path", help="Path to the CSV file")
    p_import.set_defaults(func=cmd_import)

    p_cat = sub.add_parser("categorise", help="Categorise pending transactions")
    p_cat.add_argument("--limit", type=int, default=100)
    p_cat.set_defaults(func=cmd_categorise)

    p_q = sub.add_parser("query", help="Query transactions")
    p_q.add_argument("--month", default=None)
    p_q.add_argument("--category", default=None)
    p_q.add_argument("--limit", type=int, default=20)
    p_q.set_defaults(func=cmd_query)

    p_rep = sub.add_parser("report", help="Write monthly markdown + PNG chart")
    p_rep.add_argument("month", help="YYYY-MM")
    p_rep.set_defaults(func=cmd_report)

    p_b = sub.add_parser("budget", help="Show or set monthly token budget")
    p_b.add_argument("--set", type=int, default=None, dest="set")
    p_b.add_argument("--month", default=None)
    p_b.set_defaults(func=cmd_budget)

    p_s = sub.add_parser("status", help="Read budget://status resource")
    p_s.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())