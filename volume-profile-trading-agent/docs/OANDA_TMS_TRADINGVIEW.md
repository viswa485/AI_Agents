# OANDA + TradingView setup

This guide is specific to OANDA's EU/TMS documentation. OANDA has multiple regulated divisions; verify the legal entity on your account agreement/portal before using TMS server and symbol candidates.

## 1. Connect OANDA to TradingView

OANDA's EU help guide says:
1. Sign in to TradingView.
2. Open the OANDA broker page and choose Trade → Connect.
3. Select "Login for OANDA EU and TMS clients".
4. Sign in using OANDA credentials and complete 2FA.
5. Open Products → Supercharts and select the required OANDA sub-account.
6. Tradeable OANDA TMS symbols in TradingView have the `.OTMS` suffix. The guide's example is `EURUSD.PRO.OTMS`. Search for Gold in the connected OANDA list and use the precise listed tradeable ticker; this repository deliberately leaves `gold_symbol` blank until you confirm it.

The OANDA guide states a live account is a prerequisite for the connected broker panel. Our local simulator remains paper-only; do not place trades through TradingView as part of this project.

## 2. OANDA TMS MT5 read-only market data

If your account agreement identifies OANDA TMS Brokers S.A.:
- Server in OANDA's EU MT5 guide: `OANDATMS-MT5`.
- TMS MT5 instruments use the `.pro` suffix.
- OANDA's Gold product page lists `GOLD.pro`.

The adapter checks the exact symbol with MT5 `symbol_info` and selects it in Market Watch if required. Confirm `GOLD.pro` is available to your account before running.

Install on the Windows machine/VPS with MT5:
```powershell
pip install -e ".[mt5,dev]"
vp-mt5-paper --symbol GOLD.pro --profile-timeframe M1 --timeframe M5 --timezone Europe/London --session-start 00:00
```
The timezone/session start above are examples only. Set the same session interval as TradingView, after checking MT5 broker/server time and DST. The monitor only reads completed M1/M5 bars and writes simulated trades to SQLite; no broker order method is called.

## 3. Why not OANDA v20 REST?

OANDA's developer documentation says v20 accounts are unavailable to OANDA TMS Brokers S.A. Therefore do not assume a v20 API token can connect to a TMS account. For the TMS route this project uses the MT5 terminal as a read-only feed.

## 4. Compare TradingView and Python levels

1. In TradingView, open the connected OANDA Gold tradeable symbol (suffix `.OTMS`) and an M5 chart.
2. Use Fixed Range Volume Profile over exactly the prior complete session.
3. Set 60 rows and Value Area Volume 70%.
4. In the paper monitor, profile bars are M1 and signal bars M5. Ensure the timezone/session boundary matches the exact range drawn in TradingView.
5. Compare POC, VAH and VAL. Record any difference; the OHLC volume allocation is approximate and cannot be expected to exactly clone TradingView's internal calculation.

## 5. Security

Never commit OANDA/MT5 passwords, account IDs or tokens. Keep the agent in paper mode and keep local API bound to localhost.
