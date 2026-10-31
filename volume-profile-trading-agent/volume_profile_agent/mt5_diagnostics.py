"""Read-only MT5 connection diagnostic. Never prints account login or credentials."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Any

import pandas as pd

from .mt5_feed import MT5HistoricalFeed


TIMEFRAMES = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400}


def _get(obj: Any, name: str, default=None):
    return getattr(obj, name, default) if obj is not None else default


def _bar_summary(frame: pd.DataFrame, timeframe: str) -> dict[str, Any]:
    if frame.empty:
        return {"timeframe": timeframe, "bar_count": 0, "first_bar_utc": None,
                "last_bar_utc": None, "tick_volume_sum": 0, "real_volume_sum": 0,
                "real_volume_nonzero_bars": 0}
    data = frame.copy()
    data["time"] = pd.to_datetime(data["time"], utc=True)
    tick = pd.to_numeric(data.get("tick_volume", pd.Series(0, index=data.index)), errors="coerce").fillna(0)
    real = pd.to_numeric(data.get("real_volume", pd.Series(0, index=data.index)), errors="coerce").fillna(0)
    return {
        "timeframe": timeframe,
        "bar_count": int(len(data)),
        "first_bar_utc": data.time.min().isoformat(),
        "last_bar_utc": data.time.max().isoformat(),
        "tick_volume_sum": int(tick.sum()),
        "real_volume_sum": float(real.sum()),
        "real_volume_nonzero_bars": int((real > 0).sum()),
    }


def build_diagnostic_report(*, symbol: str, expected_server: str,
                            terminal_name: str | None, terminal_company: str | None,
                            terminal_connected: bool | None, account_server: str | None,
                            account_company: str | None, symbol_info: dict[str, Any],
                            m1: pd.DataFrame, m5: pd.DataFrame,
                            checked_at: datetime) -> dict[str, Any]:
    server_text = account_server or ""
    company_text = " ".join(x or "" for x in (terminal_company, account_company))
    server_ok = bool(expected_server and expected_server.casefold() in server_text.casefold())
    broker_ok = "oanda" in (server_text + " " + company_text).casefold()
    checks = {
        "terminal_connected": terminal_connected is True,
        "account_session_available": bool(account_server),
        "oanda_server_or_company_detected": broker_ok,
        "expected_server_detected": server_ok,
        "symbol_found": bool(symbol_info.get("name")),
        "m1_history_available": not m1.empty,
        "m5_history_available": not m5.empty,
    }
    warnings = []
    if not server_ok:
        warnings.append(f"Connected server does not contain expected server name '{expected_server}'. Verify the OANDA account division/server.")
    if not broker_ok:
        warnings.append("Terminal/company metadata did not identify OANDA; verify this is the intended broker terminal.")
    if m1.empty:
        warnings.append("No M1 history returned for the requested lookback window.")
    if m5.empty:
        warnings.append("No M5 history returned for the requested lookback window.")
    return {
        "mode": "read_only_diagnostic",
        "live_order_submission": False,
        "checked_at_utc": checked_at.astimezone(timezone.utc).isoformat(),
        "symbol_requested": symbol,
        "terminal": {"name": terminal_name, "company": terminal_company,
                     "connected": terminal_connected},
        "account": {"server": account_server, "company": account_company},
        "symbol": symbol_info,
        "history": {
            "profile": _bar_summary(m1, "M1"),
            "execution": _bar_summary(m5, "M5"),
        },
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "warnings": warnings,
        "privacy": "Account login, account number, balance, equity and credentials are intentionally omitted.",
    }


def run_diagnostic(*, symbol: str = "XAUUSD", expected_server: str = "OANDATMS-MT5",
                   lookback_hours: int = 168, terminal_path: str | None = None) -> dict[str, Any]:
    if lookback_hours < 1:
        raise ValueError("lookback_hours must be >= 1")
    import MetaTrader5 as mt5
    start = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    end = datetime.now(timezone.utc)
    with MT5HistoricalFeed(terminal_path) as feed:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None:
            raise RuntimeError(f"MT5 terminal_info unavailable: {mt5.last_error()}")
        if account is None:
            raise RuntimeError(f"No logged-in MT5 account session: {mt5.last_error()}")
        info = feed.ensure_symbol(symbol)
        m1 = feed.fetch_rates(symbol, mt5.TIMEFRAME_M1, start, end)
        m5 = feed.fetch_rates(symbol, mt5.TIMEFRAME_M5, start, end)
        return build_diagnostic_report(
            symbol=symbol, expected_server=expected_server,
            terminal_name=_get(terminal, "name"), terminal_company=_get(terminal, "company"),
            terminal_connected=_get(terminal, "connected"),
            account_server=_get(account, "server"), account_company=_get(account, "company"),
            symbol_info=info, m1=m1, m5=m5, checked_at=end,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Check read-only OANDA MT5 connection and XAUUSD history.")
    parser.add_argument("--symbol", default="XAUUSD", help="Exact symbol from MT5 Market Watch.")
    parser.add_argument("--expected-server", default="OANDATMS-MT5",
                        help="Expected OANDA TMS server substring; change only if your account uses another OANDA division.")
    parser.add_argument("--lookback-hours", type=int, default=168)
    parser.add_argument("--terminal-path", default=os.getenv("MT5_TERMINAL_PATH"))
    parser.add_argument("--output", help="Optional JSON output file.")
    args = parser.parse_args()
    report = run_diagnostic(symbol=args.symbol, expected_server=args.expected_server,
                            lookback_hours=args.lookback_hours, terminal_path=args.terminal_path)
    rendered = json.dumps(report, indent=2, default=str)
    if args.output:
        from pathlib import Path
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if not report["all_checks_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
