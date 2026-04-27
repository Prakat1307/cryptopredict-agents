import asyncio
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
import pandas as pd
import numpy as np
from agents.base_agent import BaseAgent
from utils.helpers import timestamp_now, resample_ohlcv
CACHE_TTL: Dict[str, int] = {'1m': 60, '5m': 300, '15m': 900, '30m': 1800, '1h': 3600, '4h': 14400, '1d': 86400}

class DataAgent(BaseAgent):

    def __init__(self, config: Dict[str, Any]):
        super().__init__('data', config)
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.apify_token = os.getenv('APIFY_API_TOKEN', '')
        self.apify_enabled = os.getenv('APIFY_ENABLED', 'false').lower() == 'true'
        self._cache: Dict[Tuple[str, str], Tuple[pd.DataFrame, datetime]] = {}
        self._batch_fetched_at: Optional[datetime] = None
        self._batch_ttl: int = CACHE_TTL.get('5m', 300)
        self.register_tool('fetch_binance', self._fetch_binance)
        self.register_tool('fetch_apify_batch', self._fetch_apify_batch)
        self.register_tool('fetch_multi_timeframe', self._fetch_multi_timeframe)
        self.register_tool('get_latest_price', self._get_latest_price)

    async def initialize(self):
        await super().initialize()
        mode = 'Apify (batch) + Binance fallback' if self.apify_enabled else 'Binance only (Apify disabled)'
        self.logger.logger.info(f'DataAgent initialized | mode: {mode} | cache TTL per interval')

    async def run(self, asset: str='BTC', bars: int=1000, interval: str='5m', **kwargs) -> Dict[str, Any]:
        self.status = 'running'
        self.last_run = timestamp_now()
        self.logger.log_decision(f'Fetching {bars} bars of {interval} data for {asset}', {'asset': asset, 'bars': bars, 'interval': interval})
        try:
            data, source = await self._get_data(asset, bars, interval)
            result = {'asset': asset, 'interval': interval, 'bars': len(data) if hasattr(data, '__len__') else 0, 'source': source, 'timestamp': timestamp_now(), 'data': data}
            self.add_to_memory({'action': 'fetch_data', 'asset': asset, 'bars': bars, 'source': source})
            self.status = 'idle'
            return result
        except Exception as e:
            self.status = 'error'
            self.logger.log_error(e, {'asset': asset, 'bars': bars})
            raise

    async def fetch_data(self, asset: str, bars: int=1000, interval: str='5m') -> pd.DataFrame:
        result = await self.run(asset=asset, bars=bars, interval=interval)
        return result.get('data', pd.DataFrame())

    async def _get_data(self, asset: str, bars: int, interval: str) -> Tuple[pd.DataFrame, str]:
        cached = self._from_cache(asset, interval)
        if cached is not None:
            self.logger.logger.info(f'Cache hit: {asset}/{interval}')
            return (cached, 'cache')
        if self.apify_token and self.apify_enabled:
            if self._batch_needs_refresh():
                try:
                    await self._fetch_apify_batch()
                    cached = self._from_cache(asset, interval)
                    if cached is not None:
                        return (cached, 'apify_batch')
                except Exception as e:
                    self.logger.logger.warning(f'Apify batch failed: {e}, using Binance')
        df = await self._fetch_binance(asset=asset, bars=bars, interval=interval)
        self._to_cache(asset, interval, df)
        return (df, 'binance')

    def _from_cache(self, asset: str, interval: str) -> Optional[pd.DataFrame]:
        key = (asset.upper(), interval)
        if key not in self._cache:
            return None
        df, fetched_at = self._cache[key]
        ttl = CACHE_TTL.get(interval, 300)
        if (datetime.utcnow() - fetched_at).total_seconds() < ttl:
            return df
        del self._cache[key]
        return None

    def _to_cache(self, asset: str, interval: str, df: pd.DataFrame):
        self._cache[asset.upper(), interval] = (df, datetime.utcnow())

    def _batch_needs_refresh(self) -> bool:
        if self._batch_fetched_at is None:
            return True
        return (datetime.utcnow() - self._batch_fetched_at).total_seconds() >= self._batch_ttl

    async def _fetch_binance(self, asset: str, bars: int, interval: str) -> pd.DataFrame:
        symbol = f'{asset.upper()}USDT'
        interval_map = {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h', '4h': '4h', '1d': '1d'}
        binance_interval = interval_map.get(interval, '5m')
        response = await self.http_client.get('https://api.binance.com/api/v3/klines', params={'symbol': symbol, 'interval': binance_interval, 'limit': min(bars, 1000)})
        response.raise_for_status()
        df = pd.DataFrame(response.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        self.logger.log_action('binance_fetch', {'symbol': symbol, 'rows': len(df)})
        return df

    async def _fetch_apify_batch(self, *args, **kwargs):
        from apify_client import ApifyClient
        config_assets = self.config.get('assets', [])
        symbols = [a['symbol'] if isinstance(a, dict) else a for a in config_assets]
        if not symbols:
            symbols = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE']
        self.logger.logger.info(f'Apify batch fetch for {symbols} (1 token call)')
        client = ApifyClient(self.apify_token)
        run_input = {'symbols': symbols, 'days': '3'}
        run = client.actor('datastorm/cryptoprices-api').call(run_input=run_input)
        items = list(client.dataset(run['defaultDatasetId']).iterate_items())
        if not items:
            raise ValueError('Apify returned no data')
        df_all = pd.DataFrame(items)
        self._batch_fetched_at = datetime.utcnow()
        symbol_col = next((c for c in df_all.columns if c.lower() in ('symbol', 'asset', 'ticker')), None)
        for symbol in symbols:
            if symbol_col and symbol_col in df_all.columns:
                df_sym = df_all[df_all[symbol_col].str.upper() == symbol.upper()].copy()
            else:
                df_sym = df_all.copy()
            if df_sym.empty:
                continue
            if 'timestamp' in df_sym.columns:
                df_sym['timestamp'] = pd.to_datetime(df_sym['timestamp'])
                df_sym.set_index('timestamp', inplace=True)
            for interval in ['5m', '15m']:
                self._to_cache(symbol, interval, df_sym)
        self.logger.logger.info(f'Apify batch complete — cached {len(symbols)} assets (cost: 1 Apify call)')

    async def _fetch_multi_timeframe(self, asset: str, timeframes: List[str], bars: int=1000) -> Dict[str, pd.DataFrame]:
        tasks = [self._get_data(asset, bars, tf) for tf in timeframes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        data: Dict[str, pd.DataFrame] = {}
        for tf, result in zip(timeframes, results):
            if isinstance(result, Exception):
                self.logger.logger.warning(f'Failed to fetch {asset}/{tf}: {result}')
            else:
                df, _ = result
                data[tf] = df
        return data

    async def _get_latest_price(self, asset: str) -> Dict[str, Any]:
        symbol = f'{asset.upper()}USDT'
        response = await self.http_client.get('https://api.binance.com/api/v3/ticker/24hr', params={'symbol': symbol})
        response.raise_for_status()
        data = response.json()
        return {'symbol': asset, 'price': float(data['lastPrice']), 'change_24h': float(data['priceChangePercent']), 'volume_24h': float(data['volume']), 'high_24h': float(data['highPrice']), 'low_24h': float(data['lowPrice'])}

    async def shutdown(self):
        await self.http_client.aclose()
        await super().shutdown()