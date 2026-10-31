"""Rule-based detectors for the three Volume Profile Blueprint setups."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
from typing import Any
import numpy as np
import pandas as pd
from .profile import VolumeProfile


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    risk_reward: float = 2.0
    atr_period: int = 14
    atr_stop_buffer: float = 0.15
    poc_touch_tolerance_atr: float = 0.15
    swing_lookback: int = 5
    max_breakout_setup_bars: int = 12
    pullback_tolerance_atr: float = 0.35
    max_pullback_depth_atr: float = 0.50


@dataclass(frozen=True, slots=True)
class Signal:
    signal_id: str
    symbol: str
    strategy: str
    side: str
    timestamp: str
    entry: float
    stop: float
    target: float
    risk_per_unit: float
    reward_risk: float
    reason: str
    metadata: dict[str, Any]

    def to_dict(self):
        return asdict(self)


def _prepare(data):
    need = {"time","open","high","low","close"}
    if need-set(data.columns):
        raise ValueError(f"Missing OHLC columns: {sorted(need-set(data.columns))}")
    if data.empty:
        raise ValueError("No bars")
    f=data.copy().sort_values("time").reset_index(drop=True)
    f["time"]=pd.to_datetime(f.time,utc=True,errors="coerce")
    if f.time.isna().any():
        raise ValueError("Invalid bar timestamps")
    for c in ("open","high","low","close"):
        f[c]=pd.to_numeric(f[c],errors="coerce")
    if f[["open","high","low","close"]].isna().any().any() or (f.high<f.low).any():
        raise ValueError("Invalid OHLC")
    return f


def _atr(f, period):
    prev=f.close.shift(1)
    tr=pd.concat([f.high-f.low,(f.high-prev).abs(),(f.low-prev).abs()],axis=1).max(axis=1)
    return tr.rolling(period,min_periods=1).mean().replace(0,1e-8)


def _engulf(a,b):
    if a.close<a.open and b.close>b.open and b.open<=a.close and b.close>=a.open:
        return "LONG"
    if a.close>a.open and b.close<b.open and b.open>=a.close and b.close<=a.open:
        return "SHORT"
    return None


def _make(symbol,strategy,side,row,entry,stop,cfg,reason,meta):
    risk=entry-stop if side=="LONG" else stop-entry
    if not np.isfinite([entry,stop,risk]).all() or risk<=0:
        return None
    target=entry+cfg.risk_reward*risk if side=="LONG" else entry-cfg.risk_reward*risk
    stamp=pd.Timestamp(row.time).isoformat()
    key=f"{symbol}|{strategy}|{side}|{stamp}|{entry:.8f}"
    return Signal(hashlib.sha256(key.encode()).hexdigest()[:20],symbol,strategy,side,stamp,
                  float(entry),float(stop),float(target),float(risk),float(cfg.risk_reward),reason,meta)


def poc_bounce(data, profile: VolumeProfile, prior_close: float, *, config=None):
    """Outside prior close + POC retest + engulfing rejection confirmation."""
    cfg=config or StrategyConfig()
    if profile.val<=prior_close<=profile.vah:
        return []
    f=_prepare(data); f["atr"]=_atr(f,cfg.atr_period)
    result=[]; tolerance=float(f.atr.iloc[-1])*cfg.poc_touch_tolerance_atr
    for i in range(1,len(f)):
        prev,row=f.iloc[i-1],f.iloc[i]
        touched=row.low<=profile.poc+tolerance and row.high>=profile.poc-tolerance
        side=_engulf(prev,row)
        if not touched or side is None:
            continue
        buffer=float(row.atr)*cfg.atr_stop_buffer
        stop=profile.poc-buffer if side=="LONG" else profile.poc+buffer
        sig=_make(profile.symbol,"POC_BOUNCE",side,row,float(row.close),stop,cfg,
                  f"Previous session closed outside value; POC retest and {side.lower()} engulfing rejection.",
                  {"poc":profile.poc,"vah":profile.vah,"val":profile.val,"prior_close":float(prior_close)})
        if sig: result.append(sig)
    return result


def value_area_reversal(data,profile: VolumeProfile,prior_close:float,*,config=None):
    """Prior close inside VA; outside close followed by a candle close back inside."""
    cfg=config or StrategyConfig()
    if not profile.val<=prior_close<=profile.vah:
        return []
    f=_prepare(data); f["atr"]=_atr(f,cfg.atr_period); result=[]
    for i in range(1,len(f)):
        prev,row=f.iloc[i-1],f.iloc[i]
        if prev.close<profile.val and profile.val<=row.close<=profile.vah: side="LONG"
        elif prev.close>profile.vah and profile.val<=row.close<=profile.vah: side="SHORT"
        else: continue
        look=f.iloc[max(0,i-cfg.swing_lookback):i+1]
        buff=float(row.atr)*cfg.atr_stop_buffer
        stop=float(look.low.min()-buff) if side=="LONG" else float(look.high.max()+buff)
        sig=_make(profile.symbol,"VALUE_AREA_REVERSAL",side,row,float(row.close),stop,cfg,
                  f"Completed candle closed back inside value from {'below VAL' if side=='LONG' else 'above VAH'}.",
                  {"poc":profile.poc,"vah":profile.vah,"val":profile.val,"prior_close":float(prior_close)})
        if sig: result.append(sig)
    return result


def breakout(data,profile:VolumeProfile,*,config=None):
    """Break close -> retest/hold near VA boundary -> close through intervening swing (BOS)."""
    cfg=config or StrategyConfig()
    f=_prepare(data); f["atr"]=_atr(f,cfg.atr_period); result=[]; consumed=set()
    for start in range(len(f)-2):
        if start in consumed: continue
        br=f.iloc[start]
        side="LONG" if br.close>profile.vah else "SHORT" if br.close<profile.val else None
        if side is None: continue
        boundary=profile.vah if side=="LONG" else profile.val
        atr=float(br.atr); tol=atr*cfg.pullback_tolerance_atr; depth=atr*cfg.max_pullback_depth_atr
        end=min(len(f)-1,start+cfg.max_breakout_setup_bars); emitted=False
        for ri in range(start+1,end):
            ret=f.iloc[ri]
            held=(ret.low<=boundary+tol and ret.low>=boundary-depth and ret.close>=boundary-depth) if side=="LONG" else (ret.high>=boundary-tol and ret.high<=boundary+depth and ret.close<=boundary+depth)
            if not held: continue
            segment=f.iloc[start:ri+1]
            swing=float(segment.high.max()) if side=="LONG" else float(segment.low.min())
            for bi in range(ri+1,end+1):
                row=f.iloc[bi]
                crossed=row.close>swing if side=="LONG" else row.close<swing
                if not crossed: continue
                buf=float(row.atr)*cfg.atr_stop_buffer
                stop=float(ret.low-buf) if side=="LONG" else float(ret.high+buf)
                sig=_make(profile.symbol,"BREAKOUT",side,row,float(row.close),stop,cfg,
                          f"Value-area breakout, pullback hold and {side.lower()} BOS confirmation.",
                          {"boundary":boundary,"bos_level":swing,"breakout_time":br.time.isoformat(),"pullback_time":ret.time.isoformat()})
                if sig: result.append(sig); consumed.update(range(start,bi+1))
                emitted=True; break
            if emitted: break
    return result


def scan_all(data,profile,prior_close,*,config=None):
    cfg=config or StrategyConfig()
    signals=poc_bounce(data,profile,prior_close,config=cfg)
    signals+=value_area_reversal(data,profile,prior_close,config=cfg)
    signals+=breakout(data,profile,config=cfg)
    unique={s.signal_id:s for s in signals}
    return sorted(unique.values(),key=lambda s:s.timestamp)
