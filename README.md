# HFT Trading Bot (Solo Developer Edition)

An asynchronous High-Frequency Trading (HFT) bot built in Python. Designed for speed, reliability, and modularity, this project is tailored for a single developer focusing on short-term intraday strategies (Mean Reversion, RSI, and Momentum).

## 🚀 Key Features

- **Asynchronous Architecture**: Powered by `asyncio` for non-blocking market data ingestion and order execution.
- **WebSocket-First**: Real-time ticker streaming via Binance Spot WebSockets with automatic reconnection.
- **Multi-Strategy Ensemble**: Combines multiple "expert" strategies (SMA, RSI, Momentum) to reduce false signals.
- **Robust Risk Management**: Built-in safety guards for max position sizing, daily loss limits, and global drawdown.
- **Backtest Engine**: Integrated historical simulation tool (`backtester.py`) for validating strategies against CSV/Parquet data.
- **CCXT Integration**: Support for 100+ exchanges with Sandbox (Paper) and Live trading modes.
- **Day Trading Support**: `KlineAggregator` for transforming tick data into 1m/5m bars for lower-noise strategies.
- **Mock Fallback**: Includes a `MockMarketDataIngestor` to bypass geofencing and SSL issues during development.

## 🏗️ Architecture

- **`main.py`**: The central orchestrator tying all components together.
- **`ingestor.py`**: Handles live (WebSocket) and historical (CSV) market data feeds.
- **`aggregator.py`**: [NEW] Aggregates raw ticks into OHLCV candles (Day Trading).
- **`strategy.py`**: The "brain" containing SMA Crossover, RSI, and Momentum logic (Tick & Kline support).
- **`risk.py`**: The mandatory gatekeeper for all trade validation.
- **`execution.py`**: Manages order placement via CCXT (Paper Trading enabled by default).
- **`models.py`**: Pydantic schemas for strict data validation.
- **`utils.py`**: Performance metrics like Sharpe Ratio and Max Drawdown.

## 🛠️ Setup & Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/hft.git
    cd hft
    ```

2.  **Install dependencies**:
    ```bash
    python3 -m pip install websockets pydantic certifi pandas numpy ccxt python-dotenv
    ```

3.  **Configure Environment**:
    Copy `.env.template` to `.env` and add your API keys.

## 🚦 How to Run

### Live/Paper Trading
By default, the bot runs in **Paper Trading** mode using **CCXT Sandbox**:
```bash
python3 main.py
```

### Backtesting
Run the backtester against historical data:
```bash
python3 backtester.py
```

## 🛡️ Risk Controls
The bot is configured with conservative defaults in `risk.py`:
- **Max Position**: $100,000
- **Daily Loss Limit**: $1,000
- **Max Drawdown**: 5.0%

## 🗺️ Roadmap & Remaining Work

### Phase 1: Infrastructure & Reliability (Current Priority)
- [ ] **Persistence Layer**: Integrate SQLite/DuckDB to store trade history and equity curves.
- [ ] **Monitoring**: Add Telegram/Slack bot for real-time trade alerts and risk warnings.
- [ ] **Logging**: Implement `RotatingFileHandler` for managed, persistent log files.

### Phase 2: Advanced Strategy Development
- [ ] **Pairs Trading**: Statistical Arbitrage module for correlated assets (BTC/ETH).
- [ ] **Order Book Analysis**: Order Book Imbalance (Level 2) metrics for micro-level direction.
- [ ] **Backtest Fidelity**: Add slippage (0.05%) and exchange fee modeling to the engine.

### Phase 3: Scaling & Optimization
- [ ] **Multi-Timeframe Consensus**: Logic to require agreement between Tick (HFT) and 1m (Intraday) signals.
- [ ] **Native Kline Streams**: Add direct subscription to Binance Kline WebSockets.

