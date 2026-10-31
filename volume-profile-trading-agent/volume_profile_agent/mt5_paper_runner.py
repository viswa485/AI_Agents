"""Read-only MT5 candle polling that feeds the local paper broker."""
from __future__ import annotations
import argparse,json,logging,os,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pandas as pd
from .mt5_feed import MT5HistoricalFeed
from .backtest import scan_sessions
from .profile import ProfileConfig
from .risk_paper import PaperBroker,RiskConfig

TIMEFRAMES={"M1":60,"M5":300,"M15":900,"M30":1800,"H1":3600,"H4":14400}


def run(symbol,timeframe,session_timezone,session_start,volume_field="tick_volume",
        lookback_days=10,poll_seconds=5,db_path="data/paper.sqlite",
        state_path="data/mt5-paper-state.json",initial_balance=10000,once=False):
    if timeframe not in TIMEFRAMES: raise ValueError(f"Unsupported timeframe: {timeframe}")
    if lookback_days<2 or poll_seconds<1: raise ValueError("lookback_days >= 2 and poll_seconds >= 1 required")
    import MetaTrader5 as mt5
    state_file=Path(state_path); state_file.parent.mkdir(parents=True,exist_ok=True)
    try: state=json.loads(state_file.read_text()) if state_file.exists() else {}
    except (OSError,json.JSONDecodeError): state={}
    cursor=state.get("last_processed_bar")
    broker=PaperBroker(db_path,initial_balance,RiskConfig())
    logging.warning("PAPER MODE ONLY. Market data read from MT5; no live order methods are used.")
    terminal_path=os.getenv("MT5_TERMINAL_PATH") or None
    with MT5HistoricalFeed(terminal_path) as feed:
        while True:
            now=datetime.now(timezone.utc); start=now-timedelta(days=lookback_days)
            bars=feed.fetch_rates(symbol,getattr(mt5,"TIMEFRAME_"+timeframe),start,now)
            if not bars.empty:
                duration=pd.Timedelta(seconds=TIMEFRAMES[timeframe])
                bars["time"]=pd.to_datetime(bars.time,utc=True)
                # MT5 returns open timestamps. Do not use the currently forming candle.
                bars=bars.loc[bars.time+duration<=pd.Timestamp(now)].sort_values("time").reset_index(drop=True)
            if len(bars)>=3:
                latest=bars.iloc[-1]; latest_time=pd.Timestamp(latest.time).isoformat()
                if latest_time!=cursor:
                    config=ProfileConfig(row_count=60,value_area_pct=.70,volume_field=volume_field)
                    signals,_=scan_sessions(bars,symbol=symbol,timezone=session_timezone,
                                             session_start=session_start,profile_config=config)
                    # Manage already-open paper positions on each newly completed candle.
                    for item in broker.on_bar(symbol,{"time":latest_time,"high":float(latest.high),
                                                       "low":float(latest.low),"close":float(latest.close)}):
                        logging.info("Paper exit: %s",item)
                    # On restart, only the latest completed candle can create a new entry.
                    for signal in signals:
                        if pd.Timestamp(signal.timestamp)==pd.Timestamp(latest_time):
                            logging.info("Paper entry candidate: %s",broker.submit(signal))
                    cursor=latest_time
                    tmp=state_file.with_suffix(state_file.suffix+".tmp")
                    tmp.write_text(json.dumps({"last_processed_bar":cursor},indent=2)+"\n")
                    tmp.replace(state_file)
            acct=broker.account()
            logging.info("Paper account %s | open=%s | realized=%s",acct["balance"],acct["open_positions"],acct["realized_pnl"])
            if once: return
            time.sleep(poll_seconds)


def main():
    p=argparse.ArgumentParser(description="MT5 read-only market data -> paper broker; no real orders.")
    p.add_argument("--symbol",required=True,help="Exact symbol in MT5 Market Watch, including suffix")
    p.add_argument("--timeframe",default="M5",choices=tuple(TIMEFRAMES))
    p.add_argument("--timezone",required=True,help="IANA timezone, e.g. Europe/London")
    p.add_argument("--session-start",required=True,help="Local broker session start HH:MM")
    p.add_argument("--volume-field",default="tick_volume",choices=["tick_volume","real_volume"])
    p.add_argument("--lookback-days",type=int,default=10); p.add_argument("--poll-seconds",type=int,default=5)
    p.add_argument("--db-path",default="data/paper.sqlite"); p.add_argument("--state-path",default="data/mt5-paper-state.json")
    p.add_argument("--initial-balance",type=float,default=10000); p.add_argument("--once",action="store_true")
    a=p.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    run(a.symbol,a.timeframe,a.timezone,a.session_start,a.volume_field,a.lookback_days,
        a.poll_seconds,a.db_path,a.state_path,a.initial_balance,a.once)


if __name__=="__main__": main()
