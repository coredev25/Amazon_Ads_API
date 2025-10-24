"""
Enhanced Negative Keyword Manager
Identifies and manages negative keywords with advanced logic
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import re


@dataclass
class NegativeKeywordCandidate:
    """Candidate for negative keyword list"""
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


class NegativeKeywordManager:
    """
    Advanced negative keyword identification and management
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Configuration thresholds
        self.ctr_threshold = config.get('negative_keyword_ctr_threshold', 0.1)
        self.impression_threshold = config.get('negative_keyword_impression_threshold', 1000)
        self.zero_conversion_threshold = config.get('negative_zero_conversion_threshold', 500)
        self.high_cost_threshold = config.get('negative_high_cost_threshold', 50.0)
        
        # Negative keyword patterns (common waste terms)
        self.waste_patterns = [
            r'\b(free|cheap|cheapest|discount|sale|clearance)\b',
            r'\b(used|refurbished|repair|fix|broken)\b',
            r'\b(review|reviews|complaint|complaints)\b',
            r'\b(diy|how to|tutorial|instructions)\b',
            r'\b(job|jobs|career|hiring|employment)\b',
            r'\b(for kids|for children|toy|toys)\b',  # Product-specific
        ]
    
    def identify_negative_candidates(self, keyword_data: Dict[str, Any],
                                     performance_data: List[Dict[str, Any]]) -> Optional[NegativeKeywordCandidate]:
        """Identify keywords that should be added to negative lists"""
        if not performance_data:
            return None
        
        keyword_text = keyword_data.get('keyword_text', '').lower()
        keyword_id = keyword_data.get('id', 0)
        match_type = keyword_data.get('match_type', 'UNKNOWN')
        
        # Aggregate performance metrics
        total_impressions = sum(int(record.get('impressions', 0)) for record in performance_data)
        total_clicks = sum(int(record.get('clicks', 0)) for record in performance_data)
        total_cost = sum(float(record.get('cost', 0)) for record in performance_data)
        total_conversions = sum(int(record.get('attributed_conversions_7d', 0)) for record in performance_data)
        
        # Calculate CTR
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # Rule 1: Low CTR with high impressions (relevance issue)
        if total_impressions >= self.impression_threshold and ctr < self.ctr_threshold:
            return NegativeKeywordCandidate(
                keyword_id=keyword_id,
                keyword_text=keyword_text,
                match_type=match_type,
                ctr=ctr,
                impressions=total_impressions,
                clicks=total_clicks,
                cost=total_cost,
                conversions=total_conversions,
                reason=f"Very low CTR ({ctr:.2f}%) with {total_impressions} impressions indicates poor relevance",
                severity='high',
                confidence=0.9,
                suggested_match_type='negative_exact'
            )
        
        # Rule 2: Zero conversions with significant spend
        if total_conversions == 0 and total_cost >= self.high_cost_threshold:
            return NegativeKeywordCandidate(
                keyword_id=keyword_id,
                keyword_text=keyword_text,
                match_type=match_type,
                ctr=ctr,
                impressions=total_impressions,
                clicks=total_clicks,
                cost=total_cost,
                conversions=total_conversions,
                reason=f"Zero conversions despite ${total_cost:.2f} spend",
                severity='critical',
                confidence=0.95,
                suggested_match_type='negative_exact'
            )
        
        # Rule 3: Zero conversions with moderate impressions
        if total_conversions == 0 and total_impressions >= self.zero_conversion_threshold:
            return NegativeKeywordCandidate(
                keyword_id=keyword_id,
                keyword_text=keyword_text,
                match_type=match_type,
                ctr=ctr,
                impressions=total_impressions,
                clicks=total_clicks,
                cost=total_cost,
                conversions=total_conversions,
                reason=f"Zero conversions with {total_impressions} impressions",
                severity='medium',
                confidence=0.7,
                suggested_match_type='negative_phrase'
            )
        
        # Rule 4: Waste term patterns
        waste_match = self._check_waste_patterns(keyword_text)
        if waste_match and total_impressions >= 100:
            return NegativeKeywordCandidate(
                keyword_id=keyword_id,
                keyword_text=keyword_text,
                match_type=match_type,
                ctr=ctr,
                impressions=total_impressions,
                clicks=total_clicks,
                cost=total_cost,
                conversions=total_conversions,
                reason=f"Contains waste term pattern: '{waste_match}'",
                severity='high',
                confidence=0.85,
                suggested_match_type='negative_phrase'
            )
        
        return None
    
    def _check_waste_patterns(self, keyword_text: str) -> Optional[str]:
        """Check if keyword matches known waste patterns"""
        for pattern in self.waste_patterns:
            match = re.search(pattern, keyword_text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def identify_broad_match_issues(self, keyword_data: Dict[str, Any],
                                   search_term_report: List[Dict[str, Any]]) -> List[str]:
        """Identify problematic search terms from broad match keywords"""
        negative_terms = []
        
        if keyword_data.get('match_type') != 'BROAD':
            return negative_terms
        
        # Analyze search terms that triggered this keyword
        for search_term_data in search_term_report:
            impressions = int(search_term_data.get('impressions', 0))
            clicks = int(search_term_data.get('clicks', 0))
            conversions = int(search_term_data.get('conversions', 0))
            
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            
            # Identify poor-performing search terms
            if impressions >= 50 and (ctr < 0.5 or (conversions == 0 and clicks >= 5)):
                search_term = search_term_data.get('search_term', '')
                if search_term and search_term not in negative_terms:
                    negative_terms.append(search_term)
        
        return negative_terms
    
    def build_negative_keyword_list(self, candidates: List[NegativeKeywordCandidate],
                                   existing_negatives: Set[str]) -> List[Dict[str, Any]]:
        """Build optimized negative keyword list"""
        negative_list = []
        
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
            
            negative_list.append({
                'keyword_text': candidate.keyword_text,
                'match_type': candidate.suggested_match_type,
                'reason': candidate.reason,
                'severity': candidate.severity,
                'confidence': candidate.confidence,
                'cost_saved': candidate.cost,
                'impressions': candidate.impressions
            })
        
        return negative_list
    
    def analyze_negative_keyword_coverage(self, active_keywords: List[Dict[str, Any]],
                                          negative_keywords: List[str]) -> Dict[str, Any]:
        """Analyze negative keyword list coverage and effectiveness"""
        total_keywords = len(active_keywords)
        negative_count = len(negative_keywords)
        
        # Calculate coverage metrics
        broad_match_count = sum(1 for kw in active_keywords if kw.get('match_type') == 'BROAD')
        phrase_match_count = sum(1 for kw in active_keywords if kw.get('match_type') == 'PHRASE')
        
        # Estimate potential waste
        high_risk_keywords = sum(1 for kw in active_keywords if kw.get('match_type') == 'BROAD' and kw.get('bid', 0) > 2.0)
        
        return {
            'total_active_keywords': total_keywords,
            'total_negative_keywords': negative_count,
            'coverage_ratio': negative_count / total_keywords if total_keywords > 0 else 0,
            'broad_match_keywords': broad_match_count,
            'phrase_match_keywords': phrase_match_count,
            'high_risk_keywords': high_risk_keywords,
            'recommendations': self._generate_coverage_recommendations(
                total_keywords, negative_count, broad_match_count, high_risk_keywords
            )
        }
    
    def _generate_coverage_recommendations(self, total_keywords: int,
                                           negative_count: int,
                                           broad_count: int,
                                           high_risk_count: int) -> List[str]:
        """Generate recommendations for negative keyword coverage"""
        recommendations = []
        
        coverage_ratio = negative_count / total_keywords if total_keywords > 0 else 0
        
        if coverage_ratio < 0.1:
            recommendations.append("Low negative keyword coverage - consider expanding negative lists")
        
        if broad_count > total_keywords * 0.5:
            recommendations.append(f"High proportion of broad match keywords ({broad_count}) - increase negative keyword monitoring")
        
        if high_risk_count > 0:
            recommendations.append(f"{high_risk_count} high-risk keywords (broad match with high bids) - add protective negatives")
        
        if not recommendations:
            recommendations.append("Negative keyword coverage appears adequate")
        
        return recommendations
    
    def suggest_negative_keyword_categories(self, product_category: str) -> List[str]:
        """Suggest negative keyword categories based on product type"""
        # Common negative categories by product type
        category_negatives = {
            'electronics': [
                'repair', 'fix', 'broken', 'used', 'refurbished', 
                'manual', 'instructions', 'tutorial', 'review'
            ],
            'clothing': [
                'pattern', 'sewing', 'diy', 'costume', 'rental',
                'used', 'vintage', 'thrift'
            ],
            'beauty': [
                'diy', 'homemade', 'recipe', 'ingredients',
                'school', 'kids', 'toy'
            ],
            'home': [
                'rental', 'apartment', 'commercial', 'industrial',
                'business', 'wholesale'
            ],
            'default': [
                'free', 'cheap', 'cheapest', 'used', 'broken',
                'repair', 'review', 'job', 'career'
            ]
        }
        
        category = product_category.lower() if product_category else 'default'
        
        # Try to match category
        for key in category_negatives:
            if key in category:
                return category_negatives[key]
        
        return category_negatives['default']
    
    def export_negative_keywords(self, negative_list: List[Dict[str, Any]],
                                output_format: str = 'amazon') -> List[Dict[str, str]]:
        """Export negative keywords in Amazon Ads format"""
        exported = []
        
        for negative in negative_list:
            if output_format == 'amazon':
                exported.append({
                    'Keyword': negative['keyword_text'],
                    'Match Type': self._convert_match_type(negative['match_type']),
                    'Status': 'Enabled'
                })
            else:  # CSV format
                exported.append({
                    'keyword': negative['keyword_text'],
                    'match_type': negative['match_type'],
                    'reason': negative['reason'],
                    'severity': negative['severity'],
                    'cost_saved': f"${negative.get('cost_saved', 0):.2f}"
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

