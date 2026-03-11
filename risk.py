"""
Risk management module for global drawdown and position control.
"""
import logging
from typing import Dict
from models import OrderSignal, Position


class RiskManager:
    """
    Enforces risk constraints before any order is placed.
    """

    def __init__(
        self,
        max_position_size_usd: float = 100000.0,
        max_drawdown_percent: float = 0.05,
        daily_loss_limit_usd: float = 1000.0
    ):
        """
        Initialize risk parameters.
        """
        self.max_position_size_usd = max_position_size_usd
        self.max_drawdown_percent = max_drawdown_percent
        self.daily_loss_limit_usd = daily_loss_limit_usd

        self.current_positions: Dict[str, Position] = {}
        self.total_equity_usd = 10000.0  # Initial hypothetical equity
        self.initial_equity_usd = 10000.0
        self.daily_pnl_usd = 0.0

        self.logger = logging.getLogger(__name__)

    def validate_signal(self, signal: OrderSignal) -> bool:
        """
        Validates a signal against current risk constraints.

        Args:
            signal: The proposed OrderSignal

        Returns:
            True if signal is safe to execute, False otherwise.
        """
        # 1. Check Daily Loss Limit
        if self.daily_pnl_usd <= -self.daily_loss_limit_usd:
            self.logger.warning("Risk: Daily loss limit reached. Signal rejected.")
            return False

        # 2. Check Global Drawdown
        current_drawdown = (self.initial_equity_usd - self.total_equity_usd) / self.initial_equity_usd
        if current_drawdown >= self.max_drawdown_percent:
            self.logger.warning(f"Risk: Max drawdown reached ({current_drawdown:.2%}). Signal rejected.")
            return False

        # 3. Check Position Size
        # Rough estimate: signal.price * quantity (simplifying for validation)
        # Assuming fixed trade sizes for now in this MVP
        if signal.price > self.max_position_size_usd:
             self.logger.warning(f"Risk: Signal price ${signal.price} exceeds max position size limit.")
             return False

        self.logger.info(f"Risk: Signal for {signal.symbol} validated successfully.")
        return True

    def update_position(self, position: Position):
        """Update internal position state after execution."""
        self.current_positions[position.symbol] = position

    def update_pnl(self, pnl: float):
        """Update realized PnL to track daily limits."""
        self.daily_pnl_usd += pnl
        self.total_equity_usd += pnl
