"""
Strategy engine supporting multiple concurrent strategies and signal ensemble.
"""
import logging
from typing import Deque, Optional, List
from collections import deque
from abc import ABC, abstractmethod
from models import TickerData, OrderSignal, SignalType


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    """
    @abstractmethod
    def on_ticker(self, ticker: TickerData) -> Optional[OrderSignal]:
        pass


class MovingAverageStrategy(BaseStrategy):
    """
    A simple Moving Average Crossover strategy (Price vs. SMA).
    """

    def __init__(self, window_size: int = 20, threshold: float = 0.0001):
        self.window_size = window_size
        self.threshold = threshold
        self.prices: Deque[float] = deque(maxlen=window_size)
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_ticker(self, ticker: TickerData) -> Optional[OrderSignal]:
        self.prices.append(ticker.price)

        if len(self.prices) < self.window_size:
            return None

        sma = sum(self.prices) / len(self.prices)
        price_diff = (ticker.price - sma) / sma

        signal_type = SignalType.HOLD
        if price_diff > self.threshold:
            signal_type = SignalType.SELL
        elif price_diff < -self.threshold:
            signal_type = SignalType.BUY

        if signal_type != SignalType.HOLD:
            return OrderSignal(
                symbol=ticker.symbol,
                signal=signal_type,
                price=ticker.price,
                confidence=min(abs(price_diff) * 10, 1.0),
                metadata={"sma": sma, "price_diff": price_diff}
            )
        return None


class RSIStrategy(BaseStrategy):
    """
    Relative Strength Index (RSI) strategy.
    RSI < 30: Oversold (BUY)
    RSI > 70: Overbought (SELL)
    """

    def __init__(self, window_size: int = 14, overbought: float = 70.0, oversold: float = 30.0):
        self.window_size = window_size
        self.overbought = overbought
        self.oversold = oversold
        self.prices: Deque[float] = deque(maxlen=window_size + 1)
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_ticker(self, ticker: TickerData) -> Optional[OrderSignal]:
        self.prices.append(ticker.price)
        if len(self.prices) <= self.window_size:
            return None

        gains = []
        losses = []
        for i in range(1, len(self.prices)):
            diff = self.prices[i] - self.prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))

        avg_gain = sum(gains) / self.window_size
        avg_loss = sum(losses) / self.window_size

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        signal_type = SignalType.HOLD
        if rsi < self.oversold:
            signal_type = SignalType.BUY
        elif rsi > self.overbought:
            signal_type = SignalType.SELL

        if signal_type != SignalType.HOLD:
            return OrderSignal(
                symbol=ticker.symbol,
                signal=signal_type,
                price=ticker.price,
                confidence=0.5,  # Fixed confidence for RSI in this MVP
                metadata={"rsi": rsi}
            )
        return None


class EnsembleStrategy(BaseStrategy):
    """
    Combines multiple strategies. Only emits a signal if they agree.
    """

    def __init__(self, strategies: List[BaseStrategy]):
        self.strategies = strategies
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_ticker(self, ticker: TickerData) -> Optional[OrderSignal]:
        signals = []
        for strat in self.strategies:
            sig = strat.on_ticker(ticker)
            if sig:
                signals.append(sig)

        if not signals:
            return None

        # Simple Logic: Only signal if ALL strategies that emitted a signal agree
        # and we have at least 2 strategies contributing (for higher conviction)
        if len(signals) < len(self.strategies):
            return None

        first_sig = signals[0].signal
        if all(s.signal == first_sig for s in signals):
            # Combined metadata
            meta = {}
            for s in signals:
                if s.metadata:
                    meta.update(s.metadata)
            
            return OrderSignal(
                symbol=ticker.symbol,
                signal=first_sig,
                price=ticker.price,
                confidence=sum(s.confidence for s in signals) / len(signals),
                metadata=meta
            )
        
        return None


class MomentumStrategy(BaseStrategy):
    """
    Intraday Momentum / Breakout Strategy.
    Enters a trade if the price is moving strongly in one direction
    with high relative volume.
    """

    def __init__(self, window_size: int = 20, volume_window: int = 50, threshold: float = 0.002):
        self.window_size = window_size
        self.volume_window = volume_window
        self.threshold = threshold
        
        self.prices: Deque[float] = deque(maxlen=window_size)
        self.volumes: Deque[float] = deque(maxlen=volume_window)
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_ticker(self, ticker: TickerData) -> Optional[OrderSignal]:
        self.prices.append(ticker.price)
        self.volumes.append(ticker.volume)

        if len(self.prices) < self.window_size or len(self.volumes) < self.volume_window:
            return None

        # 1. Price Momentum: Percent change over window
        momentum = (ticker.price - self.prices[0]) / self.prices[0]
        
        # 2. Volume Filter: Is current volume above average?
        avg_volume = sum(self.volumes) / len(self.volumes)
        vol_ratio = ticker.volume / avg_volume if avg_volume > 0 else 1.0

        signal_type = SignalType.HOLD
        if momentum > self.threshold and vol_ratio > 1.2:
            signal_type = SignalType.BUY  # Strong upward momentum
        elif momentum < -self.threshold and vol_ratio > 1.2:
            signal_type = SignalType.SELL # Strong downward momentum

        if signal_type != SignalType.HOLD:
            return OrderSignal(
                symbol=ticker.symbol,
                signal=signal_type,
                price=ticker.price,
                confidence=min(abs(momentum) * 50, 1.0),
                metadata={"momentum": momentum, "vol_ratio": vol_ratio}
            )

        return None
