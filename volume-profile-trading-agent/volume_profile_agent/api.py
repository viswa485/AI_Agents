"""Optional local FastAPI profile/scan and paper API. No live trading endpoints."""
import os
import pandas as pd
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from .profile import ProfileConfig,calculate_profile
from .strategies import scan_all,Signal
from .risk_paper import PaperBroker,RiskConfig

class Bar(BaseModel):
    time:str; open:float; high:float; low:float; close:float
    tick_volume:float=0; real_volume:float=0; volume:float=0

class ProfileRequest(BaseModel):
    symbol:str="XAUUSD"; bars:list[Bar]; row_count:int=60; value_area_pct:float=.70
    volume_field:str="tick_volume"

class ScanRequest(ProfileRequest):
    current_session_bars:list[Bar]
    previous_session_close:float

class PaperSignalRequest(BaseModel):
    signal_id:str; symbol:str; strategy:str; side:str; timestamp:str
    entry:float; stop:float; target:float; risk_per_unit:float; reward_risk:float=2
    reason:str; metadata:dict=Field(default_factory=dict)

class MarkBarRequest(BaseModel):
    symbol:str; time:str; high:float; low:float; close:float

app=FastAPI(title="Volume Profile Trading Agent",version="0.2.1",description="Research and local paper simulation; no live execution.")
paper=PaperBroker(os.getenv("VP_PAPER_DB","data/paper.sqlite"),float(os.getenv("VP_INITIAL_BALANCE","10000")),RiskConfig())

@app.get("/health")
def health():
    return {"status":"ok","mode":"paper_only","live_execution":False}

@app.post("/v1/profile")
def profile_endpoint(req:ProfileRequest):
    try:
        frame=pd.DataFrame([b.model_dump() for b in req.bars])
        result=calculate_profile(frame,ProfileConfig(req.row_count,req.value_area_pct,req.volume_field),symbol=req.symbol)
        return result.to_dict()
    except (ValueError,TypeError) as exc: raise HTTPException(422,str(exc)) from exc

@app.post("/v1/scan")
def scan_endpoint(req:ScanRequest):
    try:
        prior=pd.DataFrame([b.model_dump() for b in req.bars])
        current=pd.DataFrame([b.model_dump() for b in req.current_session_bars])
        profile=calculate_profile(prior,ProfileConfig(req.row_count,req.value_area_pct,req.volume_field),symbol=req.symbol)
        signals=scan_all(current,profile,req.previous_session_close)
        return {"profile":profile.to_dict(),"signals":[s.to_dict() for s in signals],"live_execution":False}
    except (ValueError,TypeError) as exc: raise HTTPException(422,str(exc)) from exc

@app.post("/v1/paper/signals")
def submit_signal(req:PaperSignalRequest):
    try:
        signal=Signal(**req.model_dump())
        return paper.submit(signal)
    except (ValueError,TypeError) as exc: raise HTTPException(422,str(exc)) from exc

@app.post("/v1/paper/mark-bar")
def mark_bar(req:MarkBarRequest):
    try:
        return {"closed_trades":paper.on_bar(req.symbol,{"time":req.time,"high":req.high,"low":req.low,"close":req.close})}
    except (ValueError,TypeError) as exc: raise HTTPException(422,str(exc)) from exc

@app.get("/v1/paper/account")
def account(): return paper.account()

@app.get("/v1/paper/trades")
def trades(status:str|None=None):
    try: return paper.trades(status)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
