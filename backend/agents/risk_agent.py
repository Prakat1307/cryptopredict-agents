import math
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
import pandas as pd
from agents.base_agent import BaseAgent
from utils.helpers import timestamp_now, calculate_returns, calculate_correlation_matrix

class RiskAgent(BaseAgent):

    def __init__(self, config: Dict[str, Any]):
        super().__init__('risk', config)
        self.risk_config = config.get('risk', {})
        self.bankroll = self.risk_config.get('bankroll', 1000.0)
        self.max_kelly_fraction = self.risk_config.get('max_kelly_fraction', 0.25)
        self.correlation_threshold = self.risk_config.get('correlation_threshold', 0.7)
        self.diversification_max = self.risk_config.get('diversification_max', 0.3)
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.register_tool('kelly_size', self._kelly_size)
        self.register_tool('portfolio_optimize', self._portfolio_optimize)
        self.register_tool('risk_assess', self._risk_assess)
        self.register_tool('drawdown_control', self._drawdown_control)

    async def initialize(self):
        await super().initialize()
        self.logger.logger.info(f'RiskAgent initialized with bankroll: ${self.bankroll}')

    async def run(self, prediction: Dict[str, Any], asset: str='BTC', **kwargs) -> Dict[str, Any]:
        self.status = 'running'
        self.last_run = timestamp_now()
        self.logger.log_decision(f'Assessing risk for {asset} prediction', {'asset': asset, 'prediction': prediction})
        try:
            kelly = await self.execute_tool('kelly_size', prediction=prediction)
            risk = await self.execute_tool('risk_assess', asset=asset, prediction=prediction)
            dd_control = await self.execute_tool('drawdown_control')
            result = {'asset': asset, 'timestamp': timestamp_now(), 'recommendation': self._generate_recommendation(kelly, risk, dd_control), 'position_size': kelly['recommended_size'], 'kelly_fraction': kelly['kelly_fraction'], 'half_kelly': kelly['half_kelly'], 'quarter_kelly': kelly['quarter_kelly'], 'risk_metrics': risk, 'drawdown_control': dd_control, 'bankroll': self.bankroll, 'max_position': self.bankroll * self.diversification_max}
            self.add_to_memory({'action': 'risk_assess', 'asset': asset, 'result': result})
            self.status = 'idle'
            return result
        except Exception as e:
            self.status = 'error'
            self.logger.log_error(e, {'asset': asset, 'prediction': prediction})
            raise

    async def _kelly_size(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        upside_prob = prediction.get('upside_probability', 0.5)
        confidence = prediction.get('confidence', 0.5)
        expected_return = prediction.get('expected_return', 0)
        p = upside_prob * confidence
        q = 1 - p
        if p > 0.5:
            b = p / q
        else:
            b = q / p
        if b <= 0:
            kelly_f = 0
        else:
            kelly_f = (b * p - q) / b
        kelly_f = max(0, min(kelly_f, self.max_kelly_fraction))
        full_kelly = self.bankroll * kelly_f
        half_kelly = self.bankroll * kelly_f * 0.5
        quarter_kelly = self.bankroll * kelly_f * 0.25
        recommended = min(half_kelly, self.bankroll * self.diversification_max)
        self.logger.log_action('kelly_calc', {'p': round(p, 4), 'q': round(q, 4), 'b': round(b, 4), 'kelly_f': round(kelly_f, 4)})
        return {'kelly_fraction': round(kelly_f, 4), 'full_kelly': round(full_kelly, 2), 'half_kelly': round(half_kelly, 2), 'quarter_kelly': round(quarter_kelly, 2), 'recommended_size': round(recommended, 2), 'win_probability': round(p, 4), 'odds': round(b, 4)}

    async def _portfolio_optimize(self, assets_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        if not assets_data:
            return {'weights': {}, 'expected_return': 0, 'volatility': 0}
        returns_dict = {}
        for asset, df in assets_data.items():
            if 'close' in df.columns:
                returns_dict[asset] = calculate_returns(df['close'])
        if len(returns_dict) < 2:
            return {'weights': {k: 1.0 for k in returns_dict}, 'expected_return': 0, 'volatility': 0}
        returns_df = pd.DataFrame(returns_dict).dropna()
        if returns_df.empty:
            return {'weights': {}, 'expected_return': 0, 'volatility': 0}
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()
        inv_vol = 1 / returns_df.std()
        weights = inv_vol / inv_vol.sum()
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return {'weights': {k: round(v, 4) for k, v in zip(returns_dict.keys(), weights)}, 'expected_return': round(portfolio_return, 6), 'volatility': round(portfolio_vol, 6), 'sharpe': round(portfolio_return / portfolio_vol if portfolio_vol > 0 else 0, 4)}

    async def _risk_assess(self, asset: str, prediction: Dict[str, Any]) -> Dict[str, Any]:
        confidence = prediction.get('confidence', 0.5)
        volatility = prediction.get('volatility', 0.01)
        regime = prediction.get('regime', 'unknown')
        risk_score = 0
        risk_score += (1 - confidence) * 0.3
        risk_score += min(volatility * 10, 0.3)
        regime_risk = {'trending': 0.1, 'mean_reverting': 0.2, 'random_walk': 0.3, 'unknown': 0.4}
        risk_score += regime_risk.get(regime, 0.3)
        risk_score = min(risk_score, 1.0)
        if risk_score < 0.3:
            level = 'low'
        elif risk_score < 0.6:
            level = 'medium'
        else:
            level = 'high'
        return {'risk_score': round(risk_score, 4), 'risk_level': level, 'confidence_risk': round((1 - confidence) * 0.3, 4), 'volatility_risk': round(min(volatility * 10, 0.3), 4), 'regime_risk': regime_risk.get(regime, 0.3), 'recommendation': 'proceed' if risk_score < 0.5 else 'caution' if risk_score < 0.7 else 'avoid'}

    async def _drawdown_control(self) -> Dict[str, Any]:
        if not self.trade_history:
            return {'current_drawdown': 0, 'max_drawdown': 0, 'status': 'ok'}
        pnl = [t.get('pnl', 0) for t in self.trade_history]
        cumulative = np.cumsum(pnl)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / np.maximum(running_max, 1)
        current_dd = drawdown[-1] if len(drawdown) > 0 else 0
        max_dd = np.min(drawdown) if len(drawdown) > 0 else 0
        if current_dd < -0.15:
            status = 'halt'
        elif current_dd < -0.1:
            status = 'reduce'
        elif current_dd < -0.05:
            status = 'caution'
        else:
            status = 'ok'
        return {'current_drawdown': round(float(current_dd), 4), 'max_drawdown': round(float(max_dd), 4), 'status': status, 'total_trades': len(self.trade_history), 'total_pnl': round(float(cumulative[-1]) if len(cumulative) > 0 else 0, 2)}

    def _generate_recommendation(self, kelly: Dict, risk: Dict, dd: Dict) -> str:
        if dd.get('status') == 'halt':
            return 'HALT_TRADING'
        if risk.get('risk_level') == 'high':
            return 'AVOID'
        if kelly['kelly_fraction'] < 0.02:
            return 'NO_EDGE'
        if dd.get('status') == 'reduce':
            return 'REDUCE_SIZE'
        if risk.get('risk_level') == 'medium':
            return 'CAUTION'
        return 'PROCEED'

    def record_trade(self, asset: str, direction: str, size: float, entry_price: float, exit_price: float=None):
        trade = {'asset': asset, 'direction': direction, 'size': size, 'entry_price': entry_price, 'exit_price': exit_price, 'timestamp': timestamp_now()}
        if exit_price:
            if direction == 'up':
                trade['pnl'] = size * (exit_price - entry_price) / entry_price
            else:
                trade['pnl'] = size * (entry_price - exit_price) / entry_price
        self.trade_history.append(trade)
        self.positions[asset] = trade