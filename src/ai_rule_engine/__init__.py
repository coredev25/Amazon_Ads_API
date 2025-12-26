"""
Amazon Ads AI Rule Engine
=========================

A Python-based automation system that adjusts bids and budgets according to 
ACOS, ROAS, and CTR rules with bid-floor/cap limits and negative-keyword logic.

Author: AI Assistant
Version: 1.0.0
"""

from .rule_engine import AIRuleEngine
from .rules import ACOSRule, ROASRule, CTRRule, NegativeKeywordRule, BudgetRule
from .recommendations import RecommendationEngine, Recommendation
from .database import DatabaseConnector
from .config import RuleConfig
from .intelligence_engines import (
    IntelligenceOrchestrator,
    DataIntelligenceEngine,
    KeywordIntelligenceEngine,
    LongTailEngine,
    RankingEngine,
    SeasonalityEngine,
    ProfitEngine
)
from .negative_manager import NegativeKeywordManager, NegativeKeywordCandidate
from .bid_optimizer import BidOptimizationEngine, BudgetOptimizationEngine
from .learning_loop import LearningLoop, ModelTrainer
from .re_entry_control import ReEntryController, BidChangeTracker, ReEntryControlResult, OscillationDetectionResult
# Advanced Features (#26-30) - Import conditionally
try:
    from .advanced_models import TimeSeriesModelTrainer, CausalInferenceModel
except ImportError:
    TimeSeriesModelTrainer = None
    CausalInferenceModel = None

try:
    from .bandit_models import ThompsonSamplingBandit, UCBBandit, CounterfactualEvaluator
except ImportError:
    ThompsonSamplingBandit = None
    UCBBandit = None
    CounterfactualEvaluator = None

try:
    from .portfolio_learning import PortfolioLearningEngine, PrivacyController
except ImportError:
    PortfolioLearningEngine = None
    PrivacyController = None

try:
    from .explainability import ModelExplainer
except ImportError:
    ModelExplainer = None

try:
    from .simulator import HistoricalSimulator
except ImportError:
    HistoricalSimulator = None

__version__ = "2.2.0"
__all__ = [
    # Core Engine
    "AIRuleEngine",
    # Traditional Rules
    "ACOSRule", 
    "ROASRule",
    "CTRRule",
    "NegativeKeywordRule",
    "BudgetRule",
    # Recommendation System
    "RecommendationEngine",
    "Recommendation",
    # Database
    "DatabaseConnector",
    # Configuration
    "RuleConfig",
    # Intelligence Engines
    "IntelligenceOrchestrator",
    "DataIntelligenceEngine",
    "KeywordIntelligenceEngine",
    "LongTailEngine",
    "RankingEngine",
    "SeasonalityEngine",
    "ProfitEngine",
    # Negative Keyword Management
    "NegativeKeywordManager",
    "NegativeKeywordCandidate",
    # Bid Optimization
    "BidOptimizationEngine",
    "BudgetOptimizationEngine",
    # Learning Loop
    "LearningLoop",
    "ModelTrainer",
    # Re-entry Control & Oscillation Prevention
    "ReEntryController",
    "BidChangeTracker",
    "ReEntryControlResult",
    "OscillationDetectionResult",
    # Advanced Models (#26)
    "TimeSeriesModelTrainer",
    "CausalInferenceModel",
    # Multi-Armed Bandits (#27)
    "ThompsonSamplingBandit",
    "UCBBandit",
    "CounterfactualEvaluator",
    # Portfolio Learning (#28)
    "PortfolioLearningEngine",
    "PrivacyController",
    # Explainability (#29)
    "ModelExplainer",
    # Simulator (#30)
    "HistoricalSimulator"
]
