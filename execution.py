"""
Execution handler for order placement and status tracking.
"""
import logging
import asyncio
import os
from typing import Optional
from models import OrderSignal, Position
import ccxt.async_support as ccxt
from dotenv import load_dotenv

load_dotenv()


class ExecutionHandler:
    """
    Handles communication with exchange for order execution using CCXT.
    """

    def __init__(self, symbol: str, is_paper_trading: bool = True):
        """
        Initialize the execution handler.
        """
        self.symbol = symbol
        self.is_paper_trading = is_paper_trading
        self.logger = logging.getLogger(__name__)

        # Initialize CCXT exchange object
        # Using Binance as default, can be parameterized later
        self.exchange = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET_KEY'),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })

        if self.is_paper_trading:
            self.exchange.set_sandbox_mode(True)
            self.logger.info("ExecutionHandler: Running in Sandbox (Paper Trading) mode.")

    async def execute_order(self, signal: OrderSignal) -> Optional[Position]:
        """
        Submits an order based on the signal using CCXT.
        """
        self.logger.info(f"Executing {signal.signal} order for {signal.symbol} at ${signal.price}...")

        try:
            # Simple Market Order for MVP
            # In a real setup, you might use Limit orders or check balance first
            side = 'buy' if signal.signal.value == 'BUY' else 'sell'
            
            if self.is_paper_trading and not self.exchange.apiKey:
                # Fallback for mock/local verification if no keys provided
                await asyncio.sleep(0.05)
                self.logger.info(f"Mock Paper Trade success: {signal.symbol} @ ${signal.price}")
                return Position(symbol=signal.symbol, quantity=1.0, entry_price=signal.price)

            order = await self.exchange.create_order(
                symbol=signal.symbol,
                type='market',
                side=side,
                amount=1.0  # Fixed qty for MVP
            )

            self.logger.info(f"Order successful! ID: {order['id']}")
            return Position(
                symbol=signal.symbol,
                quantity=float(order['amount']),
                entry_price=float(order['price']) if order['price'] else signal.price
            )

        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return None

    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()
