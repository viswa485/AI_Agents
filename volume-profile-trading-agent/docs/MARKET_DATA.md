# Market data notes

## Intended integration: TradingView + OANDA

The OANDA EU help centre distinguishes OANDA divisions. It says residents of EU member states may apply for an OANDA TMS account; verify the legal entity named in your own account agreement before applying the TMS settings below.

For OANDA TMS:
- Official MT5 guide lists server `OANDATMS-MT5`.
- The same guide says OANDA TMS instrument names end in `.pro`.
- OANDA's EU Gold instrument page lists `GOLD.pro`. This is a candidate and the adapter will verify exact symbol visibility in Market Watch.
- OANDA's TradingView TMS guide says tradeable TradingView tickers carry `.OTMS`; its example is `EURUSD.PRO.OTMS`. Do not guess the exact Gold ticker: select it in TradingView's connected OANDA instrument list.
- The TradingView guide states its chart prices are indicative and may differ from actual execution prices.

OANDA's v20 REST API requires a v20 account and explicitly excludes OANDA TMS Brokers S.A. accounts. Do not assume v20 API access if your account is TMS. This project currently uses MT5 read-only data for that account path. No credentials belong in YAML or GitHub.

## Two-resolution profile and signal workflow

The paper monitor now defaults to:
- M1 completed bars for the previous-session profile (60 rows, 70% VA).
- M5 completed bars for current-session strategy confirmation.

TradingView explains that its Volume Profile calculates from lower-timeframe data for the same symbol and that it uses tick volume for forex and crypto CFDs (price-update count). This is why using M1 profile input is a better comparison starting point than calculating from M5 alone.

The Python implementation still distributes each M1 candle's selected volume uniformly across its high-low interval. That is an OHLC range estimate, not reconstruction of each tick's exact traded price. Expect differences from TradingView even with identical session and feed. For a valid comparison use same OANDA feed, same completed session, same timezone, same M1 history, same 60 rows and 70% VA.

## Session alignment

No session boundary is assumed. Set an IANA timezone and local session start only after confirming the exact session range you use on TradingView and the MT5 broker/server time conversion. Daylight-saving changes must be handled. The code does not infer OANDA's gold dealing hours from the symbol.

## Multiple asset classes

CCXT crypto OHLCV is an independent exchange feed; confirm market (spot vs perpetual), symbol and base/quote volume units. FX symbols in config are examples to verify in the connected account.
