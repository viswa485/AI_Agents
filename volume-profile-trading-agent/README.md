# Volume Profile Trading Agent

Paper-trading-first implementation of the supplied Volume Profile Trading Blueprint.

**Intended setup:** TradingView charts + OANDA MT5 read-only market data + local paper simulator. **User-confirmed MT5 symbol:** `XAUUSD`. Primary market: Gold CFD. Account division and server are still checked by the diagnostic. No live order endpoint exists.

## Strategies
1. POC Bounce — previous session closes outside Value Area; price retests POC; engulfing rejection confirms direction.
2. Value Area Reversal — previous session closes inside value; price closes outside VAH/VAL then a completed candle closes back inside.
3. Breakout — close outside VAH/VAL, pullback/hold near boundary, then close through the intervening swing extreme (BOS).

The PDF specifies 60 profile rows, 70% value area and approximately 2R. It does not define session clock, rejection tolerance, swing/BOS algorithm, stop buffer or pullback tolerance; these are configurable engineering assumptions.

## OANDA MT5 connection check (Windows)

1. Open the OANDA MT5 desktop terminal and log in to the account. Do not send credentials to this project or GitHub.
2. Confirm `XAUUSD` is present in Market Watch (you confirmed this symbol).
3. On the same Windows machine, install the project and run:

```powershell
pip install -e ".[mt5,dev]"
vp-mt5-check --symbol XAUUSD --expected-server OANDATMS-MT5 --lookback-hours 168 --output results/oanda-mt5-check.json
```

The diagnostic prints the terminal company/name, broker server, symbol metadata and available M1/M5 history. It deliberately omits account login, account number, balance, equity and credentials. It does not submit, modify or close orders. If your account is not on the TMS division/server, pass its server name in `--expected-server` after verifying the account entity.

## Paper monitor (Windows; only after connection diagnostic passes)

```powershell
vp-mt5-paper --symbol XAUUSD --profile-timeframe M1 --timeframe M5 --timezone Europe/London --session-start 00:00
```

The timezone/session start above are examples only. Confirm the session interval against your OANDA feed and TradingView chart before starting. M1 completed bars build the prior-session profile; M5 completed bars are used for strategy confirmation. The monitor only reads history and writes simulated paper trades to local SQLite. It does not submit MT5 orders.

## TradingView comparison

For OANDA TMS, the official TradingView guide says tradeable symbols have the `.OTMS` suffix and its example is `EURUSD.PRO.OTMS`. Search for Gold in the connected OANDA symbol list; do not guess the complete ticker. Select the OANDA feed and use the same session, M1 source data, 60 rows and 70% Value Area. The Python profile allocates M1 candle volume uniformly across each candle's low-high range, so level differences from TradingView are expected.

## Install and test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Optional extras: `.[mt5]` on Windows with MT5 terminal; `.[crypto]` for CCXT; `.[api]` for FastAPI.

## Other commands

```bash
vp-agent profile --csv sample_data/synthetic_example.csv --symbol SAMPLE --start 2026-10-29T00:00:00Z --end 2026-10-30T00:00:00Z
vp-agent scan --csv market.csv --symbol XAUUSD --timezone Europe/London --session-start 00:00
vp-agent backtest --csv market.csv --symbol XAUUSD --timezone Europe/London --session-start 00:00
```

## Limitations
- MT5 tick volume is price-update count; real_volume is a separate field. Gold CFD volume is broker-feed data, not a consolidated COMEX futures tape.
- Profile allocation is an OHLC estimate, not transaction-level volume-at-price.
- Backtesting lacks broker-specific spreads, commissions, slippage, swaps, tick value, contract-size/lot calculation and latency modelling. Paper quantity is abstract risk units, not MT5 lots.
- If stop and target both touch within one OHLC bar, simulator assumes stop first.
- Synthetic samples are software tests, not market history or performance claims.
- No live order endpoint exists. Keep paper mode and credentials private.
