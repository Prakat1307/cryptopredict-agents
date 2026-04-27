"""
Feedback Agent - Hermes Agent loop feedback system.
Learns from prediction outcomes and adjusts agent behavior.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import numpy as np

from agents.base_agent import BaseAgent
from utils.helpers import timestamp_now, CircularBuffer


class FeedbackAgent(BaseAgent):
    """
    Agent responsible for the Hermes Agent learning loop.
    Tracks predictions, evaluates outcomes, and provides feedback
    to improve future predictions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("feedback", config)
        self.feedback_config = config.get("feedback", {})
        self.learning_rate = self.feedback_config.get("learning_rate", 0.1)
        self.memory_window = self.feedback_config.get("memory_window", 100)
        
        # Prediction history
        self.predictions = CircularBuffer(size=1000)
        self.outcomes = CircularBuffer(size=1000)
        
        # Performance tracking per asset/timeframe
        self.performance: Dict[str, Dict[str, Any]] = {}
        
        # Model weights for ensemble (adaptive)
        self.model_weights = {
            "trend": 0.33,
            "rsi": 0.33,
            "momentum": 0.34
        }
        
        # Register tools
        self.register_tool("evaluate_prediction", self._evaluate_prediction)
        self.register_tool("update_weights", self._update_weights)
        self.register_tool("generate_feedback", self._generate_feedback)
        self.register_tool("get_accuracy", self._get_accuracy)
    
    async def initialize(self):
        await super().initialize()
        self.logger.logger.info("FeedbackAgent initialized with learning loop")
    
    async def run(self, prediction: Dict[str, Any], actual_outcome: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Run feedback loop for a prediction.
        
        Args:
            prediction: The prediction that was made
            actual_outcome: The actual outcome ("up" or "down")
        
        Returns:
            Dict with feedback and learning updates
        """
        self.status = "running"
        self.last_run = timestamp_now()
        
        try:
            # Store prediction
            self.predictions.append(prediction)
            
            # If we have an outcome, evaluate
            if actual_outcome:
                eval_result = await self.execute_tool("evaluate_prediction", 
                                                       prediction=prediction, 
                                                       actual=actual_outcome)
                self.outcomes.append(eval_result)
                
                # Update weights
                await self.execute_tool("update_weights", evaluation=eval_result)
            
            # Generate feedback
            feedback = await self.execute_tool("generate_feedback")
            
            result = {
                "timestamp": timestamp_now(),
                "prediction_id": prediction.get("timestamp"),
                "feedback": feedback,
                "current_accuracy": await self.execute_tool("get_accuracy"),
                "model_weights": self.model_weights.copy()
            }
            
            self.add_to_memory({
                "action": "feedback",
                "prediction": prediction,
                "feedback": feedback
            })
            
            self.status = "idle"
            return result
            
        except Exception as e:
            self.status = "error"
            self.logger.log_error(e, {"prediction": prediction})
            raise
    
    async def _evaluate_prediction(self, prediction: Dict[str, Any], actual: str) -> Dict[str, Any]:
        """Evaluate a prediction against actual outcome."""
        predicted_direction = prediction.get("direction", "neutral")
        confidence = prediction.get("confidence", 0.5)
        
        correct = predicted_direction == actual
        
        # Brier score for probabilistic predictions
        predicted_prob = prediction.get("upside_probability", 0.5)
        actual_prob = 1.0 if actual == "up" else 0.0
        brier_score = (predicted_prob - actual_prob) ** 2
        
        # Log loss
        epsilon = 1e-15
        log_loss = -np.log(max(min(predicted_prob if actual == "up" else 1 - predicted_prob, 1 - epsilon), epsilon))
        
        result = {
            "prediction_id": prediction.get("timestamp"),
            "predicted": predicted_direction,
            "actual": actual,
            "correct": correct,
            "confidence": confidence,
            "brier_score": round(brier_score, 4),
            "log_loss": round(log_loss, 4),
            "timestamp": timestamp_now()
        }
        
        # Update performance tracking
        asset = prediction.get("asset", "unknown")
        timeframe = prediction.get("timeframe", "unknown")
        key = f"{asset}_{timeframe}"
        
        if key not in self.performance:
            self.performance[key] = {
                "total": 0,
                "correct": 0,
                "brier_scores": [],
                "confidences": []
            }
        
        self.performance[key]["total"] += 1
        if correct:
            self.performance[key]["correct"] += 1
        self.performance[key]["brier_scores"].append(brier_score)
        self.performance[key]["confidences"].append(confidence)
        
        return result
    
    async def _update_weights(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Update model weights based on evaluation."""
        # Get recent evaluations
        recent = self.outcomes.get_recent(20)
        
        if len(recent) < 5:
            return {"weights": self.model_weights, "updated": False}
        
        # Analyze which signals performed better
        # This is a simplified version - in production you'd track per-signal performance
        
        # If recent accuracy is good, slightly increase learning rate
        # If bad, decrease it
        recent_correct = sum(1 for e in recent if e.get("correct"))
        recent_accuracy = recent_correct / len(recent)
        
        if recent_accuracy > 0.6:
            # Doing well, can be slightly more aggressive
            self.learning_rate = min(self.learning_rate * 1.05, 0.3)
        elif recent_accuracy < 0.4:
            # Doing poorly, be more conservative
            self.learning_rate = max(self.learning_rate * 0.95, 0.01)
        
        return {
            "weights": self.model_weights,
            "learning_rate": self.learning_rate,
            "updated": True,
            "recent_accuracy": round(recent_accuracy, 4)
        }
    
    async def _generate_feedback(self) -> Dict[str, Any]:
        """Generate feedback summary for the agent loop."""
        accuracy = await self.execute_tool("get_accuracy")
        
        # Performance by asset/timeframe
        best_performers = []
        worst_performers = []
        
        for key, perf in self.performance.items():
            if perf["total"] > 5:
                acc = perf["correct"] / perf["total"]
                avg_brier = np.mean(perf["brier_scores"]) if perf["brier_scores"] else 1.0
                
                info = {
                    "key": key,
                    "accuracy": round(acc, 4),
                    "samples": perf["total"],
                    "avg_brier": round(avg_brier, 4)
                }
                
                if acc > 0.55:
                    best_performers.append(info)
                elif acc < 0.45:
                    worst_performers.append(info)
        
        # Sort by accuracy
        best_performers.sort(key=lambda x: x["accuracy"], reverse=True)
        worst_performers.sort(key=lambda x: x["accuracy"])
        
        return {
            "overall_accuracy": accuracy,
            "total_predictions": len(self.predictions.get_all()),
            "total_evaluated": len(self.outcomes.get_all()),
            "best_performers": best_performers[:5],
            "worst_performers": worst_performers[:5],
            "recommendations": self._generate_recommendations(best_performers, worst_performers, accuracy)
        }
    
    async def _get_accuracy(self) -> Dict[str, Any]:
        """Get overall accuracy metrics."""
        outcomes = self.outcomes.get_all()
        
        if not outcomes:
            return {"accuracy": None, "samples": 0, "brier": None}
        
        correct = sum(1 for o in outcomes if o.get("correct"))
        total = len(outcomes)
        accuracy = correct / total if total > 0 else 0
        
        brier_scores = [o.get("brier_score", 0) for o in outcomes]
        avg_brier = np.mean(brier_scores) if brier_scores else 1.0
        
        # Calibration
        high_conf_correct = sum(1 for o in outcomes if o.get("confidence", 0) > 0.7 and o.get("correct"))
        high_conf_total = sum(1 for o in outcomes if o.get("confidence", 0) > 0.7)
        calibration = high_conf_correct / high_conf_total if high_conf_total > 0 else 0
        
        return {
            "accuracy": round(accuracy, 4),
            "samples": total,
            "brier_score": round(avg_brier, 4),
            "calibration": round(calibration, 4),
            "high_conf_accuracy": round(high_conf_correct / high_conf_total, 4) if high_conf_total > 0 else None
        }
    
    def _generate_recommendations(self, best: List[Dict], worst: List[Dict], overall: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recs = []
        
        if best:
            recs.append(f"Focus on top performers: {', '.join(b['key'] for b in best[:3])}")
        
        if worst:
            recs.append(f"Review underperforming: {', '.join(w['key'] for w in worst[:3])}")
        
        if len(self.outcomes.get_all()) > 50:
            if overall["accuracy"] and overall["accuracy"] < 0.5:
                recs.append("Overall accuracy below 50% - consider strategy revision")
            if overall["calibration"] and overall["calibration"] < 0.6:
                recs.append("Poor calibration - confidence scores need adjustment")
        
        if not recs:
            recs.append("Continue current strategy - insufficient data for recommendations")
        
        return recs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get feedback statistics."""
        return {
            "predictions_stored": len(self.predictions.get_all()),
            "outcomes_stored": len(self.outcomes.get_all()),
            "performance_by_pair": self.performance,
            "current_weights": self.model_weights,
            "learning_rate": self.learning_rate
        }
