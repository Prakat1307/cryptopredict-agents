import asyncio
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from agents.base_agent import BaseAgent
from utils.helpers import timestamp_now, safe_json_loads

class SearchAgent(BaseAgent):

    def __init__(self, config: Dict[str, Any]):
        super().__init__('search', config)
        self.polymarket_base = 'https://gamma-api.polymarket.com'
        self.kalshi_base = 'https://api.elections.kalshi.com/trade-api/v2'
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.register_tool('search_polymarket', self._search_polymarket)
        self.register_tool('search_kalshi', self._search_kalshi)
        self.register_tool('get_market_details', self._get_market_details)

    async def initialize(self):
        await super().initialize()
        self.logger.logger.info('SearchAgent initialized with Polymarket + Kalshi tools')

    async def run(self, asset: str='BTC', **kwargs) -> Dict[str, Any]:
        self.status = 'running'
        self.last_run = timestamp_now()
        self.logger.log_decision(f'Searching markets for {asset}', {'asset': asset, 'platforms': ['polymarket', 'kalshi']})
        try:
            results = await asyncio.gather(self.execute_tool('search_polymarket', asset=asset), self.execute_tool('search_kalshi', asset=asset), return_exceptions=True)
            polymarket_data = results[0] if not isinstance(results[0], Exception) else None
            kalshi_data = results[1] if not isinstance(results[1], Exception) else None
            result = {'asset': asset, 'timestamp': timestamp_now(), 'polymarket': polymarket_data, 'kalshi': kalshi_data, 'markets_found': self._count_markets(polymarket_data, kalshi_data)}
            self.add_to_memory({'action': 'search', 'asset': asset, 'result': result})
            self.status = 'idle'
            return result
        except Exception as e:
            self.status = 'error'
            self.logger.log_error(e, {'asset': asset})
            raise

    async def _search_polymarket(self, asset: str) -> Optional[Dict[str, Any]]:
        try:
            slug_patterns = [f'{asset.lower()}-', f'bitcoin' if asset == 'BTC' else f'ethereum' if asset == 'ETH' else asset.lower()]
            markets = []
            for slug in slug_patterns:
                url = f'{self.polymarket_base}/events'
                params = {'slug': slug, 'active': True, 'closed': False, 'limit': 20}
                response = await self.http_client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    events = data if isinstance(data, list) else data.get('events', [])
                    for event in events:
                        for market in event.get('markets', []):
                            markets.append({'id': market.get('id'), 'question': market.get('question'), 'slug': event.get('slug'), 'volume': market.get('volume', 0), 'liquidity': market.get('liquidity', 0), 'outcomes': market.get('outcomes', []), 'outcomePrices': market.get('outcomePrices', []), 'end_date': market.get('endDate')})
            short_term = [m for m in markets if any((kw in m['question'].lower() for kw in ['5 minute', '15 minute', 'next 5', 'next 15', 'up or down']))]
            return {'markets': short_term[:5] if short_term else markets[:5], 'total_found': len(markets), 'short_term_found': len(short_term), 'platform': 'polymarket'}
        except Exception as e:
            self.logger.log_error(e, {'platform': 'polymarket', 'asset': asset})
            return None

    async def _search_kalshi(self, asset: str) -> Optional[Dict[str, Any]]:
        try:
            series_map = {'BTC': 'KXBTC', 'ETH': 'KXETH'}
            series = series_map.get(asset, f'KX{asset}')
            url = f'{self.kalshi_base}/markets'
            params = {'series_ticker': series, 'status': 'open', 'limit': 20}
            response = await self.http_client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                markets = data.get('markets', [])
                short_term = [m for m in markets if any((kw in m.get('title', '').lower() for kw in ['5 minute', '15 minute', 'next 5', 'next 15']))]
                return {'markets': short_term[:5] if short_term else markets[:5], 'total_found': len(markets), 'short_term_found': len(short_term), 'platform': 'kalshi'}
            return None
        except Exception as e:
            self.logger.log_error(e, {'platform': 'kalshi', 'asset': asset})
            return None

    async def _get_market_details(self, platform: str, market_id: str) -> Optional[Dict[str, Any]]:
        try:
            if platform == 'polymarket':
                url = f'{self.polymarket_base}/markets/{market_id}'
                response = await self.http_client.get(url)
                if response.status_code == 200:
                    return response.json()
            elif platform == 'kalshi':
                url = f'{self.kalshi_base}/markets/{market_id}'
                response = await self.http_client.get(url)
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            self.logger.log_error(e, {'platform': platform, 'market_id': market_id})
            return None

    def _count_markets(self, poly_data: Any, kalshi_data: Any) -> int:
        count = 0
        if poly_data and isinstance(poly_data, dict):
            count += poly_data.get('total_found', 0)
        if kalshi_data and isinstance(kalshi_data, dict):
            count += kalshi_data.get('total_found', 0)
        return count

    async def shutdown(self):
        await self.http_client.aclose()
        await super().shutdown()