"""
Prediction Agent - Uses Kronos foundation model for crypto price prediction.
Implements probabilistic forecasting with Monte Carlo sampling.

Kronos Integration: https://github.com/shiyu-coder/Kronos
Models: NeoQuasar/Kronos-mini, NeoQuasar/Kronos-small, NeoQuasar/Kronos-base
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from agents.base_agent import BaseAgent
from utils.helpers import timestamp_now, calculate_returns, detect_regime
from kronos_integration import KronosIntegration


class PredictionAgent(BaseAgent):
    """
    Agent responsible for predicting crypto price movements.
    Uses Kronos foundation model (https://github.com/shiyu-coder/Kronos)
    for time series forecasting with autoregressive K-line prediction.
    Falls back to statistical methods if Kronos is unavailable.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("prediction", config)
        self.pred_config = config.get("prediction", {})
        self.model_name = self.pred_config.get("model", "NeoQuasar/Kronos-small")
        self.tokenizer_name = self.pred_config.get("tokenizer", "NeoQuasar/Kronos-Tokenizer-base")
        self.device = self.pred_config.get("device", "cpu")
        self.sample_count = self.pred_config.get("sample_count", 30)
        self.max_context = self.pred_config.get("max_context", 512)
        
        # Kronos integration from https://github.com/shiyu-coder/Kronos
        model_size = self._extract_model_size(self.model_name)
        self.kronos = KronosIntegration(model_size=model_size, device=self.device)
        self.kronos_available = False
        
        # Register tools
        self.register_tool("kronos_predict", self._kronos_predict)
        self.register_tool("statistical_predict", self._statistical_predict)
        self.register_tool("ensemble_predict", self._ensemble_predict)
        self.register_tool("monte_carlo_simulate", self._monte_carlo_simulate)
    
    def _extract_model_size(self, model_name: str) -> str:
        """Extract model size from HuggingFace model name."""
        if "mini" in model_name.lower():
            return "mini"
        elif "small" in model_name.lower():
            return "small"
        elif "base" in model_name.lower():
            return "base"
        return "small"
    
    async def initialize(self):
        await super().initialize()
        
        # Try to load Kronos model from https://github.com/shiyu-coder/Kronos
        try:
            loaded = self.kronos.load_model()
            self.kronos_available = loaded
            if loaded:
                self.logger.logger.info(
                    f"Kronos model loaded successfully from HuggingFace: {self.model_name}"
                )
            else:
                self.logger.logger.warning(
                    "Kronos model not available - using statistical fallback. "
                    "To use Kronos, ensure git and transformers are installed."
                )
        except Exception as e:
            self.kronos_available = False
            self.logger.logger.warning(
                f"Could not load Kronos model: {e}. Using statistical fallback."
            )
    
    async def run(self, asset: str = "BTC", data: pd.DataFrame = None, timeframe: str = "5m", **kwargs) -> Dict[str, Any]:
        """
        Run prediction for an asset.
        
        Args:
            asset: Asset symbol
            data: OHLCV DataFrame
            timeframe: Prediction timeframe
        
        Returns:
            Dict with prediction results
        """
        self.status = "running"
        self.last_run = timestamp_now()
        
        if data is None or data.empty:
            raise ValueError("No data provided for prediction")
        
        self.logger.log_decision(
            f"Predicting {asset} for {timeframe} timeframe",
            {"asset": asset, "data_points": len(data), "timeframe": timeframe}
        )
        
        try:
            # Determine prediction length based on timeframe
            pred_config = self.pred_config.get("pred_lengths", {})
            pred_len = pred_config.get("short", 5) if timeframe in ["1m", "5m"] else \
                      pred_config.get("medium", 15) if timeframe in ["15m", "30m"] else \
                      pred_config.get("long", 60)
            
            # Run prediction using Kronos if available
            if self.kronos_available:
                prediction = await self.execute_tool("kronos_predict", data=data, pred_len=pred_len)
            else:
                prediction = await self.execute_tool("statistical_predict", data=data, pred_len=pred_len)
            
            # Run Monte Carlo for uncertainty quantification
            mc_results = await self.execute_tool("monte_carlo_simulate", data=data, pred_len=pred_len)
            
            # Combine results
            result = {
                "asset": asset,
                "timeframe": timeframe,
                "prediction_length": pred_len,
                "timestamp": timestamp_now(),
                "direction": prediction["direction"],
                "confidence": prediction["confidence"],
                "upside_probability": prediction["upside_probability"],
                "expected_return": prediction["expected_return"],
                "volatility_forecast": prediction["volatility"],
                "regime": prediction.get("regime", "unknown"),
                "monte_carlo": mc_results,
                "model_used": prediction.get("model", "statistical"),
                "kronos_info": self.kronos.get_model_info() if self.kronos_available else None
            }
            
            self.add_to_memory({
                "action": "predict",
                "asset": asset,
                "prediction": result
            })
            
            self.status = "idle"
            return result
            
        except Exception as e:
            self.status = "error"
            self.logger.log_error(e, {"asset": asset, "timeframe": timeframe})
            raise
    
    async def _kronos_predict(self, data: pd.DataFrame, pred_len: int) -> Dict[str, Any]:
        """
        Predict using Kronos foundation model from https://github.com/shiyu-coder/Kronos.
        Uses autoregressive K-line prediction with Monte Carlo sampling.
        """
        try:
            result = self.kronos.predict(
                df=data,
                pred_len=pred_len,
                sample_count=self.sample_count,
                temperature=1.0
            )
            
            # Add regime detection
            result["regime"] = detect_regime(data["close"])
            result["last_price"] = round(data["close"].iloc[-1], 2)
            
            self.logger.log_action("kronos_predict", {
                "direction": result["direction"],
                "confidence": result["confidence"],
                "model": result.get("model", "kronos")
            })
            
            return result
            
        except Exception as e:
            self.logger.logger.warning(f"Kronos prediction failed: {e}, falling back to statistical")
            return await self._statistical_predict(data, pred_len)
    
    async def _statistical_predict(self, data: pd.DataFrame, pred_len: int) -> Dict[str, Any]:
        """Predict using statistical methods (ARIMA-like, momentum, etc.)."""
        closes = data["close"].values
        returns = calculate_returns(data["close"])
        
        # Recent trend analysis
        short_window = min(20, len(closes) // 10)
        long_window = min(50, len(closes) // 4)
        
        if len(closes) >= long_window:
            sma_short = np.mean(closes[-short_window:])
            sma_long = np.mean(closes[-long_window:])
            trend = "up" if sma_short > sma_long else "down"
        else:
            trend = "neutral"
        
        # Momentum (RSI-like)
        if len(returns) >= 14:
            gains = returns[returns > 0]
            losses = -returns[returns < 0]
            avg_gain = np.mean(gains[-14:]) if len(gains) > 0 else 0
            avg_loss = np.mean(losses[-14:]) if len(losses) > 0 else 0.001
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # Volatility
        vol = returns.std() if len(returns) > 0 else 0.01
        
        # Regime detection
        regime = detect_regime(data["close"])
        
        # Predict next move
        last_price = closes[-1]
        
        # Combine signals
        trend_score = 1.0 if trend == "up" else -1.0 if trend == "down" else 0
        rsi_score = (rsi - 50) / 50  # Normalize to -1 to 1
        
        # Weighted combination
        if regime == "trending":
            weights = {"trend": 0.6, "rsi": 0.2, "momentum": 0.2}
        elif regime == "mean_reverting":
            weights = {"trend": 0.2, "rsi": 0.5, "momentum": 0.3}
        else:
            weights = {"trend": 0.33, "rsi": 0.33, "momentum": 0.34}
        
        # Momentum from recent returns
        recent_momentum = np.mean(returns[-5:]) if len(returns) >= 5 else 0
        momentum_score = np.sign(recent_momentum) * min(abs(recent_momentum) * 100, 1)
        
        combined_score = (
            weights["trend"] * trend_score +
            weights["rsi"] * rsi_score +
            weights["momentum"] * momentum_score
        )
        
        # Convert to probability
        upside_prob = 1 / (1 + np.exp(-combined_score * 3))  # Sigmoid
        
        # Expected return
        expected_return = combined_score * vol * np.sqrt(pred_len)
        
        # Confidence based on signal strength and data quality
        confidence = min(abs(combined_score) * 0.8 + 0.2, 0.95)
        
        direction = "up" if upside_prob > 0.5 else "down"
        
        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "upside_probability": round(upside_prob, 4),
            "expected_return": round(expected_return, 6),
            "volatility": round(vol, 6),
            "regime": regime,
            "last_price": round(last_price, 2),
            "model": "statistical",
            "signals": {
                "trend": trend,
                "rsi": round(rsi, 2),
                "momentum": round(momentum_score, 4)
            }
        }
    
    async def _ensemble_predict(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple predictions using ensemble methods."""
        if not predictions:
            return {"direction": "neutral", "confidence": 0.5}
        
        # Weight by confidence
        weights = [p["confidence"] for p in predictions]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return {"direction": "neutral", "confidence": 0.5}
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Weighted average of upside probabilities
        upside_probs = [p["upside_probability"] for p in predictions]
        ensemble_prob = sum(w * p for w, p in zip(normalized_weights, upside_probs))
        
        direction = "up" if ensemble_prob > 0.5 else "down"
        confidence = sum(w * p["confidence"] for w, p in zip(normalized_weights, predictions))
        
        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "upside_probability": round(ensemble_prob, 4),
            "ensemble_size": len(predictions)
        }
    
    async def _monte_carlo_simulate(self, data: pd.DataFrame, pred_len: int, n_sims: int = 100) -> Dict[str, Any]:
        """Run Monte Carlo simulation for price paths."""
        closes = data["close"].values
        returns = calculate_returns(data["close"]).values
        
        last_price = closes[-1]
        mu = np.mean(returns) if len(returns) > 0 else 0
        sigma = np.std(returns) if len(returns) > 0 else 0.01
        
        # Simulate paths
        paths = []
        for _ in range(n_sims):
            path = [last_price]
            for _ in range(pred_len):
                # Geometric Brownian Motion
                dt = 1
                shock = np.random.normal(mu * dt, sigma * np.sqrt(dt))
                price = path[-1] * np.exp(shock)
                path.append(price)
            paths.append(path)
        
        paths = np.array(paths)
        
        # Statistics
        final_prices = paths[:, -1]
        upside_count = np.sum(final_prices > last_price)
        mc_upside_prob = upside_count / n_sims
        
        return {
            "upside_probability": round(mc_upside_prob, 4),
            "mean_final_price": round(np.mean(final_prices), 2),
            "std_final_price": round(np.std(final_prices), 2),
            "percentile_5": round(np.percentile(final_prices, 5), 2),
            "percentile_95": round(np.percentile(final_prices, 95), 2),
            "n_simulations": n_sims,
            "sample_paths": paths[:5, :min(10, pred_len + 1)].tolist()
        }
