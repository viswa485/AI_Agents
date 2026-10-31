"""Fixed-range Volume Profile with transparent OHLC-range volume allocation."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from typing import Any
import numpy as np
import pandas as pd


@dataclass(frozen=True,slots=True)
class ProfileConfig:
    row_count:int=60
    value_area_pct:float=.70
    volume_field:str="tick_volume"
    def __post_init__(self):
        if self.row_count<2: raise ValueError("row_count must be >= 2")
        if not 0<self.value_area_pct<=1: raise ValueError("value_area_pct must be in (0, 1]")
        if self.volume_field not in {"tick_volume","real_volume","volume"}:
            raise ValueError("volume_field must be tick_volume, real_volume or volume")


@dataclass(frozen=True,slots=True)
class VolumeProfile:
    symbol:str
    row_count:int
    value_area_pct:float
    volume_field:str
    allocation_method:str
    profile_low:float
    profile_high:float
    total_volume:float
    poc_index:int
    poc:float
    poc_volume:float
    vah:float
    val:float
    included_value_area_volume:float
    value_area_target_reached:bool
    rows:tuple[dict[str,Any],...]
    def to_dict(self): return asdict(self)


def calculate_profile(bars:pd.DataFrame,config:ProfileConfig|None=None,*,symbol="XAUUSD")->VolumeProfile:
    """Calculate profile from bars already restricted to one session.

    Each bar's selected volume is split over bins in proportion to overlap
    with [low, high]. This is an OHLC estimate, not transaction-level replay.
    """
    cfg=config or ProfileConfig()
    missing={"high","low",cfg.volume_field}-set(bars.columns)
    if missing: raise ValueError(f"Missing columns: {sorted(missing)}")
    if bars.empty: raise ValueError("No bars supplied")
    high=pd.to_numeric(bars.high,errors="coerce").to_numpy(float)
    low=pd.to_numeric(bars.low,errors="coerce").to_numpy(float)
    vol=pd.to_numeric(bars[cfg.volume_field],errors="coerce").to_numpy(float)
    if not np.isfinite(np.column_stack([high,low,vol])).all() or np.any(high<low) or np.any(vol<0) or vol.sum()<=0:
        raise ValueError("Invalid OHLC/volume data")
    lo,hi=float(low.min()),float(high.max())
    if hi<=lo: raise ValueError("Price range must have positive width")
    edges=np.linspace(lo,hi,cfg.row_count+1); row_vol=np.zeros(cfg.row_count)
    for a,b,volume in zip(low,high,vol,strict=True):
        if volume==0: continue
        if b==a:
            idx=min(max(int(np.searchsorted(edges,a,side="right")-1),0),cfg.row_count-1)
            row_vol[idx]+=volume; continue
        first=min(max(int(np.searchsorted(edges,a,side="right")-1),0),cfg.row_count-1)
        last=min(max(int(np.searchsorted(edges,b,side="left")),0),cfg.row_count-1)
        for idx in range(first,last+1):
            overlap=max(0.0,min(b,edges[idx+1])-max(a,edges[idx]))
            row_vol[idx]+=volume*overlap/(b-a)
    total=float(row_vol.sum())
    if not np.isclose(total,vol.sum(),rtol=1e-9,atol=1e-8):
        raise RuntimeError("Volume allocation failed conservation check")
    poc_idx=int(np.argmax(row_vol)); target=total*cfg.value_area_pct
    included=float(row_vol[poc_idx]); lower=upper=poc_idx; above,below=poc_idx+1,poc_idx-1
    eps=max(1e-12,total*1e-12)
    while included+eps<target and (above<cfg.row_count or below>=0):
        if above>=cfg.row_count: chosen,direction=below,"below"
        elif below<0: chosen,direction=above,"above"
        elif row_vol[above]>row_vol[below]: chosen,direction=above,"above"
        elif row_vol[below]>row_vol[above]: chosen,direction=below,"below"
        else:
            # TradingView tie break: choose the candidate closer to POC;
            # if distances are equal, choose the upper row.
            dist_above=abs(above-poc_idx); dist_below=abs(below-poc_idx)
            if dist_above<dist_below: chosen,direction=above,"above"
            elif dist_below<dist_above: chosen,direction=below,"below"
            else: chosen,direction=above,"above"
        candidate=float(row_vol[chosen])
        if candidate>target-included+eps: break
        included+=candidate
        if direction=="above": upper,above=chosen,chosen+1
        else: lower,below=chosen,chosen-1
    rows=tuple({"index":i,"price_low":float(edges[i]),"price_high":float(edges[i+1]),
        "price_mid":float((edges[i]+edges[i+1])/2),"volume":float(row_vol[i]),
        "volume_pct":float(row_vol[i]/total*100),"in_value_area":lower<=i<=upper}
        for i in range(cfg.row_count))
    return VolumeProfile(symbol,cfg.row_count,cfg.value_area_pct,cfg.volume_field,
        "range_uniform_ohlc_estimate",lo,hi,total,poc_idx,float((edges[poc_idx]+edges[poc_idx+1])/2),
        float(row_vol[poc_idx]),float(edges[upper+1]),float(edges[lower]),included,included+eps>=target,rows)
