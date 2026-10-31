# Volume Profile Trading Agent

Paper-trading-first implementation of the supplied Volume Profile Trading Blueprint.

**Intended setup:** TradingView charting + OANDA broker feed + local paper simulator. Primary market: OANDA Gold CFD, with XAU/USD-style gold exposure. OANDA account division must be confirmed before applying the TMS-specific settings.

## Strategies
1. POC Bounce — previous session closes outside Value Area; price retests POC; engulfing rejection confirms direction.
2. Value Area Reversal — previous session closes inside value; price closes outside VAH/VAL then a completed candle closes back inside.
3. Breakout — close outside VAH/VAL, pullback/hold near boundary, then close through the intervening swing extreme (BOS).

The PDF specifies 60 profile rows, 70% value area and approximately 2R. It does not define session clock, rejection tolerance, swing/BOS algorithm, stop buffer or pullback tolerance; these are configurable engineering assumptions.

## OANDA + TradingView

See [OANDA + TradingView setup](docs/OANDA_TMS_TRADINGVIEW.md). For OANDA TMS EU, official documentation lists MT5 server `OANDATMS-MT5`, MT5 instrument suffix `.pro`, and Gold instrument `GOLD.pro`. Treat these as candidates until your account agreement and Market Watch confirm them. Tradeable TMS symbols in TradingView carry `.OTMS`; exact Gold ticker is not hard-coded.

The official OANDA v20 docs exclude TMS Brokers S.A. from v20 account availability, so this project does not assume v20 API access for a TMS account. The MT5 data adapter is read-only.

## Install
Python 3.10+:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```
Optional extras: `.[mt5]` on Windows with MT5 terminal; `.[crypto]` for CCXT; `.[api]` for FastAPI.

## OANDA MT5 paper monitor (Windows)
```powershell
pip install -e ".[mt5,dev]"
vp-mt5-paper --symbol GOLD.pro --profile-timeframe M1 --timeframe M5 --timezone Europe/London --session-start 00:00
```
Symbol, timezone and session above are examples/candidates; verify exact Market Watch symbol and use the identical previous-session interval as TradingView. The monitor calculates profile from completed M1 bars and evaluates signals on completed M5 bars.

## Other commands
```bash
vp-agent profile --csv sample_data/synthetic_example.csv --symbol SAMPLE --start 2026-10-29T00:00:00Z --end 2026-10-30T00:00:00Z
vp-agent scan --csv market_m5.csv --profile-csv market_m1.csv --symbol GOLD.pro --timezone Europe/London --session-start 00:00
vp-agent backtest --csv market_m5.csv --profile-csv market_m1.csv --symbol GOLD.pro --timezone Europe/London --session-start 00:00
```
The session settings are examples and must be confirmed.

Optional local API: `pip install -e ".[api]" && uvicorn volume_profile_agent.api:app --host 127.0.0.1 --port 8000`. Public crypto OHLCV export: `vp-export-ccxt --exchange binance --symbol BTC/USDT --timeframe 5m --limit 1000 --output btc.csv`.

## Limitations
- Volume Profile uses M1 bars by default for the previous session. The selected M1 volume is spread uniformly across each bar's low-high range, a transparent OHLC estimate rather than tick-level volume-at-price. Differences from TradingView are expected.
- TradingView documents tick volume for forex/CFD Volume Profile; MT5 exposes tick_volume and real_volume separately.
- OANDA Gold CFD data is broker-feed data, not consolidated COMEX futures volume.
- Backtesting lacks real broker spread/commission/slippage/swap and contract-size/lot calculation. Paper quantity is abstract risk units, not MT5 lots.
- If stop and target both touch in one OHLC bar, simulator assumes stop first.
- No live order endpoint exists. Synthetic samples are software tests, not market data or performance claims.
