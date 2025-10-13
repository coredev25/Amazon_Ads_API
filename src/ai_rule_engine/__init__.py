"""
Amazon Ads AI Rule Engine
=========================

A Python-based automation system that adjusts bids and budgets according to 
ACOS, ROAS, and CTR rules with bid-floor/cap limits and negative-keyword logic.

Author: AI Assistant
Version: 1.0.0
"""

from .rule_engine import AIRuleEngine
from .rules import ACOSRule, ROASRule, CTRRule, NegativeKeywordRule
from .recommendations import RecommendationEngine
from .database import DatabaseConnector
from .config import RuleConfig

__version__ = "1.0.0"
__all__ = [
    "AIRuleEngine",
    "ACOSRule", 
    "ROASRule",
    "CTRRule",
    "NegativeKeywordRule",
    "RecommendationEngine",
    "DatabaseConnector",
    "RuleConfig"
]
