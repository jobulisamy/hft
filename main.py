"""
Orchestrator for the HFT trading bot.
Ties together ingestor, strategy, risk, and execution.
"""
import asyncio
import logging
import signal
from ingestor import MarketDataIngestor, MockMarketDataIngestor
from strategy import MovingAverageStrategy, RSIStrategy, EnsembleStrategy
from risk import RiskManager
from execution import ExecutionHandler
from models import TickerData


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
        # 1. Strategy Signal Generation
        signal = self.strategy.on_ticker(ticker)
        if not signal:
            return

        # 2. Risk Validation
        if self.risk.validate_signal(signal):
            # 3. Execution
            position = await self.execution.execute_order(signal)
            if position:
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
