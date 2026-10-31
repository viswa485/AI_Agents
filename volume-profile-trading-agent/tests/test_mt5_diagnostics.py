import pandas as pd
from volume_profile_agent.mt5_diagnostics import build_diagnostic_report


def test_diagnostic_report_is_sanitized_and_checks_server_and_history():
    m1 = pd.DataFrame({"time": pd.to_datetime(["2026-10-30T10:00:00Z"]),
                       "tick_volume": [10], "real_volume": [0]})
    m5 = pd.DataFrame({"time": pd.to_datetime(["2026-10-30T10:00:00Z"]),
                       "tick_volume": [40], "real_volume": [0]})
    report = build_diagnostic_report(
        symbol="XAUUSD", expected_server="OANDATMS-MT5",
        terminal_name="MetaTrader 5", terminal_company="MetaQuotes",
        terminal_connected=True, account_server="OANDATMS-MT5-Demo",
        account_company="OANDA TMS Brokers S.A.",
        symbol_info={"name":"XAUUSD","digits":2,"point":0.01},
        m1=m1,m5=m5,checked_at=pd.Timestamp("2026-10-30T10:05:00Z").to_pydatetime())
    assert report["checks"]["terminal_connected"]
    assert report["checks"]["expected_server_detected"]
    assert report["checks"]["symbol_found"]
    assert report["all_checks_passed"]
    assert "account_login" not in str(report).lower()
    assert "password" not in str(report).lower()


def test_diagnostic_report_warns_when_server_or_history_missing():
    empty = pd.DataFrame(columns=["time","tick_volume","real_volume"])
    report = build_diagnostic_report(
        symbol="XAUUSD", expected_server="OANDATMS-MT5",
        terminal_name="MT5", terminal_company="Other",
        terminal_connected=True, account_server="OTHER-SERVER", account_company="Other",
        symbol_info={"name":"XAUUSD"}, m1=empty, m5=empty,
        checked_at=pd.Timestamp("2026-10-30T10:05:00Z").to_pydatetime())
    assert not report["all_checks_passed"]
    assert len(report["warnings"]) >= 3
