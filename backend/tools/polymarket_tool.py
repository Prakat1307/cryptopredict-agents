"""
Hermes Agent Tool - Polymarket Integration
Provides market data access for Polymarket prediction markets.
"""

import json
import os
from typing import Dict, Any, Optional
import httpx


class PolymarketTool:
    """Tool for accessing Polymarket prediction market data."""
    
    def __init__(self):
        self.base_url = "https://gamma-api.polymarket.com"
        self.clob_url = "https://clob.polymarket.com"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_markets(self, query: str = "bitcoin", limit: int = 10) -> str:
        """Search for markets on Polymarket."""
        try:
            url = f"{self.base_url}/events"
            params = {
                "slug": query.lower(),
                "active": True,
                "closed": False,
                "limit": limit
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            events = data if isinstance(data, list) else data.get("events", [])
            
            markets = []
            for event in events:
                for market in event.get("markets", []):
                    markets.append({
                        "id": market.get("id"),
                        "question": market.get("question"),
                        "slug": event.get("slug"),
                        "volume": market.get("volume", 0),
                        "liquidity": market.get("liquidity", 0),
                        "outcomes": market.get("outcomes", []),
                        "outcomePrices": market.get("outcomePrices", [])
                    })
            
            return json.dumps({
                "success": True,
                "markets": markets,
                "count": len(markets)
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    async def get_price(self, token_id: str, side: str = "BUY") -> str:
        """Get current price for a token."""
        try:
            url = f"{self.clob_url}/price"
            params = {"token_id": token_id, "side": side}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return json.dumps({
                "success": True,
                "price": data.get("price"),
                "token_id": token_id,
                "side": side
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    async def get_orderbook(self, token_id: str) -> str:
        """Get order book for a token."""
        try:
            url = f"{self.clob_url}/book"
            params = {"token_id": token_id}
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return json.dumps({
                "success": True,
                "market": data.get("market"),
                "bids": data.get("bids", []),
                "asks": data.get("asks", [])
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    async def close(self):
        await self.client.aclose()


# Hermes Agent tool schema
POLYMARKET_TOOL_SCHEMA = {
    "name": "polymarket_search",
    "description": "Search for crypto prediction markets on Polymarket",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'bitcoin', 'ethereum')"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 10
            }
        },
        "required": ["query"]
    }
}

POLYMARKET_PRICE_SCHEMA = {
    "name": "polymarket_price",
    "description": "Get current price for a Polymarket outcome token",
    "parameters": {
        "type": "object",
        "properties": {
            "token_id": {
                "type": "string",
                "description": "Token ID from market search"
            },
            "side": {
                "type": "string",
                "enum": ["BUY", "SELL"],
                "default": "BUY"
            }
        },
        "required": ["token_id"]
    }
}
