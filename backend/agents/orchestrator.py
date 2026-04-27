import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
from agents.search_agent import SearchAgent
from agents.data_agent import DataAgent
from agents.prediction_agent import PredictionAgent
from agents.risk_agent import RiskAgent
from agents.feedback_agent import FeedbackAgent
from agents.llm_agent import LLMAgent
from utils.logging_config import get_logger
from utils.helpers import timestamp_now, CircularBuffer

class AgentOrchestrator:

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger('orchestrator')
        self.search_agent = SearchAgent(config)
        self.data_agent = DataAgent(config)
        self.prediction_agent = PredictionAgent(config)
        self.llm_agent = LLMAgent(config)
        self.risk_agent = RiskAgent(config)
        self.feedback_agent = FeedbackAgent(config)
        self.prediction_history = CircularBuffer(size=2000)
        self.active_predictions: Dict[str, Any] = {}
        self.scaling_config = config.get('scaling', {})
        self.assets = [a['symbol'] for a in config.get('assets', [])]

    async def initialize(self):
        self.logger.info('Initializing CryptoPredict Agent Orchestrator...')
        self.logger.info(f'Tracking assets: {self.assets}')
        await asyncio.gather(self.search_agent.initialize(), self.data_agent.initialize(), self.prediction_agent.initialize(), self.llm_agent.initialize(), self.risk_agent.initialize(), self.feedback_agent.initialize())
        self.logger.info('All 6 agents initialized successfully')

    async def shutdown(self):
        self.logger.info('Shutting down orchestrator...')
        await asyncio.gather(self.search_agent.shutdown(), self.data_agent.shutdown(), self.prediction_agent.shutdown(), self.llm_agent.shutdown(), self.risk_agent.shutdown(), self.feedback_agent.shutdown())

    async def run_prediction_pipeline(self, asset: str='BTC', timeframe: str='5m', use_kalshi: bool=True, use_polymarket: bool=True, use_llm: bool=True) -> Dict[str, Any]:
        self.logger.info(f'Running prediction pipeline for {asset}/{timeframe}')
        pipeline_start = datetime.utcnow()
        market_data = None
        if use_polymarket or use_kalshi:
            try:
                market_data = await self.search_agent.run(asset=asset)
                self.logger.info(f"Found markets for {asset}: Polymarket={market_data.get('polymarket') is not None}, Kalshi={market_data.get('kalshi') is not None}")
            except Exception as e:
                self.logger.warning(f'Market search failed: {e}')
        data_result = await self.data_agent.run(asset=asset, bars=1000, interval=timeframe)
        df = data_result.get('data')
        if df is None or (hasattr(df, 'empty') and df.empty):
            raise ValueError(f'No data available for {asset}')
        prediction = await self.prediction_agent.run(asset=asset, data=df, timeframe=timeframe)
        llm_analysis = None
        if use_llm:
            try:
                llm_analysis = await self.llm_agent.run(task='analyze', context={'asset': asset, 'prediction': prediction, 'market_data': {'polymarket_price': self._extract_polymarket_price(market_data), 'kalshi_price': self._extract_kalshi_price(market_data)}})
            except Exception as e:
                self.logger.warning(f'LLM analysis failed: {e}')
        risk = await self.risk_agent.run(prediction=prediction, asset=asset)
        feedback = await self.feedback_agent.run(prediction=prediction)
        poly_price = self._extract_polymarket_price(market_data)
        kalshi_price = self._extract_kalshi_price(market_data)
        pipeline_latency = (datetime.utcnow() - pipeline_start).total_seconds()
        result = {'asset': asset, 'timeframe': timeframe, 'prediction': prediction['direction'], 'confidence': prediction['confidence'], 'upside_probability': prediction['upside_probability'], 'kelly_fraction': risk['kelly_fraction'], 'recommended_position': risk['position_size'], 'polymarket_price': poly_price, 'kalshi_price': kalshi_price, 'timestamp': timestamp_now(), 'reasoning': self._generate_reasoning(prediction, risk, llm_analysis), 'pipeline_latency_ms': round(pipeline_latency * 1000, 2), 'risk_level': risk['risk_metrics']['risk_level'], 'regime': prediction['regime'], 'llm_analysis': llm_analysis, 'kronos_info': prediction.get('kronos_info'), 'model_used': prediction.get('model_used', 'statistical')}
        self.prediction_history.append(result)
        self.active_predictions[f'{asset}_{timeframe}'] = result
        self.logger.info(f"Pipeline complete: {asset}/{timeframe} -> {prediction['direction'].upper()} (confidence: {prediction['confidence']:.2f}, kelly: {risk['kelly_fraction']:.4f})")
        return result

    async def check_arbitrage(self, asset: str, timeframes: List[str]=None) -> List[Dict[str, Any]]:
        if timeframes is None:
            timeframes = ['5m', '15m']
        self.logger.info(f'Checking arbitrage for {asset} across {timeframes}')
        opportunities = []
        predictions = {}
        for tf in timeframes:
            try:
                pred = await self.run_prediction_pipeline(asset=asset, timeframe=tf, use_llm=False)
                predictions[tf] = pred
            except Exception as e:
                self.logger.warning(f'Failed to predict {tf}: {e}')
        if len(predictions) < 2:
            return opportunities
        tfs = list(predictions.keys())
        for i in range(len(tfs)):
            for j in range(i + 1, len(tfs)):
                tf1, tf2 = (tfs[i], tfs[j])
                p1, p2 = (predictions[tf1], predictions[tf2])
                if p1['prediction'] != p2['prediction']:
                    if p1['confidence'] > 0.55 and p2['confidence'] > 0.55:
                        spread = abs(p1['upside_probability'] - p2['upside_probability'])
                        min_spread = self.scaling_config.get('arbitrage', {}).get('min_spread', 0.02)
                        if spread > min_spread:
                            opp = {'type': 'direction_mismatch', 'asset': asset, 'timeframe_a': tf1, 'timeframe_b': tf2, 'prediction_a': p1['prediction'], 'prediction_b': p2['prediction'], 'confidence_a': p1['confidence'], 'confidence_b': p2['confidence'], 'upside_prob_a': p1['upside_probability'], 'upside_prob_b': p2['upside_probability'], 'spread': round(spread, 4), 'recommended': f'trust_{tf1}' if p1['confidence'] > p2['confidence'] else f'trust_{tf2}', 'timestamp': timestamp_now()}
                            opportunities.append(opp)
                elif p1['prediction'] == p2['prediction']:
                    conf_diff = abs(p1['confidence'] - p2['confidence'])
                    if conf_diff > 0.15:
                        opp = {'type': 'confidence_divergence', 'asset': asset, 'timeframe_a': tf1, 'timeframe_b': tf2, 'prediction': p1['prediction'], 'confidence_a': p1['confidence'], 'confidence_b': p2['confidence'], 'confidence_diff': round(conf_diff, 4), 'recommended': f'size_by_{tf1}' if p1['confidence'] > p2['confidence'] else f'size_by_{tf2}', 'timestamp': timestamp_now()}
                        opportunities.append(opp)
        if '15m' in predictions and '5m' in predictions:
            p_15m = predictions['15m']
            p_5m = predictions['5m']
            if p_15m['prediction'] == 'up' and p_5m['prediction'] == 'down':
                opportunities.append({'type': 'internal_arbitrage_15m_vs_5m', 'asset': asset, 'description': '15min UP but 5min DOWN - possible reversal within 15min window', 'strategy': 'Wait for 5min reversal then enter 15min direction', 'edge': round(p_15m['confidence'] - p_5m['confidence'], 4), 'timestamp': timestamp_now()})
            if p_15m['prediction'] == p_5m['prediction'] and p_15m['confidence'] > 0.65 and (p_5m['confidence'] > 0.65):
                opportunities.append({'type': 'aligned_signal', 'asset': asset, 'description': f"Both 15m and 5m agree on {p_15m['prediction'].upper()} with high confidence", 'strategy': 'Aggressive position sizing', 'combined_confidence': round((p_15m['confidence'] + p_5m['confidence']) / 2, 4), 'timestamp': timestamp_now()})
        if opportunities and self.llm_agent.available:
            try:
                llm_arb = await self.llm_agent.run(task='arbitrage', context={'opportunities': opportunities, 'asset': asset})
                for opp in opportunities:
                    opp['llm_reasoning'] = llm_arb.get('arbitrage_analysis', '')
            except Exception as e:
                self.logger.warning(f'LLM arbitrage reasoning failed: {e}')
        return opportunities

    async def run_multi_asset_cycle(self, assets: List[str]=None, timeframes: List[str]=None):
        if assets is None:
            assets = self.assets
        if timeframes is None:
            timeframes = ['5m', '15m']
        self.logger.info(f'Running multi-asset cycle for {len(assets)} assets: {assets}')
        results = []
        for asset in assets:
            for tf in timeframes:
                try:
                    result = await self.run_prediction_pipeline(asset=asset, timeframe=tf)
                    results.append(result)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    self.logger.error(f'Cycle failed for {asset}/{tf}: {e}')
        if len(assets) >= 2:
            try:
                cross_arb = await self._check_cross_asset_arbitrage(results)
                self.logger.info(f'Cross-asset arbitrage opportunities: {len(cross_arb)}')
            except Exception as e:
                self.logger.warning(f'Cross-asset arbitrage check failed: {e}')
        self.logger.info(f'Multi-asset cycle complete: {len(results)} predictions generated')
        return results

    async def _check_cross_asset_arbitrage(self, predictions: List[Dict]) -> List[Dict]:
        opportunities = []
        by_tf = {}
        for p in predictions:
            tf = p.get('timeframe', '5m')
            if tf not in by_tf:
                by_tf[tf] = []
            by_tf[tf].append(p)
        for tf, preds in by_tf.items():
            if len(preds) < 2:
                continue
            ups = [p for p in preds if p.get('prediction') == 'up']
            downs = [p for p in preds if p.get('prediction') == 'down']
            if ups and downs:
                opportunities.append({'type': 'cross_asset_divergence', 'timeframe': tf, 'up_assets': [p['asset'] for p in ups], 'down_assets': [p['asset'] for p in downs], 'strategy': 'Long strongest UP asset, short strongest DOWN asset', 'timestamp': timestamp_now()})
        return opportunities

    def get_status(self) -> Dict[str, Any]:
        return {'status': 'running', 'agents': {'search': self.search_agent.get_status(), 'data': self.data_agent.get_status(), 'prediction': self.prediction_agent.get_status(), 'llm_reasoning': self.llm_agent.get_status(), 'risk': self.risk_agent.get_status(), 'feedback': self.feedback_agent.get_status()}, 'assets_tracked': self.assets, 'scaling': {'multi_asset': self.scaling_config.get('multi_asset', {}).get('enabled', False), 'arbitrage': self.scaling_config.get('arbitrage', {}).get('enabled', False), 'parallel_execution': self.scaling_config.get('parallel_execution', {}).get('enabled', False)}, 'last_update': timestamp_now(), 'active_predictions': len(self.active_predictions), 'total_predictions': len(self.prediction_history.get_all()), 'accuracy': self._calculate_overall_accuracy()}

    def get_feedback_stats(self) -> Dict[str, Any]:
        return self.feedback_agent.get_stats()

    def get_prediction_history(self, asset: Optional[str]=None) -> List[Dict[str, Any]]:
        if asset:
            return self.prediction_history.filter_by('asset', asset)
        return self.prediction_history.get_all()

    def _extract_polymarket_price(self, market_data: Any) -> Optional[float]:
        if not market_data or not isinstance(market_data, dict):
            return None
        poly = market_data.get('polymarket')
        if poly and poly.get('markets'):
            first = poly['markets'][0]
            prices = first.get('outcomePrices', [])
            if prices:
                try:
                    return float(prices[0])
                except (ValueError, TypeError):
                    pass
        return None

    def _extract_kalshi_price(self, market_data: Any) -> Optional[float]:
        if not market_data or not isinstance(market_data, dict):
            return None
        kal = market_data.get('kalshi')
        if kal and kal.get('markets'):
            first = kal['markets'][0]
            yes_bid = first.get('yes_bid')
            if yes_bid is not None:
                try:
                    return float(yes_bid) / 100
                except (ValueError, TypeError):
                    pass
        return None

    def _generate_reasoning(self, prediction: Dict, risk: Dict, llm_analysis: Any) -> str:
        parts = []
        parts.append(f"Predicted {prediction['direction'].upper()} move")
        parts.append(f"with {prediction['confidence'] * 100:.1f}% confidence")
        parts.append(f"(upside probability: {prediction['upside_probability'] * 100:.1f}%)")
        parts.append(f"Market regime: {prediction['regime']}")
        parts.append(f"Risk level: {risk['risk_metrics']['risk_level']}")
        parts.append(f"Kelly fraction: {risk['kelly_fraction'] * 100:.1f}%")
        parts.append(f"Recommended position: ${risk['position_size']:.2f}")
        if llm_analysis and isinstance(llm_analysis, dict):
            analysis = llm_analysis.get('analysis', '')
            if analysis:
                parts.append(f'LLM insight: {analysis[:150]}...')
        return '; '.join(parts)

    def _calculate_overall_accuracy(self) -> Optional[float]:
        feedback_stats = self.feedback_agent.get_stats()
        outcomes = feedback_stats.get('outcomes_stored', 0)
        if outcomes == 0:
            return None
        total_correct = 0
        total_evaluated = 0
        for perf in self.feedback_agent.performance.values():
            total_correct += perf.get('correct', 0)
            total_evaluated += perf.get('total', 0)
        if total_evaluated > 0:
            return round(total_correct / total_evaluated, 4)
        return None