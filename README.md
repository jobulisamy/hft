# HFT Trading Bot (Solo Developer Edition)

An asynchronous High-Frequency Trading (HFT) bot built in Python. Designed for speed, reliability, and modularity, this project is tailored for a single developer focusing on short-term intraday strategies (Mean Reversion, RSI, and Momentum).

## 🚀 Key Features

- **Asynchronous Architecture**: Powered by `asyncio` for non-blocking market data ingestion and order execution.
- **WebSocket-First**: Real-time ticker streaming via Binance Spot WebSockets with automatic reconnection.
- **Multi-Strategy Ensemble**: Combines multiple "expert" strategies (SMA, RSI, Momentum) to reduce false signals.
- **Robust Risk Management**: Built-in safety guards for max position sizing, daily loss limits, and global drawdown.
- **Backtest Engine**: Integrated historical simulation tool (`backtester.py`) for validating strategies against CSV/Parquet data.
- **Mock Fallback**: Includes a `MockMarketDataIngestor` to bypass geofencing and SSL issues during development.

## 🏗️ Architecture

- **`main.py`**: The central orchestrator tying all components together.
- **`ingestor.py`**: Handles live (WebSocket) and historical (CSV) market data feeds.
- **`strategy.py`**: The "brain" containing SMA Crossover, RSI, and Momentum logic.
- **`risk.py`**: The mandatory gatekeeper for all trade validation.
- **`execution.py`**: Manages order placement (Paper Trading enabled by default).
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
    python3 -m pip install websockets pydantic certifi pandas numpy
    ```

## 🚦 How to Run

### Live/Paper Trading
By default, the bot runs in **Paper Trading** mode with **Mock Data** enabled to ensure it works in any environment:
```bash
python3 main.py
```
To use real Binance data, modify `main.py`:
```python
bot = HFTBot("btcusdt", use_mock=False)
```

### Backtesting
Run the backtester against historical data:
```bash
python3 backtester.py
```
*(Requires a `test_data.csv` or similar file in the project root)*

## 🛡️ Risk Controls
The bot is configured with conservative defaults in `risk.py`:
- **Max Position**: $100,000 (Adjustable)
- **Daily Loss Limit**: $1,000
- **Max Drawdown**: 5.0%

## 📝 Next Steps
- [ ] Implement CCXT for real exchange execution.
- [ ] Add Pairs Trading (Stat Arb) module.
- [ ] Integrate Level 2 (Order Book) imbalance metrics.

