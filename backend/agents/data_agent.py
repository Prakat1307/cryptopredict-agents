"""
Data Agent - Fetches crypto OHLCV data using Apify and direct exchange APIs.
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import httpx
import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent
from utils.helpers import timestamp_now, resample_ohlcv


class DataAgent(BaseAgent):
    """
    Agent responsible for fetching historical and real-time crypto data.
    Uses Apify for scraping and direct exchange APIs as fallback.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("data", config)
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.apify_token = os.getenv("APIFY_API_TOKEN", "")
        
        # Register tools
        self.register_tool("fetch_binance", self._fetch_binance)
        self.register_tool("fetch_apify", self._fetch_apify)
        self.register_tool("fetch_multi_timeframe", self._fetch_multi_timeframe)
        self.register_tool("get_latest_price", self._get_latest_price)
    
    async def initialize(self):
        await super().initialize()
        self.logger.logger.info("DataAgent initialized with Apify + Binance tools")
    
    async def run(self, asset: str = "BTC", bars: int = 1000, interval: str = "5m", **kwargs) -> Dict[str, Any]:
        """
        Fetch data for an asset.
        
        Args:
            asset: Asset symbol
            bars: Number of bars to fetch
            interval: Candle interval
        
        Returns:
            Dict with OHLCV data and metadata
        """
        self.status = "running"
        self.last_run = timestamp_now()
        
        self.logger.log_decision(
            f"Fetching {bars} bars of {interval} data for {asset}",
            {"asset": asset, "bars": bars, "interval": interval}
        )
        
        # APIFY_ENABLED=false skips Apify and goes straight to Binance.
        # Set to true only when Apify trial/subscription is active.
        apify_enabled = os.getenv("APIFY_ENABLED", "false").lower() == "true"

        try:
            # Try Apify first (only if enabled), fallback to Binance
            data = None
            source = None

            if self.apify_token and apify_enabled:
                try:
                    data = await self.execute_tool("fetch_apify", asset=asset, bars=bars, interval=interval)
                    source = "apify"
                except Exception as e:
                    self.logger.logger.warning(f"Apify fetch failed: {e}, falling back to Binance")

            if data is None:
                data = await self.execute_tool("fetch_binance", asset=asset, bars=bars, interval=interval)
                source = "binance"
            
            result = {
                "asset": asset,
                "interval": interval,
                "bars": len(data) if hasattr(data, '__len__') else 0,
                "source": source,
                "timestamp": timestamp_now(),
                "data": data
            }
            
            self.add_to_memory({
                "action": "fetch_data",
                "asset": asset,
                "bars": bars,
                "source": source
            })
            
            self.status = "idle"
            return result
            
        except Exception as e:
            self.status = "error"
            self.logger.log_error(e, {"asset": asset, "bars": bars})
            raise
    
    async def fetch_data(self, asset: str, bars: int = 1000, interval: str = "5m") -> pd.DataFrame:
        """Convenience method to fetch data as DataFrame."""
        result = await self.run(asset=asset, bars=bars, interval=interval)
        return result.get("data", pd.DataFrame())
    
    async def _fetch_binance(self, asset: str, bars: int, interval: str) -> pd.DataFrame:
        """Fetch OHLCV data from Binance API."""
        symbol = f"{asset}USDT"
        
        # Map interval to Binance format
        interval_map = {
            "1m": "1m", "5m": "5m", "15m": "15m",
            "30m": "30m", "1h": "1h", "4h": "4h", "1d": "1d"
        }
        binance_interval = interval_map.get(interval, "5m")
        
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": binance_interval,
            "limit": min(bars, 1000)
        }
        
        response = await self.http_client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        
        # Convert types
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        
        self.logger.log_action("binance_fetch", {"symbol": symbol, "rows": len(df)})
        return df
    
    async def _fetch_apify(self, asset: str, bars: int, interval: str) -> pd.DataFrame:
        """Fetch crypto data using Apify actors."""
        from apify_client import ApifyClient
        
        client = ApifyClient(self.apify_token)
        
        # Use crypto prices scraper
        actor_id = "datastorm/cryptoprices-api"
        
        run_input = {
            "symbols": [asset],
            "days": str(max(1, bars // 288))  # Approximate days for 5min bars
        }
        
        run = client.actor(actor_id).call(run_input=run_input)
        dataset_id = run["defaultDatasetId"]
        
        items = list(client.dataset(dataset_id).iterate_items())
        
        if not items:
            raise ValueError("No data returned from Apify")
        
        # Convert to DataFrame
        df = pd.DataFrame(items)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
        
        self.logger.log_action("apify_fetch", {"asset": asset, "rows": len(df)})
        return df
    
    async def _fetch_multi_timeframe(self, asset: str, timeframes: List[str], bars: int = 1000) -> Dict[str, pd.DataFrame]:
        """Fetch data for multiple timeframes."""
        tasks = [self._fetch_binance(asset, bars, tf) for tf in timeframes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for tf, result in zip(timeframes, results):
            if isinstance(result, Exception):
                self.logger.logger.warning(f"Failed to fetch {tf}: {result}")
            else:
                data[tf] = result
        
        return data
    
    async def _get_latest_price(self, asset: str) -> Dict[str, Any]:
        """Get latest price for an asset."""
        symbol = f"{asset}USDT"
        url = "https://api.binance.com/api/v3/ticker/24hr"
        params = {"symbol": symbol}
        
        response = await self.http_client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        return {
            "symbol": asset,
            "price": float(data["lastPrice"]),
            "change_24h": float(data["priceChangePercent"]),
            "volume_24h": float(data["volume"]),
            "high_24h": float(data["highPrice"]),
            "low_24h": float(data["lowPrice"])
        }
    
    async def shutdown(self):
        await self.http_client.aclose()
        await super().shutdown()
