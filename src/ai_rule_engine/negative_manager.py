"""
Enhanced Negative Keyword Manager with Smart PPC Controls

This module implements a sophisticated negative keyword identification system that:
1. Uses multi-window lookback to handle episodic conversion behavior
2. Applies dynamic thresholds based on portfolio performance
3. Implements re-entry control and temporary holds
4. Considers attribution delays and conversion probability
5. Provides periodic re-evaluation for forgiveness logic

Addresses the key concerns of professional PPC managers about over-aggressive automation.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import re
import statistics


@dataclass
class NegativeKeywordCandidate:
    """Candidate for negative keyword list with enhanced metadata"""
    keyword_id: int
    keyword_text: str
    match_type: str
    ctr: float
    impressions: int
    clicks: int
    cost: float
    conversions: int
    reason: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence: float
    suggested_match_type: str  # 'negative_exact', 'negative_phrase', 'negative_broad'
    
    # Enhanced fields for smart decision-making
    lookback_windows_analyzed: int = 0
    consecutive_failures: int = 0
    last_conversion_date: Optional[datetime] = None
    conversion_probability: float = 0.0
    is_temporary_hold: bool = False
    hold_expiry_date: Optional[datetime] = None
    relative_performance_percentile: Optional[float] = None


@dataclass
class NegativeKeywordHistory:
    """Track historical performance of a keyword for re-evaluation"""
    keyword_id: int
    keyword_text: str
    marked_negative_date: datetime
    reason: str
    performance_windows: List[Dict[str, Any]] = field(default_factory=list)
    consecutive_zero_conversion_windows: int = 0
    total_cost_at_marking: float = 0.0
    can_be_reactivated: bool = False
    re_evaluation_date: Optional[datetime] = None


class SmartNegativeKeywordManager:
    """
    Professional-grade negative keyword manager with episodic behavior handling
    
    Key Features:
    - Multi-window lookback (7d, 14d, 30d) smoothing
    - Dynamic thresholds based on portfolio performance
    - Re-entry control with cooldown periods
    - Conversion probability scoring
    - Temporary holds instead of permanent negatives
    - Periodic re-evaluation for forgiveness
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Lookback window configuration
        self.short_window_days = config.get('negative_short_window_days', 7)
        self.medium_window_days = config.get('negative_medium_window_days', 14)
        self.long_window_days = config.get('negative_long_window_days', 30)
        
        # Consecutive failure requirements
        self.consecutive_failures_required = config.get('negative_consecutive_failures', 3)
        
        # Attribution delay consideration
        self.attribution_delay_days = config.get('attribution_delay_days', 14)
        
        # Cost thresholds (more conservative)
        self.min_cost_threshold = config.get('negative_min_cost_threshold', 100.0)  # Increased from $50
        self.critical_cost_threshold = config.get('negative_critical_cost_threshold', 200.0)
        
        # Impression thresholds (more conservative)
        self.min_impressions = config.get('negative_min_impressions', 2000)  # Increased from 1000
        
        # Dynamic threshold settings
        self.use_dynamic_thresholds = config.get('use_dynamic_thresholds', True)
        self.percentile_threshold = config.get('negative_percentile_threshold', 25)  # Bottom 25%
        
        # Temporary hold settings
        self.use_temporary_holds = config.get('use_temporary_holds', True)
        self.temporary_hold_days = config.get('temporary_hold_days', 30)
        
        # Re-evaluation settings
        self.enable_re_evaluation = config.get('enable_negative_re_evaluation', True)
        self.re_evaluation_interval_days = config.get('re_evaluation_interval_days', 60)
        
        # Cooldown between negative marking decisions
        self.decision_cooldown_days = config.get('negative_decision_cooldown_days', 14)
        
        # Conversion probability threshold
        self.min_conversion_probability = config.get('min_conversion_probability', 0.2)
        
        # Waste pattern handling with context
        self.waste_patterns = self._load_waste_patterns(config)
        self.price_tier = config.get('product_price_tier', 'mid')  # low, mid, premium
        
        self.logger.info(
            f"Smart Negative Keyword Manager initialized - "
            f"Lookback windows: {self.short_window_days}d/{self.medium_window_days}d/{self.long_window_days}d, "
            f"Consecutive failures required: {self.consecutive_failures_required}, "
            f"Temporary holds: {self.use_temporary_holds}"
        )
    
    def _load_waste_patterns(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """Load waste patterns with severity levels"""
        return {
            'critical': [  # Always negative regardless of context
                r'\b(job|jobs|career|hiring|employment|recruiter)\b',
                r'\b(porn|sex|adult|xxx)\b',
                r'\b(illegal|scam|fake|counterfeit)\b',
            ],
            'high': [  # Usually negative but consider context
                r'\b(repair|fix|broken|damaged)\b',
                r'\b(used|refurbished|secondhand|pre-owned)\b',
                r'\b(review|reviews|complaint|complaints|lawsuit)\b',
            ],
            'medium': [  # Context-dependent
                r'\b(diy|how to|tutorial|instructions|guide)\b',
                r'\b(free|freebie)\b',
                r'\b(for kids|for children|toy|toys)\b',
            ],
            'contextual': [  # Depends on price tier
                r'\b(cheap|cheapest|budget|affordable)\b',
                r'\b(luxury|premium|expensive|high-end)\b',
                r'\b(discount|sale|clearance|deal)\b',
            ]
        }
    
    def identify_negative_candidates(
        self, 
        keyword_data: Dict[str, Any],
        performance_windows: List[List[Dict[str, Any]]],  # Multiple time windows
        portfolio_stats: Optional[Dict[str, Any]] = None,
        last_decision_date: Optional[datetime] = None
    ) -> Optional[NegativeKeywordCandidate]:
        """
        Identify keywords that should be added to negative lists with smart logic
        
        Args:
            keyword_data: Keyword information
            performance_windows: List of performance data for different time windows
                                [short_window, medium_window, long_window]
            portfolio_stats: Overall portfolio statistics for dynamic thresholds
            last_decision_date: Date of last negative keyword decision for this keyword
            
        Returns:
            NegativeKeywordCandidate if keyword should be marked negative, None otherwise
        """
        if not performance_windows or not any(performance_windows):
            return None
        
        keyword_text = keyword_data.get('keyword_text', '').lower()
        keyword_id = keyword_data.get('id', 0)
        
        # Check decision cooldown
        if last_decision_date:
            days_since_decision = (datetime.now() - last_decision_date).days
            if days_since_decision < self.decision_cooldown_days:
                self.logger.debug(
                    f"Keyword {keyword_id} in cooldown period "
                    f"({days_since_decision}/{self.decision_cooldown_days} days)"
                )
                return None
        
        # Analyze performance across multiple windows
        window_analysis = self._analyze_performance_windows(performance_windows)
        
        if not window_analysis['has_sufficient_data']:
            return None
        
        # Rule 1: Critical waste patterns (always mark)
        waste_check = self._check_waste_patterns_with_context(
            keyword_text, 
            window_analysis['total_conversions']
        )
        if waste_check and waste_check['severity'] == 'critical':
            return self._create_candidate(
                keyword_data=keyword_data,
                window_analysis=window_analysis,
                reason=f"Critical waste term: '{waste_check['matched_term']}'",
                severity='critical',
                confidence=0.95,
                suggested_match_type='negative_phrase'
            )
        
        # Rule 2: Consecutive zero-conversion windows (smart check)
        if window_analysis['consecutive_zero_conversion_windows'] >= self.consecutive_failures_required:
            # Check if it's been long enough after attribution delay
            if window_analysis['total_cost'] >= self.min_cost_threshold:
                # Calculate conversion probability
                conv_probability = self._calculate_conversion_probability(
                    window_analysis,
                    keyword_data
                )
                
                if conv_probability < self.min_conversion_probability:
                    return self._create_candidate(
                        keyword_data=keyword_data,
                        window_analysis=window_analysis,
                        reason=f"Zero conversions across {window_analysis['consecutive_zero_conversion_windows']} consecutive windows (${window_analysis['total_cost']:.2f} spend, {conv_probability:.1%} probability)",
                        severity='high' if window_analysis['total_cost'] < self.critical_cost_threshold else 'critical',
                        confidence=0.85,
                        suggested_match_type='negative_exact',
                        conversion_probability=conv_probability,
                        is_temporary_hold=self.use_temporary_holds
                    )
        
        # Rule 3: Low CTR with dynamic thresholds
        if self.use_dynamic_thresholds and portfolio_stats:
            dynamic_ctr_result = self._evaluate_dynamic_ctr(
                window_analysis,
                portfolio_stats
            )
            
            if dynamic_ctr_result and dynamic_ctr_result['should_mark_negative']:
                return self._create_candidate(
                    keyword_data=keyword_data,
                    window_analysis=window_analysis,
                    reason=f"CTR {window_analysis['smoothed_ctr']:.2f}% in bottom {self.percentile_threshold}th percentile (threshold: {dynamic_ctr_result['threshold']:.2f}%)",
                    severity='medium',
                    confidence=dynamic_ctr_result['confidence'],
                    suggested_match_type='negative_exact',
                    relative_performance_percentile=dynamic_ctr_result['percentile']
                )
        else:
            # Fallback to static thresholds (but more conservative)
            if (window_analysis['total_impressions'] >= self.min_impressions and 
                window_analysis['smoothed_ctr'] < 0.05):  # Very low CTR (0.05% vs original 0.1%)
                return self._create_candidate(
                    keyword_data=keyword_data,
                    window_analysis=window_analysis,
                    reason=f"Very low CTR ({window_analysis['smoothed_ctr']:.2f}%) with {window_analysis['total_impressions']} impressions",
                    severity='medium',
                    confidence=0.7,
                    suggested_match_type='negative_exact'
                )
        
        # Rule 4: High cost with no conversions (but only after attribution window)
        if (window_analysis['total_conversions'] == 0 and 
            window_analysis['total_cost'] >= self.critical_cost_threshold and
            window_analysis['days_of_data'] >= self.attribution_delay_days):
            
            # But check if there's improving trend
            trend = self._analyze_performance_trend(performance_windows)
            if not trend['is_improving']:
                return self._create_candidate(
                    keyword_data=keyword_data,
                    window_analysis=window_analysis,
                    reason=f"Critical spend (${window_analysis['total_cost']:.2f}) with zero conversions after {window_analysis['days_of_data']} days",
                    severity='critical',
                    confidence=0.9,
                    suggested_match_type='negative_exact',
                    is_temporary_hold=self.use_temporary_holds
                )
        
        return None
    
    def _analyze_performance_windows(
        self, 
        performance_windows: List[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Analyze performance across multiple time windows with smoothing
        
        Returns comprehensive analysis including:
        - Aggregated metrics
        - Smoothed values
        - Consecutive failure tracking
        - Data quality indicators
        """
        analysis = {
            'has_sufficient_data': False,
            'total_impressions': 0,
            'total_clicks': 0,
            'total_cost': 0.0,
            'total_conversions': 0,
            'raw_ctr': 0.0,
            'smoothed_ctr': 0.0,
            'consecutive_zero_conversion_windows': 0,
            'last_conversion_date': None,
            'windows_analyzed': 0,
            'days_of_data': 0
        }
        
        zero_conversion_streak = 0
        window_metrics = []
        
        # Analyze each window
        for window_idx, window_data in enumerate(performance_windows):
            if not window_data:
                continue
            
            analysis['windows_analyzed'] += 1
            
            window_impressions = sum(int(r.get('impressions', 0)) for r in window_data)
            window_clicks = sum(int(r.get('clicks', 0)) for r in window_data)
            window_cost = sum(float(r.get('cost', 0)) for r in window_data)
            window_conversions = sum(int(r.get('attributed_conversions_14d', 0)) for r in window_data)
            
            # Track consecutive zero-conversion windows
            if window_conversions == 0 and window_impressions > 50:
                zero_conversion_streak += 1
            else:
                zero_conversion_streak = 0
            
            window_metrics.append({
                'impressions': window_impressions,
                'clicks': window_clicks,
                'cost': window_cost,
                'conversions': window_conversions,
                'ctr': (window_clicks / window_impressions * 100) if window_impressions > 0 else 0
            })
            
            # Aggregate totals (from longest window to avoid double counting)
            if window_idx == len(performance_windows) - 1:  # Use longest window for totals
                analysis['total_impressions'] = window_impressions
                analysis['total_clicks'] = window_clicks
                analysis['total_cost'] = window_cost
                analysis['total_conversions'] = window_conversions
        
        analysis['consecutive_zero_conversion_windows'] = zero_conversion_streak
        
        # Calculate CTR with smoothing (weight recent windows more)
        if window_metrics:
            weights = [0.5, 0.3, 0.2][:len(window_metrics)]  # Recent → older
            weights = [w / sum(weights) for w in weights]  # Normalize
            
            weighted_ctr = sum(
                m['ctr'] * w for m, w in zip(window_metrics, weights)
            )
            analysis['smoothed_ctr'] = weighted_ctr
            analysis['raw_ctr'] = window_metrics[0]['ctr'] if window_metrics else 0.0
        
        # Determine if we have sufficient data
        analysis['has_sufficient_data'] = (
            analysis['windows_analyzed'] >= 2 and
            analysis['total_impressions'] >= 100
        )
        
        # Estimate days of data (based on windows analyzed)
        if analysis['windows_analyzed'] >= 3:
            analysis['days_of_data'] = self.long_window_days
        elif analysis['windows_analyzed'] >= 2:
            analysis['days_of_data'] = self.medium_window_days
        else:
            analysis['days_of_data'] = self.short_window_days
        
        return analysis
    
    def _calculate_conversion_probability(
        self,
        window_analysis: Dict[str, Any],
        keyword_data: Dict[str, Any]
    ) -> float:
        """
        Calculate probability that keyword will convert in the future
        
        Uses multiple factors:
        - CTR (engagement indicator)
        - Impression volume (exposure)
        - Cost efficiency
        - Historical patterns
        """
        probability = 0.0
        
        # Factor 1: CTR score (0-0.4)
        ctr = window_analysis['smoothed_ctr']
        if ctr > 0.5:
            probability += 0.4
        elif ctr > 0.2:
            probability += 0.3
        elif ctr > 0.1:
            probability += 0.2
        elif ctr > 0.05:
            probability += 0.1
        
        # Factor 2: Impression volume (0-0.3)
        impressions = window_analysis['total_impressions']
        if impressions < 500:
            probability += 0.3  # Low volume, still learning
        elif impressions < 1000:
            probability += 0.2
        elif impressions < 2000:
            probability += 0.1
        # else: 0 - high volume with no conversions is bad
        
        # Factor 3: Match type (0-0.2)
        match_type = keyword_data.get('match_type', '')
        if match_type == 'EXACT':
            probability += 0.2
        elif match_type == 'PHRASE':
            probability += 0.15
        elif match_type == 'BROAD':
            probability += 0.05
        
        # Factor 4: Cost per click (0-0.1)
        clicks = window_analysis['total_clicks']
        cost = window_analysis['total_cost']
        if clicks > 0:
            cpc = cost / clicks
            if cpc < 1.0:
                probability += 0.1
            elif cpc < 2.0:
                probability += 0.05
        
        return min(1.0, probability)
    
    def _evaluate_dynamic_ctr(
        self,
        window_analysis: Dict[str, Any],
        portfolio_stats: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate CTR using dynamic percentile-based thresholds
        
        Instead of a static CTR threshold, compare to portfolio performance
        """
        if 'ctr_distribution' not in portfolio_stats:
            return None
        
        ctr_values = portfolio_stats['ctr_distribution']
        if not ctr_values:
            return None
        
        # Calculate percentile threshold
        percentile_value = statistics.quantiles(ctr_values, n=100)[self.percentile_threshold - 1]
        
        keyword_ctr = window_analysis['smoothed_ctr']
        
        # Calculate percentile rank
        below_count = sum(1 for ctr in ctr_values if ctr < keyword_ctr)
        percentile_rank = (below_count / len(ctr_values)) * 100
        
        should_mark = (
            keyword_ctr < percentile_value and
            window_analysis['total_impressions'] >= self.min_impressions
        )
        
        # Confidence based on data volume
        confidence = min(0.9, 0.5 + (window_analysis['total_impressions'] / 5000))
        
        return {
            'should_mark_negative': should_mark,
            'threshold': percentile_value,
            'percentile': percentile_rank,
            'confidence': confidence
        }
    
    def _analyze_performance_trend(
        self,
        performance_windows: List[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Analyze if performance is improving or declining
        
        Returns:
            - is_improving: bool
            - trend_direction: str
            - confidence: float
        """
        if len(performance_windows) < 2:
            return {'is_improving': False, 'trend_direction': 'unknown', 'confidence': 0.0}
        
        window_ctrs = []
        for window_data in performance_windows:
            if not window_data:
                continue
            impressions = sum(int(r.get('impressions', 0)) for r in window_data)
            clicks = sum(int(r.get('clicks', 0)) for r in window_data)
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            window_ctrs.append(ctr)
        
        if len(window_ctrs) < 2:
            return {'is_improving': False, 'trend_direction': 'unknown', 'confidence': 0.0}
        
        # Simple trend: compare recent to older
        recent_ctr = window_ctrs[0]
        older_ctr = statistics.mean(window_ctrs[1:])
        
        improvement_pct = ((recent_ctr - older_ctr) / older_ctr * 100) if older_ctr > 0 else 0
        
        is_improving = improvement_pct > 10  # At least 10% improvement
        
        return {
            'is_improving': is_improving,
            'trend_direction': 'improving' if improvement_pct > 0 else 'declining',
            'improvement_percentage': improvement_pct,
            'confidence': 0.7
        }
    
    def _check_waste_patterns_with_context(
        self,
        keyword_text: str,
        conversions: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check waste patterns with context awareness
        
        Some patterns are acceptable depending on:
        - Product price tier
        - Historical conversions
        - Specific context
        """
        # Critical patterns - always flag
        for pattern in self.waste_patterns['critical']:
            match = re.search(pattern, keyword_text, re.IGNORECASE)
            if match:
                return {
                    'matched_term': match.group(0),
                    'severity': 'critical',
                    'pattern_type': 'critical'
                }
        
        # High severity patterns - flag unless has conversions
        if conversions == 0:
            for pattern in self.waste_patterns['high']:
                match = re.search(pattern, keyword_text, re.IGNORECASE)
                if match:
                    return {
                        'matched_term': match.group(0),
                        'severity': 'high',
                        'pattern_type': 'high'
                    }
        
        # Contextual patterns - depends on price tier
        for pattern in self.waste_patterns['contextual']:
            match = re.search(pattern, keyword_text, re.IGNORECASE)
            if match:
                matched_word = match.group(0).lower()
                
                # "cheap" is bad for premium products but okay for low-tier
                if matched_word in ['cheap', 'cheapest', 'budget', 'affordable']:
                    if self.price_tier == 'premium':
                        return {
                            'matched_term': matched_word,
                            'severity': 'medium',
                            'pattern_type': 'price_mismatch'
                        }
                
                # "luxury" is bad for budget products
                elif matched_word in ['luxury', 'premium', 'expensive', 'high-end']:
                    if self.price_tier == 'low':
                        return {
                            'matched_term': matched_word,
                            'severity': 'medium',
                            'pattern_type': 'price_mismatch'
                        }
        
        return None
    
    def _create_candidate(
        self,
        keyword_data: Dict[str, Any],
        window_analysis: Dict[str, Any],
        reason: str,
        severity: str,
        confidence: float,
        suggested_match_type: str,
        conversion_probability: float = 0.0,
        is_temporary_hold: bool = False,
        relative_performance_percentile: Optional[float] = None
    ) -> NegativeKeywordCandidate:
        """Create a negative keyword candidate with all metadata"""
        
        hold_expiry = None
        if is_temporary_hold:
            hold_expiry = datetime.now() + timedelta(days=self.temporary_hold_days)
        
        return NegativeKeywordCandidate(
            keyword_id=keyword_data.get('id', 0),
            keyword_text=keyword_data.get('keyword_text', '').lower(),
            match_type=keyword_data.get('match_type', 'UNKNOWN'),
            ctr=window_analysis['smoothed_ctr'],
            impressions=window_analysis['total_impressions'],
            clicks=window_analysis['total_clicks'],
            cost=window_analysis['total_cost'],
            conversions=window_analysis['total_conversions'],
            reason=reason,
            severity=severity,
            confidence=confidence,
            suggested_match_type=suggested_match_type,
            lookback_windows_analyzed=window_analysis['windows_analyzed'],
            consecutive_failures=window_analysis['consecutive_zero_conversion_windows'],
            last_conversion_date=window_analysis.get('last_conversion_date'),
            conversion_probability=conversion_probability,
            is_temporary_hold=is_temporary_hold,
            hold_expiry_date=hold_expiry,
            relative_performance_percentile=relative_performance_percentile
        )
    
    def evaluate_negative_keywords_for_reactivation(
        self,
        negative_keyword_history: List[NegativeKeywordHistory],
        current_portfolio_stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Periodically re-evaluate negative keywords to see if they should be given another chance
        
        This is the "forgiveness" logic - keywords marked negative can be reactivated if:
        - Sufficient time has passed
        - Market conditions have changed
        - Portfolio stats suggest they might now be valuable
        
        Returns:
            List of keywords recommended for reactivation
        """
        reactivation_candidates = []
        
        for history in negative_keyword_history:
            # Check if enough time has passed
            days_since_marking = (datetime.now() - history.marked_negative_date).days
            
            if days_since_marking < self.re_evaluation_interval_days:
                continue
            
            # Don't reactivate critical waste terms
            if 'critical waste' in history.reason.lower():
                continue
            
            # Evaluate if conditions have changed
            should_reactivate = False
            reactivation_reason = ""
            
            # Reason 1: Temporary hold has expired
            if 'temporary' in history.reason.lower():
                should_reactivate = True
                reactivation_reason = f"Temporary hold expired after {days_since_marking} days"
            
            # Reason 2: Portfolio CTR has dropped (maybe lower standards now)
            elif current_portfolio_stats.get('avg_ctr', 0) < 0.5:
                if 'low ctr' in history.reason.lower():
                    should_reactivate = True
                    reactivation_reason = "Portfolio CTR declined - keyword may now be competitive"
            
            # Reason 3: Long time has passed (seasonal recovery possible)
            elif days_since_marking >= 90:  # 3 months
                should_reactivate = True
                reactivation_reason = f"Long-term re-evaluation after {days_since_marking} days - testing seasonal recovery"
            
            if should_reactivate:
                reactivation_candidates.append({
                    'keyword_id': history.keyword_id,
                    'keyword_text': history.keyword_text,
                    'marked_negative_date': history.marked_negative_date,
                    'days_as_negative': days_since_marking,
                    'original_reason': history.reason,
                    'reactivation_reason': reactivation_reason,
                    'suggested_action': 'reactivate_with_monitoring',
                    'recommended_bid': 'start_low'  # Start with low bid to test
                })
        
        self.logger.info(
            f"Re-evaluation complete: {len(reactivation_candidates)} keywords "
            f"recommended for reactivation out of {len(negative_keyword_history)} reviewed"
        )
        
        return reactivation_candidates
    
    def build_negative_keyword_list(
        self,
        candidates: List[NegativeKeywordCandidate],
        existing_negatives: Set[str]
    ) -> Dict[str, Any]:
        """
        Build optimized negative keyword list with categorization
        
        Returns:
            Dictionary with:
            - permanent_negatives: List of keywords to mark as permanent negatives
            - temporary_holds: List of keywords to temporarily pause
            - monitoring_required: List of keywords to watch closely
        """
        permanent_negatives = []
        temporary_holds = []
        monitoring_required = []
        
        # Sort by severity and confidence
        severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (severity_order.get(c.severity, 0), c.confidence),
            reverse=True
        )
        
        for candidate in sorted_candidates:
            # Skip if already in negative list
            if candidate.keyword_text in existing_negatives:
                continue
            
            negative_entry = {
                'keyword_id': candidate.keyword_id,
                'keyword_text': candidate.keyword_text,
                'match_type': candidate.suggested_match_type,
                'reason': candidate.reason,
                'severity': candidate.severity,
                'confidence': candidate.confidence,
                'cost_to_date': candidate.cost,
                'impressions': candidate.impressions,
                'conversion_probability': candidate.conversion_probability,
                'windows_analyzed': candidate.lookback_windows_analyzed,
                'consecutive_failures': candidate.consecutive_failures
            }
            
            # Categorize based on temporary hold flag and severity
            if candidate.is_temporary_hold and candidate.severity != 'critical':
                negative_entry['expiry_date'] = candidate.hold_expiry_date
                negative_entry['re_evaluation_date'] = candidate.hold_expiry_date
                temporary_holds.append(negative_entry)
            elif candidate.severity in ['critical', 'high']:
                permanent_negatives.append(negative_entry)
            else:
                # Medium/low severity - add to monitoring instead
                monitoring_required.append(negative_entry)
        
        return {
            'permanent_negatives': permanent_negatives,
            'temporary_holds': temporary_holds,
            'monitoring_required': monitoring_required,
            'summary': {
                'total_candidates': len(candidates),
                'permanent_count': len(permanent_negatives),
                'temporary_count': len(temporary_holds),
                'monitoring_count': len(monitoring_required),
                'estimated_cost_savings': sum(c.cost for c in candidates)
            }
        }
    
    def export_negative_keywords(
        self,
        negative_list: Dict[str, Any],
        output_format: str = 'amazon'
    ) -> List[Dict[str, str]]:
        """Export negative keywords in Amazon Ads format"""
        exported = []
        
        # Export permanent negatives
        for negative in negative_list.get('permanent_negatives', []):
            if output_format == 'amazon':
                exported.append({
                    'Keyword': negative['keyword_text'],
                    'Match Type': self._convert_match_type(negative['match_type']),
                    'Status': 'Enabled',
                    'Notes': f"{negative['reason']} (Confidence: {negative['confidence']:.0%})"
                })
            else:  # detailed CSV format
                exported.append({
                    'keyword': negative['keyword_text'],
                    'match_type': negative['match_type'],
                    'type': 'permanent',
                    'reason': negative['reason'],
                    'severity': negative['severity'],
                    'confidence': f"{negative['confidence']:.0%}",
                    'cost_saved': f"${negative['cost_to_date']:.2f}"
                })
        
        # Export temporary holds
        for negative in negative_list.get('temporary_holds', []):
            if output_format == 'amazon':
                exported.append({
                    'Keyword': negative['keyword_text'],
                    'Match Type': self._convert_match_type(negative['match_type']),
                    'Status': 'Paused',
                    'Notes': f"Temporary hold until {negative['expiry_date'].strftime('%Y-%m-%d')}"
                })
            else:
                exported.append({
                    'keyword': negative['keyword_text'],
                    'match_type': negative['match_type'],
                    'type': 'temporary_hold',
                    'reason': negative['reason'],
                    'expiry_date': negative['expiry_date'].strftime('%Y-%m-%d'),
                    'confidence': f"{negative['confidence']:.0%}",
                    'cost_saved': f"${negative['cost_to_date']:.2f}"
                })
        
        return exported
    
    def _convert_match_type(self, internal_match_type: str) -> str:
        """Convert internal match type to Amazon format"""
        conversion_map = {
            'negative_exact': 'Negative Exact',
            'negative_phrase': 'Negative Phrase',
            'negative_broad': 'Negative Broad'
        }
        return conversion_map.get(internal_match_type, 'Negative Phrase')


# Legacy wrapper for backwards compatibility
class NegativeKeywordManager(SmartNegativeKeywordManager):
    """
    Legacy wrapper - redirects to SmartNegativeKeywordManager
    
    This ensures existing code continues to work while using the improved logic
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.logger.warning(
            "NegativeKeywordManager is deprecated. "
            "Use SmartNegativeKeywordManager for enhanced functionality."
        )
        super().__init__(config)
