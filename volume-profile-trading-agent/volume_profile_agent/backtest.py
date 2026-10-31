"""Previous observed-session scanner and OHLC-based paper backtest."""
from __future__ import annotations
from datetime import time
from zoneinfo import ZoneInfo
import numpy as np,pandas as pd
from .profile import ProfileConfig,calculate_profile
from .strategies import scan_all
from .risk_paper import PaperBroker,RiskConfig


def _clock(value):
    try: h,m=(int(x) for x in value.split(":")); return time(h,m)
    except Exception as exc: raise ValueError("session_start must be HH:MM") from exc


def add_session_key(bars,timezone,session_start):
    zone=ZoneInfo(timezone); f=bars.copy(); ts=pd.to_datetime(f.time,utc=True,errors="coerce")
    if ts.isna().any(): raise ValueError("Invalid timestamps")
    local=ts.dt.tz_convert(zone); c=_clock(session_start)
    before=(local.dt.hour<c.hour)|((local.dt.hour==c.hour)&(local.dt.minute<c.minute))
    f["time"]=ts
    f["session_key"]=(local.dt.normalize()-pd.to_timedelta(before.astype(int),unit="D")).dt.strftime("%Y-%m-%d")
    return f.sort_values("time").reset_index(drop=True)


def scan_sessions_multiframe(profile_bars,execution_bars,*,symbol,timezone,session_start,
                             profile_config=None,strategy_config=None):
    """Use finer bars for the prior-session profile and execution bars for setups."""
    profile_frame=add_session_key(profile_bars,timezone,session_start)
    execution_frame=add_session_key(execution_bars,timezone,session_start)
    p_groups={k:g.reset_index(drop=True) for k,g in profile_frame.groupby("session_key",sort=True)}
    e_groups={k:g.reset_index(drop=True) for k,g in execution_frame.groupby("session_key",sort=True)}
    keys=sorted(set(p_groups).intersection(e_groups))
    if len(keys)<2:
        raise ValueError("Need at least two sessions present in both profile and execution data")
    signals=[]; reports=[]
    for i in range(1,len(keys)):
        prior_key,current_key=keys[i-1],keys[i]
        prior_profile_bars=p_groups[prior_key]
        prior_execution_bars=e_groups[prior_key]
        current_execution_bars=e_groups[current_key]
        profile=calculate_profile(prior_profile_bars,profile_config,symbol=symbol)
        previous_close=float(prior_execution_bars.iloc[-1].close)
        found=scan_all(current_execution_bars,profile,previous_close,config=strategy_config)
        signals.extend(found)
        reports.append({"profile_session":prior_key,"trading_session":current_key,
                        "profile_bar_count":len(prior_profile_bars),
                        "execution_bar_count":len(current_execution_bars),
                        "poc":profile.poc,"vah":profile.vah,"val":profile.val,
                        "previous_close":previous_close,"signals":len(found)})
    return sorted(signals,key=lambda s:s.timestamp),reports


def scan_sessions(bars,*,symbol,timezone,session_start,profile_config=None,strategy_config=None):
    """Convenience scanner using one timeframe for both profile and signal bars."""
    return scan_sessions_multiframe(bars,bars,symbol=symbol,timezone=timezone,
                                    session_start=session_start,profile_config=profile_config,
                                    strategy_config=strategy_config)


def paper_backtest(bars,signals,*,symbol,initial_balance=10000,risk_config=None):
    """Signal-close fills; stop-first OHLC exits; costs not included."""
    import tempfile,sqlite3
    from pathlib import Path
    f=bars.sort_values("time").copy(); f["time"]=pd.to_datetime(f.time,utc=True)
    by_time={}
    for s in signals: by_time.setdefault(pd.Timestamp(s.timestamp).isoformat(),[]).append(s)
    with tempfile.TemporaryDirectory() as tmp:
        broker=PaperBroker(Path(tmp)/"bt.sqlite",initial_balance,risk_config)
        for _,bar in f.iterrows():
            stamp=pd.Timestamp(bar.time).isoformat()
            broker.on_bar(symbol,{"time":stamp,"high":float(bar.high),"low":float(bar.low)})
            for s in by_time.get(stamp,[]): broker.submit(s)
        opened=broker.trades("OPEN")
        if len(f):
            last=f.iloc[-1]; ts=pd.Timestamp(last.time).isoformat(); price=float(last.close)
            with sqlite3.connect(broker.path) as db:
                for t in opened:
                    d=1 if t["side"]=="LONG" else -1; pnl=(price-t["entry"])*t["quantity"]*d
                    db.execute("UPDATE trades SET status='CLOSED',exit_time=?,exit=?,pnl=?,exit_reason='END_OF_TEST' WHERE id=?",
                               (ts,price,pnl,t["id"]))
        trades=sorted(broker.trades("CLOSED"),key=lambda t:t["exit_time"] or t["entry_time"])
    pnls=np.array([float(t["pnl"] or 0) for t in trades]); wins=pnls[pnls>0]; losses=pnls[pnls<0]
    eq=peak=initial_balance; dd=0
    for value in pnls:
        eq+=value; peak=max(peak,eq); dd=max(dd,(peak-eq)/peak if peak else 0)
    gw=float(wins.sum()) if len(wins) else 0; gl=float(abs(losses.sum())) if len(losses) else 0
    return {"symbol":symbol,"initial_balance":initial_balance,"final_balance":initial_balance+float(pnls.sum()),
      "net_pnl":float(pnls.sum()),"trade_count":len(trades),"wins":len(wins),"losses":len(losses),
      "win_rate":len(wins)/len(trades) if trades else 0,"profit_factor":gw/gl if gl else (None if gw else 0),
      "max_drawdown_fraction":dd,"trades":trades,
      "limitations":["OHLC-range profile estimate","no broker costs/slippage/swaps","abstract quantity, not MT5 lots","stop-first if SL and TP hit in same bar"]}
