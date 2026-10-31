# Market data notes

## XAU/USD through MT5
Use the broker's exact Market Watch symbol, including suffix/prefix. MT5 returns tick_volume and real_volume separately. FX/CFD tick volume is a count of price changes, not centralised traded contracts. The correct broker, session clock and timezone have not yet been supplied; configure them rather than guessing.

## Futures cross-check
CME/COMEX gold futures volume can be used as an additional market-context feed, but GC/MGC futures are different instruments from broker spot/CFD XAU/USD. Do not combine their histograms as though they were one consolidated tape.

## Crypto
CCXT returns exchange OHLCV. Confirm the exchange's definition and whether the chosen market reports base or quote volume. Spot and perpetual/futures instruments should be configured separately.

## Profile fidelity
The current OHLC bar allocation distributes the selected bar volume uniformly across the bar's high-low range. Use lower timeframe bars to reduce granularity error; actual trade ticks are preferable where available. Matching TradingView requires identical underlying data, period, binning, volume source and calculation settings.
