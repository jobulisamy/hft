"""
Market Data Ingestor using WebSockets.
"""
import asyncio
import json
import logging
import ssl
from typing import Callable, Awaitable
import websockets
import certifi
from datetime import datetime
from models import TickerData


class MarketDataIngestor:
    """
    Handles real-time market data streaming from an exchange.
    Defaulting to Binance Spot WebSocket API.
    """

    def __init__(self, symbol: str, callback: Callable[[TickerData], Awaitable[None]]):
        """
        Initialize the ingestor.

        Args:
            symbol: Trading pair (e.g., 'btcusdt')
            callback: Async function to process received TickerData
        """
        self.symbol = symbol.lower()
        self.callback = callback
        self.url = f"wss://stream.binance.com:9443/ws/{self.symbol}@ticker"
        self.is_running = False
        self.logger = logging.getLogger(__name__)

        # SSL Context for macOS certificate issues
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    async def run(self):
        """
        Main loop to maintain WebSocket connection and process messages.
        """
        self.is_running = True
        while self.is_running:
            try:
                async with websockets.connect(self.url, ssl=self.ssl_context) as websocket:
                    self.logger.info(f"Connected to {self.url}")
                    while self.is_running:
                        message = await websocket.recv()
                        await self._handle_message(message)
            except (websockets.ConnectionClosed, Exception) as e:
                self.logger.error(f"WebSocket error: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def _handle_message(self, message: str):
        """
        Parse raw JSON and trigger callback with TickerData.
        """
        try:
            data = json.loads(message)
            # Binance ticker fields: 'c' = close price, 'v' = base volume, 'E' = Event time
            ticker = TickerData(
                symbol=data['s'],
                price=float(data['c']),
                volume=float(data['v']),
                timestamp=datetime.fromtimestamp(data['E'] / 1000.0),
                exchange="binance"
            )
            await self.callback(ticker)
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def stop(self):
        """Stop the ingestor."""
        self.is_running = False


class MockMarketDataIngestor:
    """
    Simulates real-time market data for testing and validation.
    Bypasses networking/geofencing issues.
    """

    def __init__(self, symbol: str, callback: Callable[[TickerData], Awaitable[None]]):
        self.symbol = symbol.upper()
        self.callback = callback
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    async def run(self):
        self.is_running = True
        price = 50000.0  # Starting price
        self.logger.info(f"Starting Mock Ingestor for {self.symbol}...")
        
        import random
        while self.is_running:
            try:
                # Simulate price movement
                price += random.uniform(-10.0, 10.0)
                ticker = TickerData(
                    symbol=self.symbol,
                    price=round(price, 2),
                    volume=random.uniform(0.1, 2.0),
                    timestamp=datetime.utcnow(),
                    exchange="mock"
                )
                await self.callback(ticker)
                await asyncio.sleep(0.5) # 2 Hz updates
            except Exception as e:
                self.logger.error(f"Mock error: {e}")
                await asyncio.sleep(1)

    def stop(self):
        self.is_running = False


    def stop(self):
        self.is_running = False


class HistoricalDataIngestor:
    """
    Simulates real-time market data from a historical file (CSV/Parquet).
    Used for backtesting strategies with the same pipeline.
    """

    def __init__(self, file_path: str, symbol: str, callback: Callable[[TickerData], Awaitable[None]]):
        self.file_path = file_path
        self.symbol = symbol.upper()
        self.callback = callback
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    async def run(self):
        """
        Reads data from file and emits ticker updates.
        """
        import pandas as pd
        self.is_running = True
        
        self.logger.info(f"Loading historical data from {self.file_path}...")
        try:
            if self.file_path.endswith('.csv'):
                df = pd.read_csv(self.file_path)
            elif self.file_path.endswith('.parquet'):
                df = pd.read_parquet(self.file_path)
            else:
                raise ValueError("Unsupported file format. Use .csv or .parquet")

            # Expecting columns: timestamp, price, volume
            # Convert timestamp to datetime if needed
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            for _, row in df.iterrows():
                if not self.is_running:
                    break
                
                ticker = TickerData(
                    symbol=self.symbol,
                    price=float(row['price']),
                    volume=float(row['volume']),
                    timestamp=row['timestamp'].to_pydatetime() if 'timestamp' in row else datetime.utcnow(),
                    exchange="historical"
                )
                await self.callback(ticker)

        except Exception as e:
            self.logger.error(f"Historical ingest error: {e}")
        finally:
            self.is_running = False

    def stop(self):
        self.is_running = False


if __name__ == "__main__":
    # Test stub
    logging.basicConfig(level=logging.INFO)

    async def mock_callback(data: TickerData):
        print(f"[{data.timestamp}] {data.symbol}: ${data.price} (Vol: {data.volume})")

    ingestor = MarketDataIngestor("btcusdt", mock_callback)
    try:
        asyncio.run(ingestor.run())
    except KeyboardInterrupt:
        ingestor.stop()
