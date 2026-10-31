# OANDA MT5 + TradingView setup

## Confirmed account detail

The user confirms that **`XAUUSD` appears in their OANDA MT5 Market Watch**. This project uses exactly that symbol and does not silently rewrite it as `GOLD.pro`.

There is a documentation detail to check: OANDA's current OANDA TMS MT5 guide names the server `OANDATMS-MT5` and says TMS instruments typically end in `.pro`. Since the user's terminal displays `XAUUSD`, run the diagnostic to inspect the actual logged-in server and symbol metadata. The account division is not inferred from geography or the symbol name.

## 1. Read-only terminal diagnostic

On the Windows machine running the OANDA MT5 desktop terminal:

1. Start MT5 and log into your own account.
2. Confirm XAUUSD is visible in Market Watch.
3. Open PowerShell in this project folder.
4. Install: `pip install -e ".[mt5,dev]"`
5. Run:

```powershell
vp-mt5-check --symbol XAUUSD --expected-server OANDATMS-MT5 --lookback-hours 168 --output results/oanda-mt5-check.json
```

The tool reports the terminal company/name, connected server, XAUUSD symbol properties and M1/M5 history counts/timestamps. It does **not** display account login, account number, balance, equity or credentials. It does not use any order placement/modification API. If the server is different, verify the OANDA legal entity and server in the MT5 login/account details before changing `--expected-server`.

## 2. OANDA TMS reference

OANDA's EU TMS MT5 help guide identifies `OANDATMS-MT5` as the server and notes that TMS instrument names generally end in `.pro`. The user-confirmed `XAUUSD` must be checked against the live terminal rather than assumed invalid or changed automatically.

## 3. TradingView chart

For OANDA TMS, OANDA's TradingView guide says tradeable tickers have the `.OTMS` suffix (example `EURUSD.PRO.OTMS`). Search Gold after connecting the OANDA account, then record the exact tradeable ticker from the list. The account-specific Gold TradingView symbol remains intentionally blank until observed.

## 4. Compare profile levels

Use the same OANDA feed and exact completed session:
- Chart: connected OANDA Gold symbol on TradingView.
- Fixed Range Volume Profile: 60 rows, 70% Value Area.
- Agent: M1 closed bars for profile, M5 closed bars for strategy signals.
- Session: set the same confirmed timezone/open/close on both platforms.

The agent's allocation spreads M1 volume uniformly across each candle range. It is an OHLC estimate, not a reconstruction of each tick, so POC/VAH/VAL need not match TradingView exactly.

## 5. Paper monitor after diagnostics

Only after the diagnostic confirms terminal, server, symbol and data availability:

```powershell
vp-mt5-paper --symbol XAUUSD --profile-timeframe M1 --timeframe M5 --timezone Europe/London --session-start 00:00
```

Replace the example session timezone and start with the actual session you use in TradingView. The MT5 adapter is read-only; all orders are simulated in local SQLite.
