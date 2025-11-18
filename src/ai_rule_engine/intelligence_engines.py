"""
Intelligence Engines for AI Rule Engine
Implements: Keyword Intelligence, Long-Tail, Ranking, Seasonality, Profit Engines
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
from collections import defaultdict


@dataclass
class IntelligenceSignal:
    """Signal from an intelligence engine"""
    engine_name: str
    entity_type: str
    entity_id: int
    signal_type: str  # 'opportunity', 'warning', 'optimization'
    strength: float  # 0.0 to 1.0
    recommendation: str
    metadata: Dict[str, Any]


class DataIntelligenceEngine:
    """Preprocesses and analyzes Amazon Ads data for quality and insights"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def analyze_data_quality(self, performance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze data quality and completeness"""
        if not performance_data:
            return {
                'quality_score': 0.0,
                'completeness': 0.0,
                'issues': ['No performance data available'],
                'usable': False
            }
        
        total_records = len(performance_data)
        complete_records = 0
        missing_fields = defaultdict(int)
        
        required_fields = ['impressions', 'clicks', 'cost', 'attributed_sales_7d']
        
        for record in performance_data:
            is_complete = True
            for field in required_fields:
                if field not in record or record[field] is None:
                    missing_fields[field] += 1
                    is_complete = False
            
            if is_complete:
                complete_records += 1
        
        completeness = complete_records / total_records if total_records > 0 else 0
        quality_score = completeness * 100
        
        issues = []
        for field, count in missing_fields.items():
            if count > 0:
                issues.append(f"Missing {field} in {count}/{total_records} records")
        
        return {
            'quality_score': quality_score,
            'completeness': completeness,
            'total_records': total_records,
            'complete_records': complete_records,
            'issues': issues,
            'usable': quality_score >= 70.0
        }


class KeywordIntelligenceEngine:
    """Analyzes keyword performance and identifies optimization opportunities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.min_impressions = config.get('min_impressions', 100)
        self.high_performer_threshold = config.get('high_performer_roas', 5.0)
    
    def analyze_keyword_performance(self, keyword_data: Dict[str, Any], 
                                   performance_data: List[Dict[str, Any]]) -> Optional[IntelligenceSignal]:
        """Analyze individual keyword performance"""
        if not performance_data:
            return None
        
        total_impressions = sum(float(record.get('impressions', 0)) for record in performance_data)
        total_clicks = sum(float(record.get('clicks', 0)) for record in performance_data)
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        
        if total_impressions < self.min_impressions:
            return None
        
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        roas = (total_sales / total_cost) if total_cost > 0 else 0
        
        # Identify high performers
        if roas >= self.high_performer_threshold and ctr >= 1.0:
            return IntelligenceSignal(
                engine_name='KeywordIntelligence',
                entity_type='keyword',
                entity_id=keyword_data.get('id', 0),
                signal_type='opportunity',
                strength=min(1.0, roas / self.high_performer_threshold),
                recommendation=f"High-performing keyword (ROAS: {roas:.2f}, CTR: {ctr:.2f}%) - consider increasing budget",
                metadata={'roas': roas, 'ctr': ctr, 'impressions': total_impressions, 'sales': total_sales}
            )
        
        return None


class LongTailEngine:
    """Identifies long-tail keyword opportunities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.min_word_count = config.get('long_tail_min_words', 3)
        self.target_roas = config.get('roas_target', 11.11)
    
    def identify_long_tail_opportunities(self, keyword_data: Dict[str, Any],
                                        performance_data: List[Dict[str, Any]]) -> Optional[IntelligenceSignal]:
        """Identify long-tail keyword opportunities"""
        keyword_text = keyword_data.get('keyword_text', '')
        word_count = len(keyword_text.split())
        
        if word_count < self.min_word_count:
            return None
        
        if not performance_data:
            return None
        
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        total_impressions = sum(float(record.get('impressions', 0)) for record in performance_data)
        
        if total_cost == 0:
            return None
        
        roas = total_sales / total_cost if total_cost > 0 else 0
        
        # Long-tail keywords often have lower volume but higher conversion
        if roas > self.target_roas * 1.2 and total_impressions < 500:
            return IntelligenceSignal(
                engine_name='LongTail',
                entity_type='keyword',
                entity_id=keyword_data.get('id', 0),
                signal_type='opportunity',
                strength=0.8,
                recommendation=f"High-value long-tail keyword ({word_count} words, ROAS: {roas:.2f}) - consider scaling",
                metadata={'keyword_text': keyword_text, 'word_count': word_count, 'roas': roas, 'impressions': total_impressions}
            )
        
        return None


class RankingEngine:
    """Analyzes keyword ranking and position trends"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.target_impression_share = config.get('target_impression_share', 0.5)
    
    def analyze_ranking_trends(self, keyword_data: Dict[str, Any],
                              performance_data: List[Dict[str, Any]]) -> Optional[IntelligenceSignal]:
        """Analyze ranking and impression share trends"""
        if len(performance_data) < 3:
            return None
        
        # Calculate impression share trend
        recent_impressions = [float(record.get('impressions', 0)) for record in performance_data[-7:]]
        earlier_impressions = [float(record.get('impressions', 0)) for record in performance_data[:7]]
        
        recent_avg = statistics.mean(recent_impressions) if recent_impressions else 0
        earlier_avg = statistics.mean(earlier_impressions) if earlier_impressions else 0
        
        if earlier_avg == 0:
            return None
        
        change_rate = (recent_avg - earlier_avg) / earlier_avg
        
        # Significant decline in impressions suggests ranking drop
        if change_rate < -0.3:
            return IntelligenceSignal(
                engine_name='Ranking',
                entity_type='keyword',
                entity_id=keyword_data.get('id', 0),
                signal_type='warning',
                strength=min(1.0, abs(change_rate)),
                recommendation=f"Impression volume declining ({change_rate*100:.1f}%) - may indicate ranking drop",
                metadata={'change_rate': change_rate, 'recent_avg_impressions': recent_avg, 'earlier_avg_impressions': earlier_avg}
            )
        
        return None


class SeasonalityEngine:
    """Accounts for seasonal trends and adjusts recommendations accordingly"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.seasonal_boost_factor = config.get('seasonal_boost_factor', 1.5)
    
    def detect_seasonality(self, performance_data: List[Dict[str, Any]],
                          current_date: Optional[datetime] = None) -> Optional[IntelligenceSignal]:
        """Detect seasonal patterns and current season"""
        if not current_date:
            current_date = datetime.now()
        
        month = current_date.month
        day = current_date.day
        
        # Define peak seasons for e-commerce
        peak_seasons = {
            'holiday': [(11, 15, 12, 31)],  # Black Friday to New Year
            'back_to_school': [(8, 1, 9, 15)],
            'summer': [(6, 1, 7, 31)],
            'spring': [(3, 15, 5, 15)]
        }
        
        current_season = None
        for season_name, periods in peak_seasons.items():
            for start_month, start_day, end_month, end_day in periods:
                if (month > start_month or (month == start_month and day >= start_day)) and \
                   (month < end_month or (month == end_month and day <= end_day)):
                    current_season = season_name
                    break
        
        if current_season:
            return IntelligenceSignal(
                engine_name='Seasonality',
                entity_type='campaign',
                entity_id=0,
                signal_type='optimization',
                strength=0.9,
                recommendation=f"Currently in {current_season} season - consider increasing budgets and bids by {(self.seasonal_boost_factor-1)*100:.0f}%",
                metadata={'season': current_season, 'boost_factor': self.seasonal_boost_factor, 'month': month, 'day': day}
            )
        
        return None


class ProfitEngine:
    """Optimizes for profit margins rather than just ROAS"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.target_profit_margin = config.get('target_profit_margin', 0.30)  # 30%
        self.min_profit_threshold = config.get('min_profit_threshold', 0.15)  # 15%
    
    def analyze_profitability(self, entity_data: Dict[str, Any],
                             performance_data: List[Dict[str, Any]],
                             product_cost_percentage: float = 0.40) -> Optional[IntelligenceSignal]:
        """Analyze profitability and generate signals"""
        if not performance_data:
            return None
        
        total_sales = sum(float(record.get('attributed_sales_7d', 0)) for record in performance_data)
        total_ad_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        
        if total_sales == 0:
            return None
        
        # Estimate product costs
        total_product_cost = total_sales * product_cost_percentage
        
        # Calculate profit
        gross_profit = total_sales - total_ad_cost - total_product_cost
        profit_margin = (gross_profit / total_sales) if total_sales > 0 else 0
        
        # Low profit margin warning
        if profit_margin < self.min_profit_threshold:
            return IntelligenceSignal(
                engine_name='Profit',
                entity_type=entity_data.get('entity_type', 'unknown'),
                entity_id=entity_data.get('id', 0),
                signal_type='warning',
                strength=0.9,
                recommendation=f"Low profit margin ({profit_margin*100:.1f}%) - reduce ad spend or increase prices",
                metadata={'profit_margin': profit_margin, 'gross_profit': gross_profit}
            )
        
        return None


class IntelligenceOrchestrator:
    """Orchestrates all intelligence engines and combines their signals"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize all engines
        self.data_intelligence = DataIntelligenceEngine(config)
        self.keyword_intelligence = KeywordIntelligenceEngine(config)
        self.long_tail = LongTailEngine(config)
        self.ranking = RankingEngine(config)
        self.seasonality = SeasonalityEngine(config)
        self.profit = ProfitEngine(config)
    
    def analyze_entity(self, entity_data: Dict[str, Any],
                      performance_data: List[Dict[str, Any]]) -> List[IntelligenceSignal]:
        """Run all intelligence engines on an entity"""
        signals = []
        
        # Check data quality first
        quality = self.data_intelligence.analyze_data_quality(performance_data)
        if not quality['usable']:
            self.logger.warning(f"Data quality issues for entity {entity_data.get('id')}: {quality['issues']}")
            return signals
        
        entity_type = entity_data.get('entity_type', 'unknown')
        
        # Run keyword-specific engines
        if entity_type == 'keyword':
            signal = self.keyword_intelligence.analyze_keyword_performance(entity_data, performance_data)
            if signal:
                signals.append(signal)
            
            signal = self.long_tail.identify_long_tail_opportunities(entity_data, performance_data)
            if signal:
                signals.append(signal)
            
            signal = self.ranking.analyze_ranking_trends(entity_data, performance_data)
            if signal:
                signals.append(signal)
        
        # Run profit analysis for all entities
        signal = self.profit.analyze_profitability(entity_data, performance_data)
        if signal:
            signals.append(signal)
        
        # Check seasonality (campaign level)
        if entity_type == 'campaign':
            signal = self.seasonality.detect_seasonality(performance_data)
            if signal:
                signals.append(signal)
        
        return signals
    
    def combine_signals(self, signals: List[IntelligenceSignal]) -> Dict[str, Any]:
        """Combine multiple intelligence signals into actionable insights"""
        if not signals:
            return {
                'total_signals': 0,
                'opportunities': 0,
                'warnings': 0,
                'optimizations': 0,
                'recommended_actions': []
            }
        
        opportunities = [s for s in signals if s.signal_type == 'opportunity']
        warnings = [s for s in signals if s.signal_type == 'warning']
        optimizations = [s for s in signals if s.signal_type == 'optimization']
        
        # Sort by strength
        opportunities.sort(key=lambda s: s.strength, reverse=True)
        warnings.sort(key=lambda s: s.strength, reverse=True)
        
        recommended_actions = []
        for signal in opportunities[:3]:  # Top 3 opportunities
            recommended_actions.append({
                'type': 'opportunity',
                'action': signal.recommendation,
                'strength': signal.strength,
                'engine': signal.engine_name
            })
        
        for signal in warnings[:3]:  # Top 3 warnings
            recommended_actions.append({
                'type': 'warning',
                'action': signal.recommendation,
                'strength': signal.strength,
                'engine': signal.engine_name
            })
        
        return {
            'total_signals': len(signals),
            'opportunities': len(opportunities),
            'warnings': len(warnings),
            'optimizations': len(optimizations),
            'recommended_actions': recommended_actions,
            'all_signals': signals
        }
