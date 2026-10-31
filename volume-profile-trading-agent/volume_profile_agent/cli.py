"""CLI for explicit profile calculation, session scan and paper backtest."""
import argparse,json
from pathlib import Path
import pandas as pd
from .profile import ProfileConfig,calculate_profile
from .backtest import scan_sessions_multiframe,paper_backtest
from .risk_paper import RiskConfig


def load_csv(path):
    f=pd.read_csv(path)
    need={"time","open","high","low","close"}
    if need-set(f.columns): raise ValueError(f"CSV missing columns {sorted(need-set(f.columns))}")
    f["time"]=pd.to_datetime(f.time,utc=True,errors="coerce")
    if f.time.isna().any(): raise ValueError("Invalid CSV timestamps")
    return f.sort_values("time").reset_index(drop=True)


def emit(obj,path=None):
    text=json.dumps(obj,indent=2,allow_nan=False,default=str)
    if path:
        target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text+"\n")
        print(f"Wrote {target}")
    else: print(text)


def main():
    p=argparse.ArgumentParser(prog="vp-agent",description="Paper-only Volume Profile agent")
    sub=p.add_subparsers(dest="command",required=True)
    prof=sub.add_parser("profile")
    prof.add_argument("--csv",required=True); prof.add_argument("--symbol",default="XAUUSD")
    prof.add_argument("--start",required=True); prof.add_argument("--end",required=True)
    prof.add_argument("--rows",type=int,default=60); prof.add_argument("--value-area",type=float,default=.70)
    prof.add_argument("--volume-field",choices=["tick_volume","real_volume","volume"],default="tick_volume")
    prof.add_argument("--output")
    for name in ("scan","backtest"):
        q=sub.add_parser(name)
        q.add_argument("--csv",required=True,help="Execution timeframe CSV, e.g. M5")
        q.add_argument("--profile-csv",help="Optional finer profile CSV, e.g. M1. Defaults to --csv.")
        q.add_argument("--symbol",default="XAUUSD")
        q.add_argument("--timezone",default="UTC"); q.add_argument("--session-start",default="00:00")
        q.add_argument("--rows",type=int,default=60); q.add_argument("--value-area",type=float,default=.70)
        q.add_argument("--volume-field",choices=["tick_volume","real_volume","volume"],default="tick_volume")
        q.add_argument("--output")
        if name=="backtest":
            q.add_argument("--initial-balance",type=float,default=10000)
            q.add_argument("--risk-fraction",type=float,default=.0025)
            q.add_argument("--max-daily-loss",type=float,default=.01)
    a=p.parse_args(); bars=load_csv(a.csv); cfg=ProfileConfig(a.rows,a.value_area,a.volume_field)
    if a.command=="profile":
        start,end=pd.Timestamp(a.start),pd.Timestamp(a.end)
        if start.tzinfo is None or end.tzinfo is None or end<=start: raise ValueError("start/end must be ordered timezone-aware timestamps")
        selected=bars[(bars.time>=start.tz_convert("UTC"))&(bars.time<end.tz_convert("UTC"))]
        emit(calculate_profile(selected,cfg,symbol=a.symbol).to_dict(),a.output); return
    profile_bars=load_csv(a.profile_csv) if a.profile_csv else bars
    signals,sessions=scan_sessions_multiframe(profile_bars,bars,symbol=a.symbol,timezone=a.timezone,
        session_start=a.session_start,profile_config=cfg)
    if a.command=="scan":
        emit({"sessions":sessions,"signals":[s.to_dict() for s in signals],"live_execution":False},a.output)
    else:
        report=paper_backtest(bars,signals,symbol=a.symbol,initial_balance=a.initial_balance,
                              risk_config=RiskConfig(a.risk_fraction,a.max_daily_loss))
        report["sessions"]=sessions; report["signals_generated"]=len(signals); emit(report,a.output)


if __name__=="__main__": main()
