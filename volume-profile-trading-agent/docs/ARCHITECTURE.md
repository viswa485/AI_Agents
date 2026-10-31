# Architecture

1. **Inputs:** CSV, read-only MT5 historical rates, or optional public CCXT OHLCV.
2. **Session grouping:** explicit IANA timezone and local session start; no broker session is inferred.
3. **Profile:** 60 price rows, 70% target; POC/VAH/VAL.
4. **Strategy detectors:** independent POC Bounce, Value Area Reversal and Breakout/BOS.
5. **Risk controls:** validate entry/stop/target geometry, abstract risk sizing, trade-count and daily-loss caps.
6. **Paper broker:** SQLite journal and completed-bar stop/target simulation.
7. **Interfaces:** CLI and optional local FastAPI endpoints.

## Safety boundary
The MT5 adapter only initializes the terminal, reads `copy_rates_range`, and shuts down. CCXT adapter only calls public OHLCV. The paper broker has no network connection. There is no `order_send`, no exchange private order call, and no live execution endpoint in this version.
