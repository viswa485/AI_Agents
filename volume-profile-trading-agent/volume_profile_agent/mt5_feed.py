"""Read-only MT5 historical-rate adapter. No order_send/trading methods."""
from datetime import datetime,timezone
import pandas as pd


class MT5HistoricalFeed:
    def __init__(self,terminal_path=None):
        try: import MetaTrader5 as mt5
        except ImportError as exc: raise RuntimeError("Install [mt5] on Windows with MT5 terminal") from exc
        self.mt5=mt5; self.terminal_path=terminal_path; self.connected=False
    def connect(self):
        ok=self.mt5.initialize(self.terminal_path) if self.terminal_path else self.mt5.initialize()
        if not ok: raise RuntimeError(f"MT5 initialize failed: {self.mt5.last_error()}")
        self.connected=True
    def ensure_symbol(self,symbol):
        if not self.connected: raise RuntimeError("Connect before checking symbols")
        info=self.mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"MT5 symbol not found: {symbol}. Confirm exact spelling in Market Watch.")
        if not info.visible and not self.mt5.symbol_select(symbol,True):
            raise RuntimeError(f"Unable to select {symbol} in MT5: {self.mt5.last_error()}")
        return {"name":info.name,"description":info.description,"digits":info.digits,
                "point":info.point,"trade_tick_size":info.trade_tick_size,
                "trade_tick_value":info.trade_tick_value,"volume_min":info.volume_min,
                "volume_max":info.volume_max,"volume_step":info.volume_step,
                "currency_base":getattr(info,"currency_base",None),
                "currency_profit":getattr(info,"currency_profit",None),
                "currency_margin":getattr(info,"currency_margin",None)}
    def fetch_rates(self,symbol,timeframe,start:datetime,end:datetime):
        if not self.connected: raise RuntimeError("Call connect before fetch_rates")
        if start.tzinfo is None or end.tzinfo is None or end<=start:
            raise ValueError("Use ordered timezone-aware datetimes")
        self.ensure_symbol(symbol)
        raw=self.mt5.copy_rates_range(symbol,timeframe,start.astimezone(timezone.utc),end.astimezone(timezone.utc))
        if raw is None: raise RuntimeError(f"MT5 copy_rates_range failed: {self.mt5.last_error()}")
        if len(raw)==0: return pd.DataFrame(columns=["time","open","high","low","close","tick_volume","spread","real_volume"])
        f=pd.DataFrame(raw); f["time"]=pd.to_datetime(f.time,unit="s",utc=True)
        return f[(f.time>=pd.Timestamp(start))&(f.time<pd.Timestamp(end))].sort_values("time").reset_index(drop=True)
    def close(self):
        if self.connected: self.mt5.shutdown(); self.connected=False
    def __enter__(self): self.connect(); return self
    def __exit__(self,*_): self.close()
