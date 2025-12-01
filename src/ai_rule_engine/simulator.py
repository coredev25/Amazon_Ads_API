"""
Simulated Sandbox for Historical Replay (#30)

Implements:
- Historical data replay
- Simulated bid changes
- What-if analysis
- Safe testing before production
"""

import logging
import copy
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False
    pd = None


class HistoricalSimulator:
    """
    Simulated sandbox for testing bid changes on historical data (#30)
    """
    
    def __init__(self, config: Dict[str, Any], db_connector=None):
        self.config = config
        self.db = db_connector
        self.logger = logging.getLogger(__name__)
        self.enable_simulator = config.get('enable_simulator', False)
        self.simulation_lookback_days = config.get('simulation_lookback_days', 30)
    
    def load_historical_data(self, entity_type: str, entity_id: int,
                            start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Load historical performance data for simulation
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            start_date: Start date
            end_date: End date
            
        Returns:
            List of historical performance records
        """
        if not self.db:
            return []
        
        try:
            if hasattr(self.db, 'get_entity_performance_range'):
                return self.db.get_entity_performance_range(entity_type, entity_id, start_date, end_date)
            else:
                # Fallback to standard methods
                if entity_type == 'keyword':
                    return self.db.get_keyword_performance(entity_id, days_back=(end_date - start_date).days)
                elif entity_type == 'ad_group':
                    return self.db.get_ad_group_performance(entity_id, days_back=(end_date - start_date).days)
                elif entity_type == 'campaign':
                    return self.db.get_campaign_performance(entity_id, days_back=(end_date - start_date).days)
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
        
        return []
    
    def simulate_bid_change(self, historical_data: List[Dict[str, Any]],
                           original_bid: float, new_bid: float,
                           change_date: datetime) -> Dict[str, Any]:
        """
        Simulate what would have happened with a different bid
        
        Args:
            historical_data: Historical performance data
            original_bid: Original bid that was used
            new_bid: New bid to simulate
            change_date: Date when bid change would have occurred
            
        Returns:
            Simulation results with projected metrics
        """
        if not historical_data:
            return {'status': 'error', 'reason': 'no_historical_data'}
        
        try:
            # Sort by date
            sorted_data = sorted(historical_data, key=lambda x: x.get('report_date', datetime.now()))
            
            # Find change point
            change_index = None
            for i, record in enumerate(sorted_data):
                if record.get('report_date', datetime.now()) >= change_date:
                    change_index = i
                    break
            
            if change_index is None:
                change_index = len(sorted_data) // 2  # Default to middle
            
            # Calculate bid ratio
            bid_ratio = new_bid / original_bid if original_bid > 0 else 1.0
            
            # Simulate impact
            # Assumptions:
            # - Bid changes affect impressions (higher bid = more impressions)
            # - CTR may change slightly with bid
            # - Cost scales with bid and impressions
            # - Conversions scale with clicks (assuming same conversion rate)
            
            before_period = sorted_data[:change_index]
            after_period = sorted_data[change_index:]
            
            # Calculate baseline metrics
            baseline_metrics = self._calculate_period_metrics(before_period)
            
            # Simulate after period
            simulated_after = []
            for record in after_period:
                simulated = copy.deepcopy(record)
                
                # Adjust impressions (higher bid = more impressions, but with diminishing returns)
                impression_multiplier = min(1.5, 1.0 + 0.3 * (bid_ratio - 1.0))
                simulated['impressions'] = int(record.get('impressions', 0) * impression_multiplier)
                
                # Adjust CTR (slight improvement with higher bid due to better placement)
                ctr_multiplier = 1.0 + 0.05 * (bid_ratio - 1.0) if bid_ratio > 1.0 else 1.0 - 0.05 * (1.0 - bid_ratio)
                original_ctr = (record.get('clicks', 0) / record.get('impressions', 1)) if record.get('impressions', 0) > 0 else 0
                simulated['clicks'] = int(simulated['impressions'] * original_ctr * ctr_multiplier)
                
                # Adjust cost (scales with bid and impressions)
                simulated['cost'] = float(record.get('cost', 0)) * bid_ratio * impression_multiplier
                
                # Adjust conversions (assumes same conversion rate)
                original_conversion_rate = (record.get('attributed_conversions_7d', 0) / record.get('clicks', 1)) if record.get('clicks', 0) > 0 else 0
                simulated['attributed_conversions_7d'] = int(simulated['clicks'] * original_conversion_rate)
                
                # Adjust sales (assumes same average order value)
                original_aov = (record.get('attributed_sales_7d', 0) / record.get('attributed_conversions_7d', 1)) if record.get('attributed_conversions_7d', 0) > 0 else 0
                simulated['attributed_sales_7d'] = float(simulated['attributed_conversions_7d']) * original_aov
                
                simulated_after.append(simulated)
            
            # Calculate simulated metrics
            simulated_metrics = self._calculate_period_metrics(simulated_after)
            
            # Compare
            comparison = {
                'original_acos': baseline_metrics.get('acos', 0),
                'simulated_acos': simulated_metrics.get('acos', 0),
                'acos_change': simulated_metrics.get('acos', 0) - baseline_metrics.get('acos', 0),
                'original_roas': baseline_metrics.get('roas', 0),
                'simulated_roas': simulated_metrics.get('roas', 0),
                'roas_change': simulated_metrics.get('roas', 0) - baseline_metrics.get('roas', 0),
                'original_cost': baseline_metrics.get('total_cost', 0),
                'simulated_cost': simulated_metrics.get('total_cost', 0),
                'cost_change': simulated_metrics.get('total_cost', 0) - baseline_metrics.get('total_cost', 0),
                'original_sales': baseline_metrics.get('total_sales', 0),
                'simulated_sales': simulated_metrics.get('total_sales', 0),
                'sales_change': simulated_metrics.get('total_sales', 0) - baseline_metrics.get('total_sales', 0)
            }
            
            return {
                'status': 'success',
                'original_bid': original_bid,
                'simulated_bid': new_bid,
                'bid_change_percentage': (bid_ratio - 1.0) * 100,
                'baseline_metrics': baseline_metrics,
                'simulated_metrics': simulated_metrics,
                'comparison': comparison,
                'recommendation': self._generate_recommendation(comparison)
            }
        except Exception as e:
            self.logger.error(f"Error in simulation: {e}")
            return {'status': 'error', 'reason': str(e)}
    
    def _calculate_period_metrics(self, period_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate aggregated metrics for a period"""
        if not period_data:
            return {}
        
        total_cost = sum(float(r.get('cost', 0)) for r in period_data)
        total_sales = sum(float(r.get('attributed_sales_7d', 0)) for r in period_data)
        total_impressions = sum(int(r.get('impressions', 0)) for r in period_data)
        total_clicks = sum(int(r.get('clicks', 0)) for r in period_data)
        total_conversions = sum(int(r.get('attributed_conversions_7d', 0)) for r in period_data)
        
        acos = (total_cost / total_sales) if total_sales > 0 else float('inf')
        roas = (total_sales / total_cost) if total_cost > 0 else 0
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        return {
            'total_cost': total_cost,
            'total_sales': total_sales,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'acos': acos,
            'roas': roas,
            'ctr': ctr
        }
    
    def _generate_recommendation(self, comparison: Dict[str, Any]) -> str:
        """Generate recommendation based on simulation results"""
        roas_change = comparison.get('roas_change', 0)
        acos_change = comparison.get('acos_change', 0)
        cost_change = comparison.get('cost_change', 0)
        
        if roas_change > 0.5 and acos_change < -0.02:
            return "STRONG POSITIVE: Significant ROAS improvement and ACOS reduction. Recommended."
        elif roas_change > 0.2:
            return "POSITIVE: ROAS improvement. Consider implementing."
        elif roas_change < -0.2 or acos_change > 0.02:
            return "NEGATIVE: Performance degradation. Not recommended."
        elif cost_change > 100 and roas_change < 0.1:
            return "CAUTION: Significant cost increase with minimal benefit."
        else:
            return "NEUTRAL: Minimal impact. Consider other factors."
    
    def run_what_if_analysis(self, entity_type: str, entity_id: int,
                            bid_scenarios: List[float],
                            start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Run what-if analysis with multiple bid scenarios
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            bid_scenarios: List of bid values to test
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Analysis results for all scenarios
        """
        # Load historical data
        historical_data = self.load_historical_data(entity_type, entity_id, start_date, end_date)
        
        if not historical_data:
            return {'status': 'error', 'reason': 'no_historical_data'}
        
        # Get original bid (use average from historical data or from entity)
        original_bid = historical_data[0].get('bid', 1.0) if historical_data else 1.0
        
        # Simulate each scenario
        scenarios = []
        for new_bid in bid_scenarios:
            result = self.simulate_bid_change(
                historical_data,
                original_bid,
                new_bid,
                start_date + timedelta(days=(end_date - start_date).days // 2)
            )
            result['scenario_bid'] = new_bid
            scenarios.append(result)
        
        # Find best scenario
        best_scenario = None
        best_score = float('-inf')
        
        for scenario in scenarios:
            if scenario.get('status') == 'success':
                comparison = scenario.get('comparison', {})
                # Score: prioritize ROAS improvement and ACOS reduction
                score = comparison.get('roas_change', 0) * 2 - comparison.get('acos_change', 0) * 10
                if score > best_score:
                    best_score = score
                    best_scenario = scenario
        
        return {
            'status': 'success',
            'original_bid': original_bid,
            'scenarios': scenarios,
            'best_scenario': best_scenario,
            'summary': {
                'total_scenarios': len(scenarios),
                'successful_scenarios': sum(1 for s in scenarios if s.get('status') == 'success'),
                'best_bid': best_scenario.get('simulated_bid') if best_scenario else None
            }
        }
    
    def replay_historical_period(self, entity_type: str, entity_id: int,
                                start_date: datetime, end_date: datetime,
                                bid_strategy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Replay a historical period with a different bid strategy
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            start_date: Start date
            end_date: End date
            bid_strategy: Optional strategy function or fixed bid
            
        Returns:
            Replay results
        """
        historical_data = self.load_historical_data(entity_type, entity_id, start_date, end_date)
        
        if not historical_data:
            return {'status': 'error', 'reason': 'no_historical_data'}
        
        # Apply strategy day by day
        simulated_data = []
        for record in historical_data:
            simulated = copy.deepcopy(record)
            
            # Apply bid strategy
            if bid_strategy:
                if callable(bid_strategy):
                    new_bid = bid_strategy(record)
                else:
                    new_bid = bid_strategy.get('fixed_bid', record.get('bid', 1.0))
            else:
                new_bid = record.get('bid', 1.0)
            
            original_bid = record.get('bid', 1.0)
            bid_ratio = new_bid / original_bid if original_bid > 0 else 1.0
            
            # Apply same simulation logic as simulate_bid_change
            impression_multiplier = min(1.5, 1.0 + 0.3 * (bid_ratio - 1.0))
            simulated['impressions'] = int(record.get('impressions', 0) * impression_multiplier)
            
            ctr_multiplier = 1.0 + 0.05 * (bid_ratio - 1.0) if bid_ratio > 1.0 else 1.0 - 0.05 * (1.0 - bid_ratio)
            original_ctr = (record.get('clicks', 0) / record.get('impressions', 1)) if record.get('impressions', 0) > 0 else 0
            simulated['clicks'] = int(simulated['impressions'] * original_ctr * ctr_multiplier)
            
            simulated['cost'] = float(record.get('cost', 0)) * bid_ratio * impression_multiplier
            
            original_conversion_rate = (record.get('attributed_conversions_7d', 0) / record.get('clicks', 1)) if record.get('clicks', 0) > 0 else 0
            simulated['attributed_conversions_7d'] = int(simulated['clicks'] * original_conversion_rate)
            
            original_aov = (record.get('attributed_sales_7d', 0) / record.get('attributed_conversions_7d', 1)) if record.get('attributed_conversions_7d', 0) > 0 else 0
            simulated['attributed_sales_7d'] = float(simulated['attributed_conversions_7d']) * original_aov
            
            simulated_data.append(simulated)
        
        # Calculate final metrics
        final_metrics = self._calculate_period_metrics(simulated_data)
        original_metrics = self._calculate_period_metrics(historical_data)
        
        return {
            'status': 'success',
            'original_metrics': original_metrics,
            'simulated_metrics': final_metrics,
            'improvement': {
                'roas_change': final_metrics.get('roas', 0) - original_metrics.get('roas', 0),
                'acos_change': final_metrics.get('acos', 0) - original_metrics.get('acos', 0),
                'sales_change': final_metrics.get('total_sales', 0) - original_metrics.get('total_sales', 0),
                'cost_change': final_metrics.get('total_cost', 0) - original_metrics.get('total_cost', 0)
            }
        }

