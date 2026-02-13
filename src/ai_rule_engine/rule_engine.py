"""
Main AI Rule Engine implementation
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .config import RuleConfig
from .database import DatabaseConnector
from .rules import ACOSRule, ROASRule, CTRRule, NegativeKeywordRule, BudgetRule
from .recommendations import RecommendationEngine, Recommendation
from .intelligence_engines import IntelligenceOrchestrator
from .negative_manager import SmartNegativeKeywordManager
from .bid_optimizer import BidOptimizationEngine, BudgetOptimizationEngine
from .learning_loop import LearningLoop, ModelTrainer
from .telemetry import TelemetryClient


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
        self.telemetry = TelemetryClient(config.__dict__)
        
        # Initialize traditional rules
        self.rules = {
            'acos': ACOSRule(config.__dict__),
            'roas': ROASRule(config.__dict__),
            'ctr': CTRRule(config.__dict__),
            'negative_keyword': NegativeKeywordRule(config.__dict__),
            'budget': BudgetRule(config.__dict__)
        }
        
        # Initialize recommendation engine
        self.recommendation_engine = RecommendationEngine(config)
        
        # Initialize intelligence engines (if enabled)
        if config.enable_intelligence_engines:
            self.intelligence_orchestrator = IntelligenceOrchestrator(config.__dict__)
            self.logger.info("Intelligence engines initialized")
        else:
            self.intelligence_orchestrator = None
        
        # Initialize negative keyword manager
        # Pass db_connector in config so waste patterns can be loaded from database
        negative_config = config.__dict__.copy()
        negative_config['db_connector'] = db_connector
        self.negative_manager = SmartNegativeKeywordManager(negative_config)
        
        # Initialize learning loop (if enabled) - must be before bid optimizer
        if config.enable_learning_loop:
            self.learning_loop = LearningLoop(config.__dict__, db_connector, telemetry=self.telemetry)  # FIX #1: Pass db_connector
            self.model_trainer = ModelTrainer(config.__dict__, db_connector, telemetry=self.telemetry)  # FIX #21: Pass telemetry
            self.logger.info("Learning loop enabled")
        else:
            self.learning_loop = None
            self.model_trainer = None
        
        # Initialize bid optimization engine with model_trainer and learning_loop (if enabled)
        if config.enable_advanced_bid_optimization:
            self.bid_optimizer = BidOptimizationEngine(
                config.__dict__, 
                db_connector,
                model_trainer=self.model_trainer,  # For STEP 5: Predictive gating
                learning_loop=self.learning_loop,   # For STEP 7: Campaign adaptivity
                telemetry=self.telemetry
            )
            self.budget_optimizer = BudgetOptimizationEngine(config.__dict__)
            self.logger.info("Advanced bid optimization enabled with re-entry control and learning loop")
        else:
            self.bid_optimizer = None
            self.budget_optimizer = None
        
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
                portfolio_id = campaign.get('portfolio_id')
                portfolio_name = campaign.get('portfolio_name')
                ad_group_with_portfolio = {
                    **ad_group,
                    'campaign_id': campaign_id,
                    'campaign_name': campaign.get('campaign_name'),
                    'portfolio_id': portfolio_id,
                    'portfolio_name': portfolio_name
                }
                ad_group_recs = self._analyze_entity(
                    'ad_group', ad_group_id, ad_group_with_portfolio,
                    self.db.get_ad_group_performance(ad_group_id, self.config.performance_lookback_days)
                )
                all_recommendations.extend(ad_group_recs)
                
                # Analyze keywords
                keywords = self.db.get_keywords_with_performance(
                    ad_group_id, self.config.performance_lookback_days
                )
                
                for keyword in keywords:
                    keyword_id = keyword['keyword_id']
                    keyword_with_portfolio = {
                        **keyword,
                        'campaign_id': campaign_id,
                        'campaign_name': campaign.get('campaign_name'),
                        'ad_group_id': ad_group_id,
                        'ad_group_name': ad_group.get('ad_group_name'),
                        'portfolio_id': portfolio_id,
                        'portfolio_name': portfolio_name
                    }
                    keyword_recs = self._analyze_entity(
                        'keyword', keyword_id, keyword_with_portfolio,
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
        
        # Save all recommendations to database for real-time updates
        try:
            self._save_all_recommendations(filtered_recs)
        except Exception as e:
            self.logger.error(f"Error in _save_all_recommendations: {e}", exc_info=True)
        
        # Observability: Track recommendations per day (#21)
        self.telemetry.gauge('ai_rule_engine_recommendations', len(filtered_recs))
        self.telemetry.increment(
            'ai_rule_engine_recommendations_daily',
            value=len(filtered_recs),
            labels={'date': datetime.now().strftime('%Y-%m-%d')}
        )
        
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
        
        # Run intelligence engines if enabled
        intelligence_signals = []
        if self.intelligence_orchestrator:
            try:
                intelligence_signals = self.intelligence_orchestrator.analyze_entity(
                    entity_data, performance_data
                )
                if intelligence_signals:
                    self.logger.debug(f"Intelligence engines generated {len(intelligence_signals)} signals for {entity_type} {entity_id}")
            except Exception as e:
                self.logger.error(f"Error running intelligence engines for {entity_type} {entity_id}: {e}")
        
        # Use advanced bid optimization if enabled
        # FIX: Prevent "Double Dip" - Only run AI optimizer OR traditional rules, not both
        ai_recommendation = None
        if self.bid_optimizer and entity_type in ['keyword', 'ad_group']:
            try:
                bid_optimization = self.bid_optimizer.calculate_optimal_bid(
                    entity_data, performance_data, intelligence_signals
                )
                
                if bid_optimization:
                    # Log bid change to database for re-entry control tracking
                    if self.bid_optimizer:
                        # Calculate current metrics for logging
                        total_cost = sum(float(p.get('cost', 0)) for p in performance_data)
                        total_sales = sum(float(p.get('attributed_sales_7d', 0)) for p in performance_data)
                        total_impressions = sum(float(p.get('impressions', 0)) for p in performance_data)
                        total_clicks = sum(float(p.get('clicks', 0)) for p in performance_data)
                        total_conversions = sum(int(p.get('attributed_conversions_7d', 0)) for p in performance_data)
                        
                        current_metrics = {
                            'acos': (total_cost / total_sales) if total_sales > 0 else 0,
                            'roas': (total_sales / total_cost) if total_cost > 0 else 0,
                            'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                            'conversions': total_conversions
                        }
                        
                        try:
                            # STEP 1: Log bid change with performance_before for learning loop
                            self.bid_optimizer.log_bid_change(
                                bid_optimization, 
                                current_metrics,
                                performance_data=performance_data,  # Pass raw performance data for fallback
                                performance_snapshot=bid_optimization.metadata.get('performance_snapshot')
                            )
                        except Exception as e:
                            self.logger.error(f"Error logging bid change: {e}")
                    
                    # Convert to Recommendation format
                    ai_recommendation = Recommendation(
                        entity_type=bid_optimization.entity_type,
                        entity_id=bid_optimization.entity_id,
                        entity_name=bid_optimization.entity_name,
                        adjustment_type='bid',
                        current_value=bid_optimization.current_bid,
                        recommended_value=bid_optimization.recommended_bid,
                        adjustment_amount=bid_optimization.adjustment_amount,
                        adjustment_percentage=bid_optimization.adjustment_percentage,
                        priority=bid_optimization.priority,
                        confidence=bid_optimization.confidence,
                        reason=bid_optimization.reason,
                        rules_triggered=['BID_OPTIMIZER'],
                        metadata=bid_optimization.metadata,
                        created_at=datetime.now(),
                        strategy_id=bid_optimization.metadata.get('strategy_id')
                    )
                    
                    # Record adjustment for cooldown tracking (legacy)
                    self._record_adjustment(entity_type, entity_id)
                    
                    # Track recommendation in learning loop if enabled
                    if self.learning_loop:
                        try:
                            self.learning_loop.track_recommendation(
                                ai_recommendation.__dict__, entity_id, entity_type
                            )
                        except Exception as e:
                            self.logger.error(f"Error tracking recommendation: {e}")
            except Exception as e:
                self.logger.error(f"Error in bid optimization for {entity_type} {entity_id}: {e}")
        
        # If AI optimizer returned a recommendation, return it (prevent double dip)
        if ai_recommendation:
            return [ai_recommendation]
        
        # Fall back to traditional rules ONLY if AI optimizer didn't run or didn't return a recommendation
        # FIX: When BidOptimizationEngine is enabled, ONLY allow Basic Rules for Budget/Negative Keywords
        # Prevent conflicting bid decisions by skipping ACOS/ROAS/CTR rules for bids
        rule_results = []
        for rule_name, rule in self.rules.items():
            # Skip bid-related rules (ACOS, ROAS, CTR) when BidOptimizationEngine is enabled
            if self.bid_optimizer and rule_name in ['acos', 'roas', 'ctr']:
                self.logger.debug(
                    f"Skipping basic rule '{rule_name}' for {entity_type} {entity_id}: "
                    f"BidOptimizationEngine is enabled (prevents conflicting bid decisions)"
                )
                continue
            
            # Allow Budget and Negative Keyword rules to always run
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
    
    def _save_all_recommendations(self, recommendations: List[Recommendation]) -> None:
        """
        Save all recommendations to database for real-time updates
        
        This ensures recommended_value is always up-to-date in the database
        """
        if not recommendations:
            self.logger.debug("No recommendations to save")
            return
        
        self.logger.info(f"Attempting to save {len(recommendations)} recommendations to database")
        saved_count = 0
        failed_count = 0
        for rec in recommendations:
            try:
                # Convert Recommendation dataclass to dict format expected by save_recommendation
                intelligence_signals = rec.metadata.get('intelligence_signals') if rec.metadata else None
                strategy_id = rec.strategy_id or rec.metadata.get('strategy_id') if rec.metadata else None
                policy_variant = rec.metadata.get('policy_variant', 'treatment') if rec.metadata else 'treatment'
                
                # Generate stable recommendation_id for real-time updates
                # Use entity_type_entity_id_adjustment_type so we update existing recommendations
                # This ensures recommended_value is always current
                recommendation_id = f"{rec.entity_type}_{rec.entity_id}_{rec.adjustment_type}"
                
                tracking_data = {
                    'recommendation_id': recommendation_id,
                    'entity_type': rec.entity_type,
                    'entity_id': rec.entity_id,
                    'adjustment_type': rec.adjustment_type,
                    'recommended_value': float(rec.recommended_value),
                    'current_value': float(rec.current_value),
                    'intelligence_signals': intelligence_signals,
                    'strategy_id': strategy_id,
                    'policy_variant': policy_variant,
                    'timestamp': rec.created_at,
                    'applied': False,
                    'metadata': rec.metadata or {}
                }
                
                # Save to database (upsert - update if exists)
                if not self.db:
                    self.logger.warning("Database connector not available, cannot save recommendations")
                    failed_count += 1
                    continue
                
                if not hasattr(self.db, 'save_recommendation'):
                    self.logger.warning("Database connector does not have save_recommendation method")
                    failed_count += 1
                    continue
                
                save_result = self.db.save_recommendation(tracking_data)
                
                if save_result:
                    saved_count += 1
                else:
                    failed_count += 1
                    self.logger.warning(f"Failed to save recommendation {recommendation_id} to database")
                
                # Track in learning loop if enabled (for outcome tracking) - regardless of DB save success
                if self.learning_loop and rec.adjustment_type == 'bid':
                    try:
                        self.learning_loop.track_recommendation(
                            {
                                'adjustment_type': rec.adjustment_type,
                                'recommended_value': rec.recommended_value,
                                'current_value': rec.current_value,
                                'metadata': rec.metadata or {},
                                'strategy_id': strategy_id
                            },
                            rec.entity_id,
                            rec.entity_type
                        )
                    except Exception as e:
                        self.logger.warning(f"Error tracking recommendation in learning loop: {e}")
                                
            except Exception as e:
                failed_count += 1
                self.logger.error(f"Error saving recommendation for {rec.entity_type} {rec.entity_id}: {e}", exc_info=True)
        
        # Always log the result, regardless of success/failure
        self.logger.info(f"Recommendation save summary: {saved_count} saved, {failed_count} failed out of {len(recommendations)} total")
    
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
    
    def get_intelligence_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get insights from intelligence engines and learning loop"""
        insights = {
            'intelligence_enabled': self.intelligence_orchestrator is not None,
            'learning_enabled': self.learning_loop is not None,
            'advanced_optimization_enabled': self.bid_optimizer is not None
        }
        
        # Get learning loop performance
        if self.learning_loop:
            try:
                learning_trends = self.learning_loop.analyze_performance_trends(days=days)
                insights['learning_performance'] = learning_trends
            except Exception as e:
                self.logger.error(f"Error getting learning trends: {e}")
                insights['learning_performance'] = None
        
        return insights
    
    def get_negative_keyword_candidates(self, campaign_id: int) -> List[Dict[str, Any]]:
        """Get negative keyword candidates for a campaign"""
        if not self.negative_manager:
            return []
        
        candidates = []
        
        # Get keywords for campaign
        ad_groups = self.db.get_ad_groups_with_performance(
            campaign_id, self.config.performance_lookback_days
        )
        
        for ad_group in ad_groups:
            ad_group_id = ad_group['ad_group_id']
            keywords = self.db.get_keywords_with_performance(
                ad_group_id, self.config.performance_lookback_days
            )
            
            for keyword in keywords:
                keyword_id = keyword['keyword_id']
                perf_7d = self.db.get_keyword_performance(keyword_id, 7)
                perf_14d = self.db.get_keyword_performance(keyword_id, 14)
                perf_30d = self.db.get_keyword_performance(keyword_id, 30)
                
                # Pass a list of lists as expected by identify_negative_candidates
                performance_windows = [perf_7d, perf_14d, perf_30d]
                
                candidate = self.negative_manager.identify_negative_candidates(
                    keyword, performance_windows
                )
                
                if candidate:
                    candidates.append({
                        'keyword_id': candidate.keyword_id,
                        'keyword_text': candidate.keyword_text,
                        'match_type': candidate.match_type,
                        'ctr': candidate.ctr,
                        'impressions': candidate.impressions,
                        'cost': candidate.cost,
                        'reason': candidate.reason,
                        'severity': candidate.severity,
                        'confidence': candidate.confidence,
                        'suggested_match_type': candidate.suggested_match_type
                    })
        
        return candidates
    
    def export_intelligence_report(self, output_path: str) -> None:
        """Export comprehensive intelligence report"""
        report = {
            'exported_at': datetime.now().isoformat(),
            'engine_status': {
                'intelligence_engines': self.intelligence_orchestrator is not None,
                'learning_loop': self.learning_loop is not None,
                'advanced_bid_optimization': self.bid_optimizer is not None,
                'negative_manager': self.negative_manager is not None
            },
            'insights': self.get_intelligence_insights(days=30),
            'configuration': {
                'enable_intelligence_engines': self.config.enable_intelligence_engines,
                'enable_learning_loop': self.config.enable_learning_loop,
                'enable_advanced_bid_optimization': self.config.enable_advanced_bid_optimization,
                'target_acos': self.config.acos_target,
                'target_roas': self.config.roas_target,
                'seasonal_boost_factor': self.config.seasonal_boost_factor
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Exported intelligence report to {output_path}")
    
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
