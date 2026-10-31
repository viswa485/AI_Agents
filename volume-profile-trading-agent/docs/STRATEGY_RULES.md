# Strategy rules and assumptions

## POC Bounce
The PDF requires the previous session to end outside the Value Area, a return to POC and rejection confirmation. This implementation uses bullish/bearish engulfing as an explicit example confirmation. Engulfing direction determines the long/short side. POC tolerance is ATR-scaled; the PDF does not specify a distance.

## Value Area Reversal
The previous session must close inside the Value Area. A completed candle closes outside VAH/VAL, then a later completed candle closes back inside. Wicks alone do not qualify. Stop is beyond a recent configured swing plus an ATR buffer. The PDF does not define the swing calculation or buffer.

## Breakout
A completed close outside VAH/VAL starts the setup. A later candle retests near the boundary and does not close too deeply back inside. BOS is defined as a close beyond the most extreme high/low between breakout and pullback. Stop is beyond the pullback swing plus ATR buffer.

All three use 2R target construction. Entries use confirmation-bar close for historical research. Stop buffers, tolerances, swing rules and session definition are engineering assumptions requiring out-of-sample validation.
