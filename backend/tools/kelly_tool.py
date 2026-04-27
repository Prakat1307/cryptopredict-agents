"""
Hermes Agent Tool - Kelly Criterion Calculator
Position sizing using Kelly formula for prediction markets.
"""

import json
from typing import Dict, Any


class KellyTool:
    """Tool for Kelly Criterion position sizing."""
    
    def calculate(self, probability: float, odds: float, bankroll: float = 1000.0, 
                  fraction: float = 0.5) -> str:
        """
        Calculate Kelly Criterion position size.
        
        Args:
            probability: Probability of winning (0-1)
            odds: Decimal odds (profit per unit staked)
            bankroll: Total bankroll
            fraction: Kelly fraction to use (0.5 = half Kelly)
        """
        try:
            q = 1 - probability
            
            if odds <= 0:
                return json.dumps({
                    "success": False,
                    "error": "Odds must be positive"
                })
            
            # Kelly fraction
            kelly_f = (odds * probability - q) / odds
            kelly_f = max(0, min(kelly_f, 0.25))  # Cap at 25%
            
            # Position sizes
            full_kelly = bankroll * kelly_f
            half_kelly = bankroll * kelly_f * fraction
            
            return json.dumps({
                "success": True,
                "kelly_fraction": round(kelly_f, 4),
                "full_kelly": round(full_kelly, 2),
                "recommended": round(half_kelly, 2),
                "win_probability": round(probability, 4),
                "odds": round(odds, 4),
                "bankroll": bankroll
            })
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def batch_calculate(self, opportunities: list, bankroll: float = 1000.0) -> str:
        """Calculate Kelly for multiple opportunities."""
        results = []
        
        for opp in opportunities:
            prob = opp.get("probability", 0.5)
            odds = opp.get("odds", 1.0)
            
            result = json.loads(self.calculate(prob, odds, bankroll))
            result["opportunity"] = opp.get("name", "unknown")
            results.append(result)
        
        return json.dumps({
            "success": True,
            "opportunities": results,
            "total_recommended": sum(r.get("recommended", 0) for r in results)
        })


KELLY_TOOL_SCHEMA = {
    "name": "kelly_calculate",
    "description": "Calculate optimal position size using Kelly Criterion",
    "parameters": {
        "type": "object",
        "properties": {
            "probability": {
                "type": "number",
                "description": "Probability of winning (0-1)"
            },
            "odds": {
                "type": "number",
                "description": "Decimal odds"
            },
            "bankroll": {
                "type": "number",
                "description": "Total bankroll",
                "default": 1000.0
            },
            "fraction": {
                "type": "number",
                "description": "Kelly fraction (0.5 = half Kelly)",
                "default": 0.5
            }
        },
        "required": ["probability", "odds"]
    }
}
