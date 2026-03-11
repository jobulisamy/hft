"""
Backtest Engine for evaluating HFT strategies on historical data.
"""
import asyncio
import logging
from typing import Dict, Optional
from ingestor import HistoricalDataIngestor
from strategy import EnsembleStrategy, MovingAverageStrategy, RSIStrategy
from risk import RiskManager
from execution import ExecutionHandler
from models import TickerData, Position
from utils import calculate_max_drawdown


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

        self.open_positions: Dict[str, Dict] = {}
        self.equity_curve = [self.risk.total_equity_usd]

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

        sym = ticker.symbol
        sig = signal.signal.value

        if sig == 'BUY':
            if sym not in self.open_positions:
                # Open long
                qty = 1.0
                self.open_positions[sym] = {"side": "long", "entry_price": ticker.price, "qty": qty}
                self.logger.info(f"Backtest OPEN LONG {sym} @ ${ticker.price}")
            elif self.open_positions[sym]["side"] == "short":
                # Close short
                pos = self.open_positions.pop(sym)
                pnl = (pos["entry_price"] - ticker.price) * pos["qty"]
                self._record_trade(pnl, sym, ticker.price)

        elif sig == 'SELL':
            if sym not in self.open_positions:
                # Open short
                qty = 1.0
                self.open_positions[sym] = {"side": "short", "entry_price": ticker.price, "qty": qty}
                self.logger.info(f"Backtest OPEN SHORT {sym} @ ${ticker.price}")
            elif self.open_positions[sym]["side"] == "long":
                # Close long
                pos = self.open_positions.pop(sym)
                pnl = (ticker.price - pos["entry_price"]) * pos["qty"]
                self._record_trade(pnl, sym, ticker.price)

    def _record_trade(self, pnl: float, symbol: str, price: float):
        self.metrics["total_trades"] += 1
        self.metrics["total_pnl"] += pnl
        if pnl > 0:
            self.metrics["winning_trades"] += 1
        self.risk.update_pnl(pnl)
        self.equity_curve.append(self.risk.total_equity_usd)
        self.logger.info(f"Backtest CLOSE {symbol} @ ${price} | PnL: ${pnl:.2f}")

    async def run_backtest(self):
        """Run the full backtest simulation."""
        self.logger.info(f"Starting Backtest for {self.symbol}...")
        await self.ingestor.run()

        self.metrics["max_drawdown"] = calculate_max_drawdown(self.equity_curve)
        win_rate = (
            self.metrics["winning_trades"] / self.metrics["total_trades"]
            if self.metrics["total_trades"] > 0 else 0.0
        )
        self.logger.info(
            f"Backtest complete. Trades: {self.metrics['total_trades']} | "
            f"PnL: ${self.metrics['total_pnl']:.2f} | "
            f"Win Rate: {win_rate:.1%} | "
            f"Max Drawdown: {self.metrics['max_drawdown']:.2%}"
        )


async def main():
    logging.basicConfig(level=logging.INFO)
    # Run with dummy data
    tester = Backtester("BTCUSDT", "test_data.csv")
    await tester.run_backtest()


if __name__ == "__main__":
    asyncio.run(main())
