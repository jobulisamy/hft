"""
Orchestrator for the HFT trading bot.
Ties together ingestor, strategy, risk, and execution.
"""
import asyncio
import logging
import signal
from ingestor import MarketDataIngestor, MockMarketDataIngestor
from strategy import MovingAverageStrategy, RSIStrategy, EnsembleStrategy
from aggregator import KlineAggregator
from risk import RiskManager
from execution import ExecutionHandler
from models import TickerData, KlineData


class HFTBot:
    """
    Main HFT Bot orchestrator.
    """

    def __init__(self, symbol: str, use_mock: bool = True):
        self.symbol = symbol
        self.logger = logging.getLogger("HFTBot")

        # Initialize Ensemble of Strategies
        sma_strat = MovingAverageStrategy()
        rsi_strat = RSIStrategy()
        self.strategy = EnsembleStrategy([sma_strat, rsi_strat])

        # Kline Aggregator for Day Trading (1-minute bars)
        self.aggregator = KlineAggregator(symbol, interval_seconds=60, callback=self.handle_kline)

        self.risk = RiskManager()
        self.execution = ExecutionHandler(symbol=self.symbol, is_paper_trading=True)
        
        if use_mock:
            self.ingestor = MockMarketDataIngestor(symbol, self.handle_ticker)
        else:
            self.ingestor = MarketDataIngestor(symbol, self.handle_ticker)

        self.is_running = False

    async def handle_ticker(self, ticker: TickerData):
        """
        Pipeline for processing each ticker update.
        """
        # Feed ticker to aggregator for day trading logic
        await self.aggregator.add_ticker(ticker)

        # 1. Strategy Signal Generation (HFT/Tick level)
        signal = self.strategy.on_ticker(ticker)
        if signal:
            await self._process_signal(signal)

    async def handle_kline(self, kline: KlineData):
        """
        Pipeline for processing aggregated candles (Day Trading level).
        """
        self.logger.info(f"New Kline: {kline.start_time} Close: ${kline.close_price} Vol: {kline.volume}")
        
        # Strategy Signal Generation (Intraday/Bar level)
        signal = self.strategy.on_kline(kline)
        if signal:
            self.logger.info(f"Strategy generated signal from Kline: {signal}")
            await self._process_signal(signal)

    async def _process_signal(self, signal):
        """
        Common logic for signal validation and execution.
        """
        # 2. Risk Validation
        if self.risk.validate_signal(signal):
            # 3. Execution
            position = await self.execution.execute_order(signal)
            if position:
                if position.realized_pnl is not None:
                    # Position was closed — update realized PnL
                    self.risk.update_pnl(position.realized_pnl)
                    self.logger.info(f"Closed position PnL: ${position.realized_pnl:.2f}")
                else:
                    # Position was opened — register it
                    self.risk.update_position(position)
                self.logger.info(f"Updated position: {position}")

    async def start(self):
        """Start the bot components."""
        self.logger.info(f"Starting HFT Bot for {self.symbol}...")
        self.is_running = True
        await self.ingestor.run()

    def stop(self):
        """Stop the bot."""
        self.logger.info("Stopping HFT Bot...")
        self.is_running = False
        self.ingestor.stop()


async def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    bot = HFTBot("btcusdt")

    # Handle termination signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, bot.stop)

    try:
        await bot.start()
    except asyncio.CancelledError:
        pass
    finally:
        bot.stop()
        await bot.execution.close()


if __name__ == "__main__":
    asyncio.run(main())
