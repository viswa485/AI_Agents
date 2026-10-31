"""Read-only OANDA MT5 market-data polling that feeds the local paper broker."""
from __future__ import annotations
import argparse,json,logging,os,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pandas as pd
from .mt5_feed import MT5HistoricalFeed
from .backtest import scan_sessions_multiframe
from .profile import ProfileConfig
from .risk_paper import PaperBroker,RiskConfig

TIMEFRAMES={"M1":60,"M5":300,"M15":900,"M30":1800,"H1":3600,"H4":14400}


def _closed_bars(frame,seconds,now):
    if frame.empty: return frame
    out=frame.copy(); out["time"]=pd.to_datetime(out.time,utc=True)
    return out.loc[out.time+pd.Timedelta(seconds=seconds)<=pd.Timestamp(now)].sort_values("time").reset_index(drop=True)


def run(symbol,execution_timeframe,profile_timeframe,session_timezone,session_start,
        volume_field="tick_volume",lookback_days=10,poll_seconds=5,
        db_path="data/paper.sqlite",state_path="data/mt5-paper-state.json",
        initial_balance=10000,once=False):
    if execution_timeframe not in TIMEFRAMES or profile_timeframe not in TIMEFRAMES:
        raise ValueError("Unsupported timeframe")
    if lookback_days<2 or poll_seconds<1: raise ValueError("lookback_days >= 2 and poll_seconds >= 1 required")
    import MetaTrader5 as mt5
    state_file=Path(state_path); state_file.parent.mkdir(parents=True,exist_ok=True)
    try: state=json.loads(state_file.read_text()) if state_file.exists() else {}
    except (OSError,json.JSONDecodeError): state={}
    cursor=state.get("last_processed_bar")
    broker=PaperBroker(db_path,initial_balance,RiskConfig())
    logging.warning("PAPER MODE ONLY. MT5 access is historical/read-only; local paper simulator only.")
    terminal_path=os.getenv("MT5_TERMINAL_PATH") or None
    with MT5HistoricalFeed(terminal_path) as feed:
        metadata=feed.ensure_symbol(symbol)
        logging.info("Connected read-only symbol: %s | digits=%s | tick_size=%s",metadata["name"],metadata["digits"],metadata["trade_tick_size"])
        while True:
            now=datetime.now(timezone.utc); start=now-timedelta(days=lookback_days)
            profile_raw=feed.fetch_rates(symbol,getattr(mt5,"TIMEFRAME_"+profile_timeframe),start,now)
            exec_raw=feed.fetch_rates(symbol,getattr(mt5,"TIMEFRAME_"+execution_timeframe),start,now)
            profile_bars=_closed_bars(profile_raw,TIMEFRAMES[profile_timeframe],now)
            exec_bars=_closed_bars(exec_raw,TIMEFRAMES[execution_timeframe],now)
            if len(profile_bars)>=3 and len(exec_bars)>=3:
                latest=exec_bars.iloc[-1]; latest_time=pd.Timestamp(latest.time).isoformat()
                if latest_time!=cursor:
                    cfg=ProfileConfig(row_count=60,value_area_pct=.70,volume_field=volume_field)
                    signals,_=scan_sessions_multiframe(profile_bars,exec_bars,symbol=symbol,
                        timezone=session_timezone,session_start=session_start,profile_config=cfg)
                    for item in broker.on_bar(symbol,{"time":latest_time,"high":float(latest.high),
                                                       "low":float(latest.low),"close":float(latest.close)}):
                        logging.info("Paper exit: %s",item)
                    for signal in signals:
                        if pd.Timestamp(signal.timestamp)==pd.Timestamp(latest_time):
                            logging.info("Paper entry candidate: %s",broker.submit(signal))
                    cursor=latest_time
                    tmp=state_file.with_suffix(state_file.suffix+".tmp")
                    tmp.write_text(json.dumps({"last_processed_bar":cursor},indent=2)+"\n")
                    tmp.replace(state_file)
            acct=broker.account()
            logging.info("Paper account balance=%s open=%s realized_pnl=%s",acct["balance"],acct["open_positions"],acct["realized_pnl"])
            if once: return {"symbol":symbol,"metadata":metadata,"profile_bars":len(profile_bars),
                             "execution_bars":len(exec_bars),"last_processed_bar":cursor,"paper_account":acct}
            time.sleep(poll_seconds)


def main():
    p=argparse.ArgumentParser(description="OANDA MT5 read-only bars -> paper broker; no real orders.")
    p.add_argument("--symbol",required=True,help="Exact Market Watch symbol, likely GOLD.pro for OANDA TMS; verify first")
    p.add_argument("--timeframe",dest="execution_timeframe",default="M5",choices=tuple(TIMEFRAMES))
    p.add_argument("--profile-timeframe",default="M1",choices=tuple(TIMEFRAMES))
    p.add_argument("--timezone",required=True,help="IANA timezone, e.g. Europe/London")
    p.add_argument("--session-start",required=True,help="Confirmed broker session start HH:MM local time")
    p.add_argument("--volume-field",default="tick_volume",choices=["tick_volume","real_volume"])
    p.add_argument("--lookback-days",type=int,default=10); p.add_argument("--poll-seconds",type=int,default=5)
    p.add_argument("--db-path",default="data/paper.sqlite"); p.add_argument("--state-path",default="data/mt5-paper-state.json")
    p.add_argument("--initial-balance",type=float,default=10000); p.add_argument("--once",action="store_true")
    a=p.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    result=run(a.symbol,a.execution_timeframe,a.profile_timeframe,a.timezone,a.session_start,
        a.volume_field,a.lookback_days,a.poll_seconds,a.db_path,a.state_path,a.initial_balance,a.once)
    if a.once: print(json.dumps(result,indent=2,default=str))


if __name__=="__main__": main()
