"""
LLM Reasoning Agent - Uses OpenRouter for market analysis and reasoning.
Provides intelligent interpretation of prediction results.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx

from agents.base_agent import BaseAgent
from utils.helpers import timestamp_now


class LLMAgent(BaseAgent):
    """
    Agent that uses OpenRouter LLM for market reasoning and analysis.
    Provides intelligent interpretation of predictions, market context,
    and trading recommendations.
    
    Uses free models via OpenRouter:
    - meta-llama/llama-3.1-8b-instruct:free
    - google/gemini-2.0-flash-exp:free
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("llm_reasoning", config)
        
        llm_config = config.get("llm", {})
        self.api_key = os.getenv("OPENROUTER_API_KEY") or llm_config.get("api_key", "")
        self.base_url = llm_config.get("base_url", "https://openrouter.ai/api/v1")
        self.model = llm_config.get("model", "meta-llama/llama-3.1-8b-instruct:free")
        self.fallback_model = llm_config.get("fallback_model", "mistralai/mistral-7b-instruct:free")
        self.max_tokens = llm_config.get("max_tokens", 512)
        self.temperature = llm_config.get("temperature", 0.3)
        
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.available = bool(self.api_key)
        
        # Register tools
        self.register_tool("analyze_market", self._analyze_market)
        self.register_tool("explain_prediction", self._explain_prediction)
        self.register_tool("arbitrage_reasoning", self._arbitrage_reasoning)
        self.register_tool("risk_assessment_reasoning", self._risk_assessment_reasoning)
    
    async def initialize(self):
        await super().initialize()
        if self.available:
            self.logger.logger.info(f"LLM Agent initialized with model: {self.model}")
        else:
            self.logger.logger.warning("LLM Agent: No OpenRouter API key found. LLM reasoning disabled.")
    
    async def run(self, task: str = "analyze", context: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Run LLM reasoning task.
        
        Args:
            task: Task type (analyze, explain, arbitrage, risk)
            context: Context data for the LLM
        """
        self.status = "running"
        self.last_run = timestamp_now()
        
        if not self.available:
            return {
                "reasoning": "LLM reasoning not available (no API key)",
                "recommendation": "Use statistical predictions only",
                "timestamp": timestamp_now()
            }
        
        try:
            if task == "analyze":
                result = await self.execute_tool("analyze_market", context=context)
            elif task == "explain":
                result = await self.execute_tool("explain_prediction", context=context)
            elif task == "arbitrage":
                result = await self.execute_tool("arbitrage_reasoning", context=context)
            elif task == "risk":
                result = await self.execute_tool("risk_assessment_reasoning", context=context)
            else:
                result = await self._call_llm(f"Analyze this crypto trading context: {json.dumps(context)}")
            
            self.add_to_memory({
                "action": f"llm_{task}",
                "context": context,
                "result": result
            })
            
            self.status = "idle"
            return result
            
        except Exception as e:
            self.status = "error"
            self.logger.log_error(e, {"task": task, "context": context})
            return {
                "reasoning": f"LLM error: {str(e)}",
                "recommendation": "Fallback to statistical analysis",
                "timestamp": timestamp_now()
            }
    
    async def _analyze_market(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market conditions using LLM."""
        asset = context.get("asset", "BTC")
        prediction = context.get("prediction", {})
        market_data = context.get("market_data", {})
        
        prompt = f"""You are a crypto market analyst. Analyze the following prediction data and provide concise insights.

Asset: {asset}
Prediction: {prediction.get('direction', 'unknown')} with {prediction.get('confidence', 0)*100:.1f}% confidence
Upside Probability: {prediction.get('upside_probability', 0)*100:.1f}%
Regime: {prediction.get('regime', 'unknown')}
Volatility: {prediction.get('volatility_forecast', 0):.4f}

Market Data:
- Polymarket price: {market_data.get('polymarket_price', 'N/A')}
- Kalshi price: {market_data.get('kalshi_price', 'N/A')}

Provide:
1. A brief market analysis (2-3 sentences)
2. Key risks to consider
3. A trading recommendation (BUY/SELL/HOLD with reasoning)

Keep your response concise and actionable."""
        
        response = await self._call_llm(prompt)
        return {
            "analysis": response,
            "asset": asset,
            "timestamp": timestamp_now(),
            "model_used": self.model
        }
    
    async def _explain_prediction(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Explain prediction reasoning using LLM."""
        prediction = context.get("prediction", {})
        
        prompt = f"""Explain this crypto price prediction in simple terms:

Direction: {prediction.get('direction', 'unknown')}
Confidence: {prediction.get('confidence', 0)*100:.1f}%
Expected Return: {prediction.get('expected_return', 0):.4f}
Market Regime: {prediction.get('regime', 'unknown')}

Explain why this prediction was made and what factors influenced it. Keep it under 100 words."""
        
        response = await self._call_llm(prompt)
        return {
            "explanation": response,
            "timestamp": timestamp_now()
        }
    
    async def _arbitrage_reasoning(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reason about arbitrage opportunities."""
        opportunities = context.get("opportunities", [])
        asset = context.get("asset", "BTC")
        
        prompt = f"""Analyze these arbitrage opportunities for {asset}:

{json.dumps(opportunities, indent=2)}

Provide:
1. Which opportunity has the highest edge
2. Risk assessment for each
3. Recommended action

Be concise."""
        
        response = await self._call_llm(prompt)
        return {
            "arbitrage_analysis": response,
            "asset": asset,
            "timestamp": timestamp_now()
        }
    
    async def _risk_assessment_reasoning(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """LLM-based risk assessment."""
        risk = context.get("risk", {})
        prediction = context.get("prediction", {})
        
        prompt = f"""Assess the risk of this crypto trade:

Risk Level: {risk.get('risk_level', 'unknown')}
Kelly Fraction: {risk.get('kelly_fraction', 0)*100:.1f}%
Recommendation: {risk.get('recommendation', 'unknown')}
Confidence: {prediction.get('confidence', 0)*100:.1f}%

Provide risk management advice. Keep under 50 words."""
        
        response = await self._call_llm(prompt)
        return {
            "risk_advice": response,
            "timestamp": timestamp_now()
        }
    
    async def _call_llm(self, prompt: str, model: Optional[str] = None) -> str:
        """Call OpenRouter API."""
        use_model = model or self.model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://cryptopredict-agents.local",
            "X-Title": "CryptoPredict Agents"
        }
        
        payload = {
            "model": use_model,
            "messages": [
                {"role": "system", "content": "You are a concise crypto trading analyst. Provide brief, actionable insights."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip()
            
        except httpx.HTTPStatusError as e:
            # Try fallback model
            if use_model != self.fallback_model:
                self.logger.logger.warning(f"Primary model failed ({e.response.status_code}), trying fallback: {self.fallback_model}")
                return await self._call_llm(prompt, model=self.fallback_model)
            # Both models failed — return graceful fallback instead of crashing
            self.logger.logger.error(f"All LLM models failed. Returning statistical fallback.")
            return "Statistical model used — LLM unavailable. Check OpenRouter key and model availability."
        except Exception as e:
            self.logger.logger.error(f"LLM API error: {e}")
            raise
    
    async def shutdown(self):
        await self.http_client.aclose()
        await super().shutdown()
