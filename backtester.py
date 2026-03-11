"""
Backtest Engine for evaluating HFT strategies on historical data.
"""
import asyncio
import logging
from typing import List, Dict
from ingestor import HistoricalDataIngestor
from strategy import EnsembleStrategy, MovingAverageStrategy, RSIStrategy
from risk import RiskManager
from execution import ExecutionHandler
from models import TickerData, Position


class Backtester:
    """
    Orchestrates historical data playback and strategy evaluation.
    """

    def __init__(self, symbol: str, data_file: str):
        self.symbol = symbol
        self.logger = logging.getLogger("Backtester")
        
        # Initialize components for backtesting
        # We use a lower threshold for SMA in backtests to see more activity
        sma_strat = MovingAverageStrategy(threshold=0.0001)
        rsi_strat = RSIStrategy()
        self.strategy = EnsembleStrategy([sma_strat, rsi_strat])
        
        self.risk = RiskManager(daily_loss_limit_usd=10000.0) # Looser limits for backtesting
        self.execution = ExecutionHandler(is_paper_trading=True)
        self.ingestor = HistoricalDataIngestor(data_file, symbol, self.handle_ticker)
        
        self.metrics = {
            "total_trades": 0,
            "total_pnl": 0.0,
            "winning_trades": 0,
            "max_drawdown": 0.0
        }

    async def handle_ticker(self, ticker: TickerData):
        """
        Backtest pipeline for each historical ticker update.
        """
        signal = self.strategy.on_ticker(ticker)
        if not signal:
            return

        if self.risk.validate_signal(signal):
            position = await self.execution.execute_order(signal)
            if position:
                self.risk.update_position(position)
                self.metrics["total_trades"] += 1
                # Simple PnL simulation (mocked for now in this MVP)
                # In a real backtester, we'd track entry/exit matched pairs
                self.logger.info(f"Backtest Trade: {signal.signal} {signal.symbol} @ ${signal.price}")

    async def run_backtest(self):
        """Run the full backtest simulation."""
        self.logger.info(f"Starting Backtest for {self.symbol}...")
        await self.ingestor.run()
        self.logger.info(f"Backtest complete. Results: {self.metrics}")


async def main():
    logging.basicConfig(level=logging.INFO)
    # Run with dummy data
    tester = Backtester("BTCUSDT", "test_data.csv")
    await tester.run_backtest()


if __name__ == "__main__":
    asyncio.run(main())
