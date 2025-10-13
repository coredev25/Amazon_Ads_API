"""
Main AI Rule Engine implementation
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

from .config import RuleConfig
from .database import DatabaseConnector
from .rules import ACOSRule, ROASRule, CTRRule, NegativeKeywordRule, BudgetRule
from .recommendations import RecommendationEngine, Recommendation


class AIRuleEngine:
    """Main AI Rule Engine for Amazon Ads bid and budget automation"""
    
    def __init__(self, config: RuleConfig, db_connector: DatabaseConnector):
        """
        Initialize the AI Rule Engine
        
        Args:
            config: Rule configuration
            db_connector: Database connector for data retrieval
        """
        self.config = config
        self.db = db_connector
        self.logger = logging.getLogger(__name__)
        
        # Initialize rules
        self.rules = {
            'acos': ACOSRule(config.__dict__),
            'roas': ROASRule(config.__dict__),
            'ctr': CTRRule(config.__dict__),
            'negative_keyword': NegativeKeywordRule(config.__dict__),
            'budget': BudgetRule(config.__dict__)
        }
        
        # Initialize recommendation engine
        self.recommendation_engine = RecommendationEngine(config)
        
        # Track recent adjustments for cooldown enforcement
        self.recent_adjustments = {}
    
    def analyze_campaigns(self, campaign_ids: Optional[List[int]] = None) -> List[Recommendation]:
        """
        Analyze campaigns and generate recommendations
        
        Args:
            campaign_ids: List of campaign IDs to analyze (None for all)
            
        Returns:
            List of recommendations
        """
        self.logger.info("Starting campaign analysis")
        
        # Get campaigns to analyze
        if campaign_ids:
            campaigns = []
            for campaign_id in campaign_ids:
                campaign_data = self._get_campaign_data(campaign_id)
                if campaign_data:
                    campaigns.append(campaign_data)
        else:
            campaigns = self.db.get_campaigns_with_performance(
                self.config.performance_lookback_days
            )
        
        all_recommendations = []
        
        for campaign in campaigns:
            campaign_id = campaign['campaign_id']
            self.logger.info(f"Analyzing campaign {campaign_id}: {campaign['campaign_name']}")
            
            # Analyze campaign level
            campaign_recs = self._analyze_entity(
                'campaign', campaign_id, campaign, 
                self.db.get_campaign_performance(campaign_id, self.config.performance_lookback_days)
            )
            all_recommendations.extend(campaign_recs)
            
            # Analyze ad groups
            ad_groups = self.db.get_ad_groups_with_performance(
                campaign_id, self.config.performance_lookback_days
            )
            
            for ad_group in ad_groups:
                ad_group_id = ad_group['ad_group_id']
                ad_group_recs = self._analyze_entity(
                    'ad_group', ad_group_id, ad_group,
                    self.db.get_ad_group_performance(ad_group_id, self.config.performance_lookback_days)
                )
                all_recommendations.extend(ad_group_recs)
                
                # Analyze keywords
                keywords = self.db.get_keywords_with_performance(
                    ad_group_id, self.config.performance_lookback_days
                )
                
                for keyword in keywords:
                    keyword_id = keyword['keyword_id']
                    keyword_recs = self._analyze_entity(
                        'keyword', keyword_id, keyword,
                        self.db.get_keyword_performance(keyword_id, self.config.performance_lookback_days)
                    )
                    all_recommendations.extend(keyword_recs)
        
        # Filter and prioritize recommendations
        filtered_recs = self.recommendation_engine.filter_recommendations(
            all_recommendations,
            max_recommendations=100,
            min_confidence=0.3
        )
        
        self.logger.info(f"Generated {len(filtered_recs)} recommendations from {len(all_recommendations)} total")
        
        return filtered_recs
    
    def _analyze_entity(self, entity_type: str, entity_id: int, 
                       entity_info: Dict[str, Any], 
                       performance_data: List[Dict[str, Any]]) -> List[Recommendation]:
        """
        Analyze a single entity (campaign, ad group, or keyword)
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            entity_info: Entity information
            performance_data: Performance data for the entity
            
        Returns:
            List of recommendations for this entity
        """
        if not performance_data:
            return []
        
        # Check cooldown period
        if self._is_in_cooldown(entity_type, entity_id):
            self.logger.debug(f"Entity {entity_type} {entity_id} is in cooldown period")
            return []
        
        # Prepare entity info for rules
        entity_data = {
            'id': entity_id,
            'entity_type': entity_type,
            'name': entity_info.get('campaign_name', entity_info.get('ad_group_name', entity_info.get('keyword_text', ''))),
            'bid': entity_info.get('bid', entity_info.get('default_bid', 0)),
            'budget_amount': entity_info.get('budget_amount', 0)
        }
        entity_data.update(entity_info)
        
        # Evaluate all rules
        rule_results = []
        for rule_name, rule in self.rules.items():
            try:
                result = rule.evaluate(performance_data, entity_data)
                if result:
                    rule_results.append(result)
                    self.logger.debug(f"Rule {rule_name} triggered for {entity_type} {entity_id}: {result.reason}")
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule_name} for {entity_type} {entity_id}: {e}")
        
        # Generate recommendations
        if rule_results:
            recommendations = self.recommendation_engine.generate_recommendations(
                rule_results, {entity_id: entity_data}
            )
            
            # Record adjustment for cooldown tracking
            if recommendations:
                self._record_adjustment(entity_type, entity_id)
            
            return recommendations
        
        return []
    
    def _get_campaign_data(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        """Get campaign data by ID"""
        campaigns = self.db.get_campaigns_with_performance(self.config.performance_lookback_days)
        for campaign in campaigns:
            if campaign['campaign_id'] == campaign_id:
                return campaign
        return None
    
    def _is_in_cooldown(self, entity_type: str, entity_id: int) -> bool:
        """Check if entity is in cooldown period"""
        key = f"{entity_type}_{entity_id}"
        if key not in self.recent_adjustments:
            return False
        
        last_adjustment = self.recent_adjustments[key]
        cooldown_duration = timedelta(hours=self.config.cooldown_hours)
        
        return datetime.now() - last_adjustment < cooldown_duration
    
    def _record_adjustment(self, entity_type: str, entity_id: int) -> None:
        """Record an adjustment for cooldown tracking"""
        key = f"{entity_type}_{entity_id}"
        self.recent_adjustments[key] = datetime.now()
    
    def get_recommendations_summary(self, recommendations: List[Recommendation]) -> Dict[str, Any]:
        """Get summary of recommendations"""
        return self.recommendation_engine.generate_summary(recommendations)
    
    def export_recommendations(self, recommendations: List[Recommendation], 
                             output_path: str, format: str = 'json') -> None:
        """
        Export recommendations to file
        
        Args:
            recommendations: List of recommendations
            output_path: Output file path
            format: Output format ('json', 'csv')
        """
        if format == 'json':
            self._export_json(recommendations, output_path)
        elif format == 'csv':
            self._export_csv(recommendations, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(self, recommendations: List[Recommendation], output_path: str) -> None:
        """Export recommendations as JSON"""
        data = {
            'exported_at': datetime.now().isoformat(),
            'total_recommendations': len(recommendations),
            'summary': self.get_recommendations_summary(recommendations),
            'recommendations': []
        }
        
        for rec in recommendations:
            rec_data = {
                'entity_type': rec.entity_type,
                'entity_id': rec.entity_id,
                'entity_name': rec.entity_name,
                'adjustment_type': rec.adjustment_type,
                'current_value': rec.current_value,
                'recommended_value': rec.recommended_value,
                'adjustment_amount': rec.adjustment_amount,
                'adjustment_percentage': rec.adjustment_percentage,
                'priority': rec.priority,
                'confidence': rec.confidence,
                'reason': rec.reason,
                'rules_triggered': rec.rules_triggered,
                'metadata': rec.metadata,
                'created_at': rec.created_at.isoformat()
            }
            data['recommendations'].append(rec_data)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Exported {len(recommendations)} recommendations to {output_path}")
    
    def _export_csv(self, recommendations: List[Recommendation], output_path: str) -> None:
        """Export recommendations as CSV"""
        import csv
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Entity Type', 'Entity ID', 'Entity Name', 'Adjustment Type',
                'Current Value', 'Recommended Value', 'Adjustment Amount',
                'Adjustment Percentage', 'Priority', 'Confidence', 'Reason',
                'Rules Triggered', 'Created At'
            ])
            
            # Write data
            for rec in recommendations:
                writer.writerow([
                    rec.entity_type,
                    rec.entity_id,
                    rec.entity_name,
                    rec.adjustment_type,
                    rec.current_value,
                    rec.recommended_value,
                    rec.adjustment_amount,
                    rec.adjustment_percentage,
                    rec.priority,
                    rec.confidence,
                    rec.reason,
                    '; '.join(rec.rules_triggered),
                    rec.created_at.isoformat()
                ])
        
        self.logger.info(f"Exported {len(recommendations)} recommendations to {output_path}")
    
    def get_rule_documentation(self) -> Dict[str, Any]:
        """Get documentation for all rules"""
        return {
            'acos_rule': {
                'description': 'Adjusts bids based on Advertising Cost of Sales (ACOS)',
                'target': f"{self.config.acos_target:.1%}",
                'tolerance': f"±{self.config.acos_tolerance:.1%}",
                'adjustment_factor': f"{self.config.acos_bid_adjustment_factor:.1%}",
                'triggers': [
                    f"ACOS exceeds {self.config.acos_target + self.config.acos_tolerance:.1%} (reduce bid)",
                    f"ACOS below {self.config.acos_target - self.config.acos_tolerance:.1%} (increase bid)"
                ]
            },
            'roas_rule': {
                'description': 'Adjusts bids based on Return on Ad Spend (ROAS)',
                'target': f"{self.config.roas_target:.1f}:1",
                'tolerance': f"±{self.config.roas_tolerance:.1f}",
                'adjustment_factor': f"{self.config.roas_bid_adjustment_factor:.1%}",
                'triggers': [
                    f"ROAS below {self.config.roas_target - self.config.roas_tolerance:.1f}:1 (reduce bid)",
                    f"ROAS above {self.config.roas_target + self.config.roas_tolerance:.1f}:1 (increase bid)"
                ]
            },
            'ctr_rule': {
                'description': 'Adjusts bids based on Click-Through Rate (CTR)',
                'minimum': f"{self.config.ctr_minimum:.1f}%",
                'target': f"{self.config.ctr_target:.1f}%",
                'adjustment_factor': f"{self.config.ctr_bid_adjustment_factor:.1%}",
                'triggers': [
                    f"CTR below {self.config.ctr_minimum:.1f}% (increase bid)"
                ]
            },
            'negative_keyword_rule': {
                'description': 'Identifies keywords for negative keyword lists',
                'ctr_threshold': f"{self.config.negative_keyword_ctr_threshold:.1f}%",
                'impression_threshold': f"{self.config.negative_keyword_impression_threshold:,}",
                'triggers': [
                    f"CTR below {self.config.negative_keyword_ctr_threshold:.1f}% with {self.config.negative_keyword_impression_threshold:,}+ impressions"
                ]
            },
            'budget_rule': {
                'description': 'Adjusts daily budgets based on performance',
                'adjustment_factor': f"{self.config.budget_adjustment_factor:.1%}",
                'min_daily': f"${self.config.budget_min_daily:.2f}",
                'max_daily': f"${self.config.budget_max_daily:.2f}",
                'triggers': [
                    "ROAS above 3:1 (increase budget)",
                    "ROAS below 1.5:1 (decrease budget)"
                ]
            },
            'bid_limits': {
                'floor': f"${self.config.bid_floor:.2f}",
                'cap': f"${self.config.bid_cap:.2f}",
                'max_adjustment': f"{self.config.bid_max_adjustment:.1%}"
            },
            'safety_limits': {
                'max_daily_adjustments': self.config.max_daily_adjustments,
                'cooldown_hours': self.config.cooldown_hours,
                'min_impressions': self.config.min_impressions,
                'min_clicks': self.config.min_clicks,
                'min_conversions': self.config.min_conversions
            }
        }
