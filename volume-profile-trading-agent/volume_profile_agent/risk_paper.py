"""Deterministic risk checks and SQLite paper broker. No live broker calls."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
from pathlib import Path
import json,sqlite3,uuid


@dataclass(frozen=True,slots=True)
class RiskConfig:
    risk_fraction:float=0.0025
    max_daily_loss_fraction:float=0.01
    max_open_positions:int=1
    max_trades_per_day:int=5
    def __post_init__(self):
        if not 0<self.risk_fraction<=0.02: raise ValueError("risk_fraction must be in (0, .02]")
        if not 0<self.max_daily_loss_fraction<=0.10: raise ValueError("daily loss fraction must be in (0, .10]")
        if self.max_open_positions<1 or self.max_trades_per_day<1: raise ValueError("limits must be positive")


class PaperBroker:
    def __init__(self,db_path="data/paper.sqlite",initial_balance=10000,config=None):
        if initial_balance<=0: raise ValueError("initial_balance must be positive")
        self.path=Path(db_path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.initial_balance=float(initial_balance); self.config=config or RiskConfig()
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS trades(
            id TEXT PRIMARY KEY,signal_id TEXT UNIQUE,symbol TEXT,strategy TEXT,side TEXT,entry_time TEXT,
            entry REAL,stop REAL,target REAL,quantity REAL,status TEXT,exit_time TEXT,exit REAL,pnl REAL,
            exit_reason TEXT,metadata TEXT)""")
    def _db(self):
        db=sqlite3.connect(self.path); db.row_factory=sqlite3.Row; return db
    def account(self):
        with self._db() as db: rows=db.execute("SELECT * FROM trades").fetchall()
        closed=[r for r in rows if r["status"]=="CLOSED"]
        pnl=sum(float(r["pnl"] or 0) for r in closed)
        today=datetime.now(timezone.utc).date().isoformat()
        daily=sum(float(r["pnl"] or 0) for r in closed if r["exit_time"] and r["exit_time"][:10]==today)
        return {"balance":self.initial_balance+pnl,"equity":self.initial_balance+pnl,"realized_pnl":pnl,
                "daily_pnl":daily,"open_positions":sum(r["status"]=="OPEN" for r in rows),
                "trades_today":sum(r["entry_time"][:10]==today for r in rows)}
    def submit(self,signal):
        with self._db() as db:
            if db.execute("SELECT 1 FROM trades WHERE signal_id=?",(signal.signal_id,)).fetchone():
                return {"approved":False,"reason":"Duplicate signal"}
            rows=db.execute("SELECT * FROM trades").fetchall()
            realized=sum(float(r["pnl"] or 0) for r in rows if r["status"]=="CLOSED")
            equity=self.initial_balance+realized; day=signal.timestamp[:10]
            daily=sum(float(r["pnl"] or 0) for r in rows if r["status"]=="CLOSED" and r["exit_time"] and r["exit_time"][:10]==day)
            opened=sum(r["status"]=="OPEN" for r in rows); count=sum(r["entry_time"][:10]==day for r in rows)
            if opened>=self.config.max_open_positions: return {"approved":False,"reason":"Max open positions"}
            if count>=self.config.max_trades_per_day: return {"approved":False,"reason":"Max daily trades"}
            if daily<=-equity*self.config.max_daily_loss_fraction: return {"approved":False,"reason":"Daily loss limit"}
            if signal.side=="LONG": valid=signal.stop<signal.entry<signal.target; risk=signal.entry-signal.stop
            else: valid=signal.stop>signal.entry>signal.target; risk=signal.stop-signal.entry
            if not valid or risk<=0 or abs(risk-signal.risk_per_unit)>max(1e-8,risk*1e-6):
                return {"approved":False,"reason":"Invalid entry/SL/TP geometry"}
            cash=equity*self.config.risk_fraction; qty=cash/risk; tid=str(uuid.uuid4())
            db.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (tid,signal.signal_id,signal.symbol,signal.strategy,signal.side,signal.timestamp,
               signal.entry,signal.stop,signal.target,qty,"OPEN",None,None,None,None,json.dumps(signal.metadata)))
            return {"approved":True,"trade_id":tid,"quantity":qty,"risk_cash":cash}
    def on_bar(self,symbol,bar):
        stamp=str(bar["time"])
        if datetime.fromisoformat(stamp.replace("Z","+00:00")).tzinfo is None: raise ValueError("bar time must be timezone-aware")
        hi,lo=float(bar["high"]),float(bar["low"]); closed=[]
        with self._db() as db:
            rows=db.execute("SELECT * FROM trades WHERE symbol=? AND status='OPEN'",(symbol,)).fetchall()
            for r in rows:
                stop_hit=lo<=r["stop"] if r["side"]=="LONG" else hi>=r["stop"]
                target_hit=hi>=r["target"] if r["side"]=="LONG" else lo<=r["target"]
                if not stop_hit and not target_hit: continue
                # Conservative assumption when one OHLC candle hits both: stop first.
                exit_price,reason=(r["stop"],"STOP_LOSS") if stop_hit else (r["target"],"TAKE_PROFIT")
                pnl=(exit_price-r["entry"])*r["quantity"]*(1 if r["side"]=="LONG" else -1)
                db.execute("UPDATE trades SET status='CLOSED',exit_time=?,exit=?,pnl=?,exit_reason=? WHERE id=?",
                           (stamp,exit_price,pnl,reason,r["id"]))
                closed.append({"trade_id":r["id"],"exit":exit_price,"pnl":pnl,"reason":reason})
        return closed
    def trades(self,status=None):
        if status not in (None,"OPEN","CLOSED"): raise ValueError("status must be OPEN or CLOSED")
        with self._db() as db:
            q="SELECT * FROM trades"+(" WHERE status=?" if status else "")+" ORDER BY entry_time"
            rows=db.execute(q,(status,) if status else ()).fetchall()
        return [dict(r) for r in rows]
