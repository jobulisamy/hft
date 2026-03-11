"""
Aggregator to transform raw TickerData into KlineData (candles).
Supports custom window lengths.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Awaitable
from models import TickerData, KlineData


class KlineAggregator:
    """
    Groups TickerData into candles of a specified duration.
    """

    def __init__(
        self, 
        symbol: str, 
        interval_seconds: int, 
        callback: Callable[[KlineData], Awaitable[None]]
    ):
        self.symbol = symbol
        self.interval_seconds = interval_seconds
        self.callback = callback
        self.logger = logging.getLogger(self.__class__.__name__)

        self.current_kline: Optional[KlineData] = None

    async def add_ticker(self, ticker: TickerData):
        """
        Process a new ticker and update or close the current candle.
        """
        timestamp = ticker.timestamp
        
        # If no kline exists, start the first one
        if not self.current_kline:
            self._start_new_kline(ticker)
            return

        # Check if the ticker belongs to the current kline
        if timestamp < self.current_kline.end_time:
            self._update_kline(ticker)
        else:
            # Close the current kline and emit it
            await self.callback(self.current_kline)
            
            # Start a new kline
            # If there's a gap, we align to the interval
            self._start_new_kline(ticker)

    def _start_new_kline(self, ticker: TickerData):
        # Align start time to the interval (e.g., start of the minute)
        start_ts = ticker.timestamp.replace(microsecond=0)
        seconds_since_epoch = int(start_ts.timestamp())
        aligned_start = seconds_since_epoch - (seconds_since_epoch % self.interval_seconds)
        start_time = datetime.fromtimestamp(aligned_start)
        end_time = start_time + timedelta(seconds=self.interval_seconds)

        self.current_kline = KlineData(
            symbol=self.symbol,
            open_price=ticker.price,
            high_price=ticker.price,
            low_price=ticker.price,
            close_price=ticker.price,
            volume=ticker.volume,
            start_time=start_time,
            end_time=end_time
        )

    def _update_kline(self, ticker: TickerData):
        if self.current_kline:
            self.current_kline.high_price = max(self.current_kline.high_price, ticker.price)
            self.current_kline.low_price = min(self.current_kline.low_price, ticker.price)
            self.current_kline.close_price = ticker.price
            self.current_kline.volume += ticker.volume
