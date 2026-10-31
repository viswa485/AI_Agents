# Volume Profile Trading Agent

Paper-trading-first implementation of the supplied Volume Profile Trading Blueprint.

**Primary market:** XAU/USD via read-only MT5 market data. Same strategy engine supports forex CSV/MT5 bars and crypto OHLCV. **Execution mode:** local paper simulation only. No live order API exists.

## Strategies
1. **POC Bounce:** previous session closes outside Value Area, price retests POC, engulfing rejection confirms direction.
2. **Value Area Reversal:** previous session closes inside value, price closes outside VAH/VAL, then a completed candle closes back inside.
3. **Breakout:** price closes outside VAH/VAL, pulls back/holds near boundary and closes through intervening swing extreme (BOS).

The PDF specifies 60 profile rows, 70% value area and approximately 2R. It does not define session clock, rejection tolerances, swing/BOS algorithm, stop buffer or pullback tolerance. These are configurable engineering assumptions and require validation.

## Install
Python 3.10+:
```bash
cd volume-profile-trading-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```
Optional dependencies: `.[mt5]` on Windows with MT5 installed; `.[crypto]` for CCXT; `.[api]` for FastAPI. The official MetaTrader5 Python package is Windows-oriented. Develop on macOS and run the MT5 data bridge on a Windows machine/VPS.

## Commands
One explicit profile:
```bash
vp-agent profile --csv sample_data/synthetic_example.csv --symbol XAUUSD-SYNTHETIC --start 2026-10-29T00:00:00Z --end 2026-10-30T00:00:00Z
```
Previous observed-session scan:
```bash
vp-agent scan --csv sample_data/synthetic_example.csv --symbol XAUUSD-SYNTHETIC --timezone UTC --session-start 00:00
```
Historical paper backtest:
```bash
vp-agent backtest --csv market.csv --symbol XAUUSD --timezone Europe/London --session-start 00:00 --initial-balance 10000 --risk-fraction 0.0025
```

## MT5 read-only -> paper monitor (Windows)
```powershell
pip install -e ".[dev,mt5]"
vp-mt5-paper --symbol XAUUSD --timeframe M5 --timezone Europe/London --session-start 00:00
```
Supply the exact Market Watch symbol, including broker suffix. The sample timezone/session are examples only; confirm your broker's session schedule and DST. The monitor reads completed MT5 bars and submits signals only to the local SQLite paper simulator. It does not call MT5 order APIs. Paper database: `data/paper.sqlite`; processed-bar cursor: `data/mt5-paper-state.json`.

Crypto public OHLCV export: `vp-export-ccxt --exchange binance --symbol BTC/USDT --timeframe 5m --limit 1000 --output btc.csv`.

Optional local API: `pip install -e ".[api]" && uvicorn volume_profile_agent.api:app --host 127.0.0.1 --port 8000`. Endpoints: GET `/health`, POST `/v1/profile`, POST `/v1/scan`, POST `/v1/paper/signals`, POST `/v1/paper/mark-bar`, GET `/v1/paper/account`, GET `/v1/paper/trades`.

## Important limitations
- OHLC volume allocation is a transparent estimate, not transaction-level volume-at-price reconstruction.
- MT5 tick_volume is price-update count; real_volume is separate. FX/CFD XAUUSD data is broker-specific.
- CCXT volume units differ by venue; verify base versus quote volume.
- Backtest is bar-based, assumes stop first if stop and target hit in the same candle, and currently lacks broker-specific spread/commission/slippage/swap/contract-size modelling.
- Paper quantity is abstract price-risk units, not MT5 lots. No live execution exists.
- Synthetic sample data is not market history or a performance claim.

All backtest results are research outputs and do not guarantee future results.
