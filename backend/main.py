#!/usr/bin/env python3
"""
CryptoPredict Agents - Main FastAPI Application
A multi-agent system for crypto asset prediction using Hermes Agent framework.

Agents:
- SearchAgent: Finds markets on Polymarket & Kalshi
- DataAgent: Fetches OHLCV via Apify (1000 bars) + Binance fallback
- PredictionAgent: Kronos foundation model (github.com/shiyu-coder/Kronos)
- LLMAgent: OpenRouter reasoning (meta-llama/llama-3.1-8b-instruct:free)
- RiskAgent: Kelly Criterion position sizing
- FeedbackAgent: Hermes Agent learning loop
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_config import setup_logging, get_logger
from utils.config_loader import load_config
from agents.orchestrator import AgentOrchestrator

# Setup logging
setup_logging()
logger = get_logger("main")

# Load config
config = load_config()

# Global orchestrator instance
orchestrator: Optional[AgentOrchestrator] = None


# ==================== Pydantic Models ====================

class PredictionRequest(BaseModel):
    asset: str = Field(default="BTC", description="Asset symbol (BTC, ETH, SOL, etc.)")
    timeframe: str = Field(default="5m", description="Prediction timeframe")
    use_kalshi: bool = Field(default=True, description="Include Kalshi market data")
    use_polymarket: bool = Field(default=True, description="Include Polymarket data")
    use_llm: bool = Field(default=True, description="Include LLM reasoning")


class MultiAssetRequest(BaseModel):
    assets: List[str] = Field(default=None, description="List of assets (default: all configured)")
    timeframes: List[str] = Field(default=["5m", "15m"], description="Timeframes to predict")


class ArbitrageRequest(BaseModel):
    asset: str = Field(default="BTC", description="Asset to check")
    timeframes: List[str] = Field(default=["5m", "15m"], description="Timeframes to compare")


class MarketDataRequest(BaseModel):
    asset: str = Field(default="BTC", description="Asset symbol")
    bars: int = Field(default=1000, ge=10, le=5000, description="Number of bars to fetch")
    interval: str = Field(default="5m", description="Candle interval")


class LLMReasoningRequest(BaseModel):
    task: str = Field(default="analyze", description="Task type: analyze, explain, arbitrage, risk")
    asset: str = Field(default="BTC", description="Asset symbol")
    context: Dict[str, Any] = Field(default={}, description="Additional context")


class SystemStatus(BaseModel):
    status: str
    agents: Dict[str, Any]
    assets_tracked: List[str]
    scaling: Dict[str, bool]
    last_update: str
    active_predictions: int
    total_predictions: int
    accuracy: Optional[float]


# ==================== Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global orchestrator
    logger.info("=" * 60)
    logger.info(" CryptoPredict Agents - Starting Up")
    logger.info("=" * 60)
    logger.info(f"Assets: {config.get('assets', [])}")
    logger.info(f"LLM: {config.get('llm', {}).get('model', 'N/A')}")
    logger.info(f"Kronos: {config.get('prediction', {}).get('model', 'N/A')}")
    logger.info(f"Apify: {'Configured' if os.getenv('APIFY_API_TOKEN') else 'Not configured'}")
    logger.info(f"OpenRouter: {'Configured' if os.getenv('OPENROUTER_API_KEY') else 'Not configured'}")
    
    try:
        orchestrator = AgentOrchestrator(config)
        await orchestrator.initialize()
        logger.info("All agents initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise
    
    yield
    
    logger.info("Shutting down CryptoPredict Agents...")
    if orchestrator:
        await orchestrator.shutdown()


# ==================== App Setup ====================

app = FastAPI(
    title="CryptoPredict Agents API",
    description="""
Multi-agent system for crypto asset prediction and risk management.

**Agents:**
- SearchAgent: Polymarket + Kalshi market discovery
- DataAgent: Apify (1000 bars) + Binance fallback
- PredictionAgent: Kronos foundation model (github.com/shiyu-coder/Kronos)
- LLMAgent: OpenRouter reasoning
- RiskAgent: Kelly Criterion sizing
- FeedbackAgent: Hermes learning loop

**Scaling Features:**
- Multi-asset support (BTC, ETH, SOL, XRP, ADA, DOGE)
- Internal arbitrage (15min vs 3x 5min)
- Cross-timeframe analysis
- Parallel execution
    """,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Routes ====================

@app.get("/")
async def root():
    """API root with available endpoints."""
    return {
        "name": "CryptoPredict Agents",
        "version": "1.0.0",
        "description": "Multi-agent crypto prediction system with Hermes Agent framework",
        "agents": ["search", "data", "prediction", "llm_reasoning", "risk", "feedback"],
        "models": {
            "kronos": config.get("prediction", {}).get("model", "NeoQuasar/Kronos-small"),
            "llm": config.get("llm", {}).get("model", "meta-llama/llama-3.1-8b-instruct:free")
        },
        "endpoints": {
            "predict": "POST /api/predict",
            "multi_asset": "POST /api/predict/multi-asset",
            "market_data": "POST /api/market-data",
            "arbitrage": "POST /api/arbitrage",
            "llm_reasoning": "POST /api/llm/reasoning",
            "status": "GET /api/status",
            "assets": "GET /api/assets",
            "predictions_history": "GET /api/predictions/history",
            "feedback": "GET /api/feedback",
            "run_all": "POST /api/agents/run"
        }
    }


@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get full system status including all agents."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return orchestrator.get_status()


@app.post("/api/predict")
async def predict(request: PredictionRequest):
    """
    Run full prediction pipeline for a single asset.
    
    Pipeline: Search -> Data -> Kronos Predict -> LLM Reason -> Kelly Risk -> Feedback
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        result = await orchestrator.run_prediction_pipeline(
            asset=request.asset,
            timeframe=request.timeframe,
            use_kalshi=request.use_kalshi,
            use_polymarket=request.use_polymarket,
            use_llm=request.use_llm
        )
        return result
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predict/multi-asset")
async def predict_multi_asset(request: MultiAssetRequest):
    """
    Run prediction pipeline for multiple assets (scaling feature).
    
    Supports BTC, ETH, SOL, XRP, ADA, DOGE and custom assets.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        results = await orchestrator.run_multi_asset_cycle(
            assets=request.assets,
            timeframes=request.timeframes
        )
        return {
            "assets": request.assets or orchestrator.assets,
            "timeframes": request.timeframes,
            "predictions_count": len(results),
            "predictions": results
        }
    except Exception as e:
        logger.error(f"Multi-asset prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/market-data")
async def get_market_data(request: MarketDataRequest):
    """Fetch market data for an asset (1000 bars via Apify/Binance)."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        data = await orchestrator.data_agent.fetch_data(
            asset=request.asset,
            bars=request.bars,
            interval=request.interval
        )
        return {
            "asset": request.asset,
            "bars": len(data),
            "interval": request.interval,
            "source": "binance",  # or apify
            "columns": list(data.columns) if hasattr(data, 'columns') else [],
            "latest": {
                "close": float(data["close"].iloc[-1]) if hasattr(data, 'iloc') else None,
                "timestamp": str(data.index[-1]) if hasattr(data, 'index') else None
            }
        }
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/arbitrage")
async def check_arbitrage(request: ArbitrageRequest):
    """
    Check for arbitrage opportunities across timeframes.
    
    Detects:
    - Direction mismatches between timeframes
    - Confidence divergences
    - Internal arbitrage (15min vs 3x 5min)
    - Aligned signals for aggressive sizing
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        opportunities = await orchestrator.check_arbitrage(
            asset=request.asset,
            timeframes=request.timeframes
        )
        return {
            "asset": request.asset,
            "timeframes": request.timeframes,
            "opportunities_found": len(opportunities),
            "opportunities": opportunities
        }
    except Exception as e:
        logger.error(f"Arbitrage check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/llm/reasoning")
async def llm_reasoning(request: LLMReasoningRequest):
    """
    Get LLM reasoning for a specific task.
    
    Tasks:
    - analyze: Market analysis with prediction context
    - explain: Explain prediction reasoning
    - arbitrage: Analyze arbitrage opportunities
    - risk: Risk assessment advice
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if not orchestrator.llm_agent.available:
        raise HTTPException(status_code=503, detail="LLM agent not available (no API key)")
    
    try:
        result = await orchestrator.llm_agent.run(
            task=request.task,
            context={"asset": request.asset, **request.context}
        )
        return result
    except Exception as e:
        logger.error(f"LLM reasoning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents/run")
async def run_all_agents(background_tasks: BackgroundTasks):
    """Run full multi-asset agent cycle in background."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    background_tasks.add_task(orchestrator.run_multi_asset_cycle)
    return {
        "message": "Full multi-asset agent cycle started in background",
        "assets": orchestrator.assets,
        "timeframes": ["5m", "15m"]
    }


@app.get("/api/feedback")
async def get_feedback():
    """Get feedback agent learning statistics."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return orchestrator.get_feedback_stats()


@app.get("/api/assets")
async def get_assets():
    """Get list of tracked assets with configuration."""
    return {
        "assets": config.get("assets", []),
        "primary": ["BTC", "ETH"],
        "extended": ["SOL", "XRP", "ADA", "DOGE"]
    }


@app.get("/api/predictions/history")
async def get_prediction_history(asset: Optional[str] = None, limit: int = Query(default=50, ge=1, le=200)):
    """Get prediction history with optional asset filter."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    history = orchestrator.get_prediction_history(asset=asset)
    return {
        "asset": asset or "all",
        "count": len(history),
        "limit": limit,
        "predictions": history[-limit:]
    }


@app.get("/api/kronos/info")
async def get_kronos_info():
    """Get Kronos model information."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return orchestrator.prediction_agent.kronos.get_model_info()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if orchestrator else "initializing",
        "timestamp": datetime.utcnow().isoformat(),
        "agents_ready": orchestrator is not None
    }


# ==================== Main ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
