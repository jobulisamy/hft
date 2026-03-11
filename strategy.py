"""
Strategy engine supporting multiple concurrent strategies and signal ensemble.
"""
import logging
from typing import Deque, Optional, List
from collections import deque
from abc import ABC, abstractmethod
from models import TickerData, KlineData, OrderSignal, SignalType


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    """
    @abstractmethod
    def on_ticker(self, ticker: TickerData) -> Optional[OrderSignal]:
        pass

    def on_kline(self, kline: KlineData) -> Optional[OrderSignal]:
        """
        Optional: Handle candle-based data.
        """
        return None


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
            signal_type = SignalType.BUY
        elif price_diff < -self.threshold:
            signal_type = SignalType.SELL

        if signal_type != SignalType.HOLD:
            return OrderSignal(
                symbol=ticker.symbol,
                signal=signal_type,
                price=ticker.price,
                confidence=min(abs(price_diff) * 10, 1.0),
                metadata={"sma": sma, "price_diff": price_diff}
            )
        return None

    def on_kline(self, kline: KlineData) -> Optional[OrderSignal]:
        """
        SMA crossover using candle close prices.
        """
        self.prices.append(kline.close_price)

        if len(self.prices) < self.window_size:
            return None

        sma = sum(self.prices) / len(self.prices)
        price_diff = (kline.close_price - sma) / sma

        signal_type = SignalType.HOLD
        if price_diff > self.threshold:
            signal_type = SignalType.BUY
        elif price_diff < -self.threshold:
            signal_type = SignalType.SELL

        if signal_type != SignalType.HOLD:
            return OrderSignal(
                symbol=kline.symbol,
                signal=signal_type,
                price=kline.close_price,
                confidence=min(abs(price_diff) * 10, 1.0),
                metadata={"sma": sma, "price_diff": price_diff, "source": "kline"}
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
        self.prev_avg_gain: Optional[float] = None
        self.prev_avg_loss: Optional[float] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def _compute_rsi(self, current_price: float, prev_price: float) -> Optional[float]:
        diff = current_price - prev_price
        gain = diff if diff > 0 else 0.0
        loss = abs(diff) if diff < 0 else 0.0

        if self.prev_avg_gain is None:
            # Seed: need a full window of prior diffs — not ready yet
            return None

        avg_gain = (self.prev_avg_gain * (self.window_size - 1) + gain) / self.window_size
        avg_loss = (self.prev_avg_loss * (self.window_size - 1) + loss) / self.window_size
        self.prev_avg_gain = avg_gain
        self.prev_avg_loss = avg_loss

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _seed_rsi(self):
        """Seed prev_avg_gain/loss from the initial window using simple average."""
        gains, losses = [], []
        prices = list(self.prices)
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            gains.append(diff if diff > 0 else 0.0)
            losses.append(abs(diff) if diff < 0 else 0.0)
        self.prev_avg_gain = sum(gains) / self.window_size
        self.prev_avg_loss = sum(losses) / self.window_size

    def on_ticker(self, ticker: TickerData) -> Optional[OrderSignal]:
        self.prices.append(ticker.price)
        if len(self.prices) <= self.window_size:
            return None

        prices = list(self.prices)
        if self.prev_avg_gain is None:
            self._seed_rsi()
            return None

        rsi = self._compute_rsi(prices[-1], prices[-2])
        if rsi is None:
            return None

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
                confidence=0.5,
                metadata={"rsi": rsi}
            )
        return None

    def on_kline(self, kline: KlineData) -> Optional[OrderSignal]:
        """
        RSI calculation using candle close prices.
        """
        self.prices.append(kline.close_price)
        if len(self.prices) <= self.window_size:
            return None

        prices = list(self.prices)
        if self.prev_avg_gain is None:
            self._seed_rsi()
            return None

        rsi = self._compute_rsi(prices[-1], prices[-2])
        if rsi is None:
            return None

        signal_type = SignalType.HOLD
        if rsi < self.oversold:
            signal_type = SignalType.BUY
        elif rsi > self.overbought:
            signal_type = SignalType.SELL

        if signal_type != SignalType.HOLD:
            return OrderSignal(
                symbol=kline.symbol,
                signal=signal_type,
                price=kline.close_price,
                confidence=0.5,
                metadata={"rsi": rsi, "source": "kline"}
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

    def on_kline(self, kline: KlineData) -> Optional[OrderSignal]:
        signals = []
        for strat in self.strategies:
            sig = strat.on_kline(kline)
            if sig:
                signals.append(sig)

        if not signals:
            return None

        # Same consensus logic as on_ticker
        first_sig = signals[0].signal
        if all(s.signal == first_sig for s in signals):
            meta = {}
            for s in signals:
                if s.metadata:
                    meta.update(s.metadata)
            
            return OrderSignal(
                symbol=kline.symbol,
                signal=first_sig,
                price=kline.close_price,
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
