"""
Hermes Agent Tool - Kalshi Integration
Provides market data access for Kalshi prediction markets.
"""

import json
from typing import Dict, Any, Optional
import httpx


class KalshiTool:
    """Tool for accessing Kalshi prediction market data."""
    
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_markets(self, series: str = "KXBTC", limit: int = 10) -> str:
        """Search for markets on Kalshi."""
        try:
            url = f"{self.base_url}/markets"
            params = {
                "series_ticker": series,
                "status": "open",
                "limit": limit
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            markets = data.get("markets", [])
            
            formatted = []
            for m in markets:
                formatted.append({
                    "ticker": m.get("ticker"),
                    "title": m.get("title"),
                    "yes_bid": m.get("yes_bid"),
                    "yes_ask": m.get("yes_ask"),
                    "no_bid": m.get("no_bid"),
                    "no_ask": m.get("no_ask"),
                    "volume": m.get("volume"),
                    "open_interest": m.get("open_interest"),
                    "expiration": m.get("expiration_date")
                })
            
            return json.dumps({
                "success": True,
                "markets": formatted,
                "count": len(formatted)
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    async def get_orderbook(self, ticker: str, depth: int = 10) -> str:
        """Get order book for a market."""
        try:
            url = f"{self.base_url}/markets/{ticker}/orderbook"
            params = {"depth": depth}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return json.dumps({
                "success": True,
                "ticker": ticker,
                "orderbook": data.get("orderbook", {})
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    async def close(self):
        await self.client.aclose()


KALSHI_TOOL_SCHEMA = {
    "name": "kalshi_search",
    "description": "Search for crypto prediction markets on Kalshi",
    "parameters": {
        "type": "object",
        "properties": {
            "series": {
                "type": "string",
                "description": "Series ticker (e.g., KXBTC, KXETH)"
            },
            "limit": {
                "type": "integer",
                "default": 10
            }
        },
        "required": ["series"]
    }
}
