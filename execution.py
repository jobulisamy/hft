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
        self.capital_usd = 10000.0
        self.risk_per_trade = 0.05
        self.open_positions: dict = {}  # symbol -> Position
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
        Opens a new position if none exists; closes the existing position on a reversal signal.
        Returns the Position with realized_pnl set on close, or None if no action taken.
        """
        self.logger.info(f"Executing {signal.signal} order for {signal.symbol} at ${signal.price}...")

        try:
            sig = signal.signal.value
            sym = signal.symbol

            if sig not in ('BUY', 'SELL'):
                self.logger.debug(f"Ignoring non-actionable signal: {sig}")
                return None

            existing = self.open_positions.get(sym)

            # Close existing position on reversal
            if existing:
                is_reversal = (existing.side == "long" and sig == 'SELL') or \
                              (existing.side == "short" and sig == 'BUY')
                if is_reversal:
                    if existing.side == "long":
                        pnl = (signal.price - existing.entry_price) * existing.quantity
                    else:
                        pnl = (existing.entry_price - signal.price) * existing.quantity

                    closed = existing.model_copy(update={"realized_pnl": pnl})
                    del self.open_positions[sym]
                    self.logger.info(f"Closed {existing.side} {sym} @ ${signal.price} | PnL: ${pnl:.2f}")
                    return closed
                else:
                    self.logger.debug(f"Already holding {existing.side} on {sym}, skipping same-direction signal.")
                    return None

            # Open new position
            side = 'buy' if sig == 'BUY' else 'sell'
            position_side = 'long' if sig == 'BUY' else 'short'
            order_value = self.capital_usd * self.risk_per_trade
            amount = round(order_value / signal.price, 6)

            if self.is_paper_trading and not self.exchange.apiKey:
                await asyncio.sleep(0.05)
                position = Position(symbol=sym, quantity=amount, entry_price=signal.price, side=position_side)
                self.open_positions[sym] = position
                self.logger.info(f"Opened {position_side} {sym} @ ${signal.price} qty={amount}")
                return position

            order = await self.exchange.create_order(
                symbol=sym,
                type='market',
                side=side,
                amount=amount
            )
            fill_price = float(order['price']) if order['price'] else signal.price
            position = Position(symbol=sym, quantity=float(order['amount']), entry_price=fill_price, side=position_side)
            self.open_positions[sym] = position
            self.logger.info(f"Order successful! ID: {order['id']}")
            return position

        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return None

    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()
