"""Read-only public CCXT OHLCV adapter and CSV exporter."""
import argparse
import pandas as pd


class CCXTHistoricalFeed:
    def __init__(self,exchange_id):
        try: import ccxt
        except ImportError as exc: raise RuntimeError("Install optional dependency: pip install -e '.[crypto]'") from exc
        cls=getattr(ccxt,exchange_id,None)
        if cls is None: raise ValueError(f"Unknown CCXT exchange: {exchange_id}")
        self.exchange=cls({"enableRateLimit":True})
        if (getattr(self.exchange,"has",{}) or {}).get("fetchOHLCV") is False: raise ValueError("fetchOHLCV unsupported")
    def fetch_ohlcv(self,symbol,timeframe="5m",since=None,limit=1000):
        if "/" not in symbol or not 1<=limit<=1000: raise ValueError("Use unified symbol BTC/USDT and limit 1..1000")
        rows=self.exchange.fetch_ohlcv(symbol,timeframe,since,limit)
        if not rows: raise ValueError("No OHLCV returned")
        f=pd.DataFrame(rows,columns=["timestamp_ms","open","high","low","close","volume"])
        f["time"]=pd.to_datetime(f.pop("timestamp_ms"),unit="ms",utc=True)
        return f[["time","open","high","low","close","volume"]]
    def close(self): self.exchange.close()


def main():
    p=argparse.ArgumentParser(description="Export public exchange OHLCV only; no trading.")
    p.add_argument("--exchange",required=True); p.add_argument("--symbol",required=True)
    p.add_argument("--timeframe",default="5m"); p.add_argument("--limit",type=int,default=1000); p.add_argument("--output",required=True)
    a=p.parse_args(); feed=CCXTHistoricalFeed(a.exchange)
    try: frame=feed.fetch_ohlcv(a.symbol,a.timeframe,limit=a.limit)
    finally: feed.close()
    frame.to_csv(a.output,index=False); print(f"Wrote {len(frame)} bars. Verify base/quote volume units.")
