# OANDA MT5 + TradingView setup

## Confirmed symbol

The user has confirmed that **`XAUUSD` appears in their OANDA MT5 Market Watch**. The agent uses exactly this symbol. It does not silently rename it to `GOLD.pro`.

OANDA's EU TMS MT5 guide identifies the server as `OANDATMS-MT5`. Its TMS instrument guide says many instruments use a `.pro` suffix, while OANDA's EU execution-policy supplement also lists `XAUUSD` among quoted gold CFD symbols. The diagnostic inspects the actual logged-in terminal/server and exact symbol metadata rather than assuming a suffix.

## 1. Read-only terminal login

For an extra safety boundary, OANDA's MT5 guide documents an **Investor (read-only) password**. It allows viewing account activity/history but does not permit entering or modifying orders.

In MT5:
1. Tools → Options.
2. Server tab → Change.
3. Select **Change Investor (read only) password**.
4. Set the investor password.
5. Use a separate data-only MT5 terminal instance logged in with the investor password for this project.

Do not send passwords or account numbers to this project or GitHub.

## 2. Run diagnostic (Windows)

The official Python `MetaTrader5` package on PyPI currently publishes Windows x86-64 wheels only. OANDA provides an MT5 Mac installer, but native macOS Python cannot install that official package directly. Run this diagnostic on a Windows machine/VPS with the OANDA MT5 terminal installed:

```powershell
pip install -e ".[mt5,dev]"
vp-mt5-check --symbol XAUUSD --expected-server OANDATMS-MT5 --lookback-hours 168 --output results/oanda-mt5-check.json
```

The command returns terminal company/name, broker server, symbol metadata and M1/M5 history counts/timestamps. It deliberately omits account login, account number, balance, equity and credentials. It never submits, modifies or closes orders.

If the expected server substring fails, verify the server from the terminal's login/account information. OANDA's documentation says `OANDATMS-MT5`; a live/demo server display may add a suffix. Only change `--expected-server` after confirming the intended OANDA account division.

## 3. Mac development option

You can keep Python strategy research, CSV processing, API and dashboard development on macOS. For direct Python-to-MT5 market data, use the Windows terminal/connector on a Windows VPS. A separate MQL5-to-CSV exporter can be used if you want the MT5 chart terminal to stay on Mac and avoid the Windows Python package.

## 4. TradingView chart

For OANDA TMS, OANDA's TradingView guide says tradeable tickers have the `.OTMS` suffix (example `EURUSD.PRO.OTMS`). Search for Gold after connecting the OANDA account, then record the exact Gold ticker from the available list. The account-specific Gold TradingView ticker remains blank until observed.

## 5. Compare profile levels

Use the same OANDA feed and exact completed session:
- Chart: connected OANDA Gold symbol on TradingView.
- Fixed Range Volume Profile: 60 rows, 70% Value Area.
- Agent: M1 closed bars for profile, M5 closed bars for strategy signals.
- Session: identical timezone and session range on both platforms.

The agent distributes each M1 bar's selected volume uniformly across its high-low range. This is an OHLC estimate, not a reconstruction of each tick; exact POC/VAH/VAL equality with TradingView is not guaranteed.

## 6. Paper monitor after diagnostics

Only after the diagnostic confirms terminal, server, symbol and data availability:

```powershell
vp-mt5-paper --symbol XAUUSD --profile-timeframe M1 --timeframe M5 --timezone Europe/London --session-start 00:00
```

Replace the example timezone/session start with the actual session used in TradingView. The MT5 adapter is read-only; all entries/exits are simulated in local SQLite.
