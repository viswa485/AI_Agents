import pandas as pd
import pytest
from types import SimpleNamespace
from volume_profile_agent.profile import ProfileConfig,calculate_profile
from volume_profile_agent.strategies import poc_bounce,value_area_reversal,breakout,Signal
from volume_profile_agent.risk_paper import PaperBroker,RiskConfig
from volume_profile_agent.backtest import scan_sessions_multiframe


def test_profile_60_rows_and_volume_conservation():
    bars=pd.DataFrame({"high":[100,101,102],"low":[99,100,101],"tick_volume":[10,20,30]})
    result=calculate_profile(bars,ProfileConfig())
    assert len(result.rows)==60
    assert result.total_volume==pytest.approx(60)
    assert result.val<=result.poc<=result.vah


def test_invalid_profile_data_rejected():
    with pytest.raises(ValueError):
        calculate_profile(pd.DataFrame({"high":[1],"low":[2],"tick_volume":[0]}))


def test_poc_bounce_requires_prior_close_outside_and_engulfing():
    p=SimpleNamespace(symbol="XAUUSD",poc=100.,vah=105.,val=95.)
    bars=pd.DataFrame([["2026-01-01T00:00:00Z",101,102,98,99],
      ["2026-01-01T00:05:00Z",98,103,97,102]],columns=["time","open","high","low","close"])
    assert len(poc_bounce(bars,p,106))==1
    assert poc_bounce(bars,p,100)==[]


def test_value_area_reversal_requires_close_back_inside():
    p=SimpleNamespace(symbol="XAUUSD",poc=100.,vah=105.,val=95.)
    bars=pd.DataFrame([["2026-01-01T00:00:00Z",96,97,92,94],
      ["2026-01-01T00:05:00Z",94,98,93,96]],columns=["time","open","high","low","close"])
    assert len(value_area_reversal(bars,p,101))==1
    assert value_area_reversal(bars,p,108)==[]


def test_breakout_requires_retest_and_bos():
    p=SimpleNamespace(symbol="XAUUSD",poc=95.,vah=100.,val=90.)
    bars=pd.DataFrame([["2026-01-01T00:00:00Z",98,99,97,98],
      ["2026-01-01T00:05:00Z",99,103,98,102],
      ["2026-01-01T00:10:00Z",102,102,100.1,101],
      ["2026-01-01T00:15:00Z",101,105,100.8,104]],
      columns=["time","open","high","low","close"])
    assert len(breakout(bars,p))==1


def test_paper_broker_risk_and_stop_first_rule(tmp_path):
    signal=Signal("abc","XAUUSD","POC_BOUNCE","LONG","2026-01-01T10:00:00+00:00",
                  100,98,104,2,2,"unit test",{})
    broker=PaperBroker(tmp_path/"paper.sqlite",10000,RiskConfig())
    opened=broker.submit(signal)
    assert opened["approved"] is True
    assert opened["quantity"]==pytest.approx(12.5)
    closed=broker.on_bar("XAUUSD",{"time":"2026-01-01T10:05:00Z","high":105,"low":97})
    assert closed[0]["reason"]=="STOP_LOSS"
    assert closed[0]["pnl"]==pytest.approx(-25)


def test_multiframe_scanner_uses_prior_m1_profile_and_current_m5_signals():
    profile_bars=pd.DataFrame([
      ["2026-01-01T00:00:00Z",100,101,99,100,10],
      ["2026-01-01T00:01:00Z",100,102,99,101,20],
      ["2026-01-01T00:02:00Z",101,103,100,102,30],
      ["2026-01-02T00:00:00Z",102,103,101,102,10],
      ["2026-01-02T00:01:00Z",102,104,101,103,20]],
      columns=["time","open","high","low","close","tick_volume"])
    execution_bars=pd.DataFrame([
      ["2026-01-01T00:00:00Z",100,101,99,100],
      ["2026-01-01T00:05:00Z",100,102,99,101],
      ["2026-01-02T00:00:00Z",102,103,101,102],
      ["2026-01-02T00:05:00Z",102,104,101,103]],
      columns=["time","open","high","low","close"])
    _,reports=scan_sessions_multiframe(profile_bars,execution_bars,symbol="GOLD.pro",
      timezone="UTC",session_start="00:00",profile_config=ProfileConfig(row_count=10))
    assert len(reports)==1
    assert reports[0]["profile_bar_count"]==3
    assert reports[0]["execution_bar_count"]==2
    assert reports[0]["profile_session"]=="2026-01-01"
    assert reports[0]["trading_session"]=="2026-01-02"
