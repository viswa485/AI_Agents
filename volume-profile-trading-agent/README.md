# Volume Profile Trading Agent

Paper-trading-first implementation of the supplied Volume Profile Trading Blueprint. Primary target: XAU/USD via read-only MT5 data. The same broker-independent rules support FX OHLCV and public crypto OHLCV.

## Strategies
1. POC Bounce — previous session closes outside Value Area; price retests POC; engulfing rejection confirms direction.
2. Value Area Reversal — previous session closes inside value; price closes outside VAH/VAL, then a completed candle closes back inside.
3. Breakout — close outside VAH/VAL, pullback/hold near boundary, then close through intervening swing extreme (BOS).

The PDF specifies 60 profile rows, 70% value area and approximately 2R. It does not define session clock, rejection tolerances, swing/BOS algorithm, stop buffers or pullback tolerance. These are explicit configurable engineering assumptions and require validation.

## Architecture
```text
MT5 read-only / CSV / CCXT OHLCV
          -> UTC sessions
          -> Fixed Range Volume Profile (POC/VAH/VAL)
          -> POC Bounce | VA Reversal | Breakout/BOS
          -> deterministic risk checks
          -> SQLite paper broker / backtest
          -> CLI / optional local API
```

## Install
Python 3.10+:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```
Optional: `.[mt5]` on Windows with MT5 terminal, `.[crypto]` for CCXT, `.[api]` for FastAPI. Official MetaTrader5 Python package is Windows-oriented; use a Windows VPS/terminal for MT5 data, macOS for strategy research.

## CLI
Profile: `vp-agent profile --csv bars.csv --symbol XAUUSD --start 2026-10-29T00:00:00Z --end 2026-10-30T00:00:00Z`

Scan: `vp-agent scan --csv bars.csv --symbol XAUUSD --timezone Europe/London --session-start 00:00`

Backtest: `vp-agent backtest --csv bars.csv --symbol XAUUSD --timezone Europe/London --session-start 00:00 --initial-balance 10000 --risk-fraction 0.0025`

The session settings above are examples, not assumptions about your broker. Confirm market hours, server timezone and DST before using real data.

## Limitations
- Profile allocation uses an OHLC-range estimate: each bar's chosen volume is distributed uniformly over its low-to-high range. This conserves volume but is not transaction-level volume-at-price reconstruction.
- MT5 exposes tick_volume and real_volume separately. FX/CFD tick volume counts price updates, not global traded contract quantity.
- XAU/USD spot/CFD data is broker-specific. Exact symbol, volume source and session must be confirmed.
- CCXT volume units vary by exchange/market; verify base versus quote volume.
- Backtest uses signal-bar close and OHLC exits. If SL and TP both hit in one bar, stop wins.
- No broker-specific spread, commission, slippage, swap, financing, tick value, contract size or latency model yet. Results are not execution-grade.
- Paper quantity is abstract units, not MT5 lot sizing.

## Safety
This version is paper-only. MT5 and CCXT adapters are read-only; no live order API exists. Do not commit broker passwords/API keys. Never treat backtests as a guarantee of future results.
