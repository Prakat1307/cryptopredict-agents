import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

def load_config(config_path: Optional[str]=None) -> Dict[str, Any]:
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    config = _override_from_env(config)
    return config

def _override_from_env(config: Dict[str, Any]) -> Dict[str, Any]:
    if os.getenv('APIFY_API_TOKEN'):
        config.setdefault('apify', {})['api_token'] = os.getenv('APIFY_API_TOKEN')
    if os.getenv('OPENROUTER_API_KEY'):
        config.setdefault('llm', {})['api_key'] = os.getenv('OPENROUTER_API_KEY')
    if os.getenv('KALSHI_API_KEY_ID'):
        config.setdefault('kalshi', {})['api_key_id'] = os.getenv('KALSHI_API_KEY_ID')
    if os.getenv('POLYMARKET_KEY_ID'):
        config.setdefault('polymarket', {})['key_id'] = os.getenv('POLYMARKET_KEY_ID')
    if os.getenv('BANKROLL'):
        config.setdefault('risk', {})['bankroll'] = float(os.getenv('BANKROLL'))
    return config

def get_asset_config(config: Dict[str, Any], symbol: str) -> Optional[Dict[str, Any]]:
    for asset in config.get('assets', []):
        if asset.get('symbol') == symbol:
            return asset
    return None

def get_llm_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get('llm', {})

def get_risk_config(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get('risk', {})