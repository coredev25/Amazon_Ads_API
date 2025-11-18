"""
Re-entry Control and Bid Oscillation Prevention Module

This module implements the logic to prevent rapid bid oscillation and
ensure stable, data-driven bid adjustments.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class ReEntryControlResult:
    """Result of re-entry control check"""
    allowed: bool
    reason: str
    metadata: Dict[str, Any]
    days_until_eligible: Optional[int] = None
    last_change_date: Optional[datetime] = None


@dataclass
class OscillationDetectionResult:
    """Result of oscillation detection"""
    is_oscillating: bool
    direction_changes: int
    last_changes: List[Dict[str, Any]]
    recommendation: str


class ReEntryController:
    """
    Controls bid re-entry logic to prevent oscillation and ensure stable adjustments
    
    Implements:
    1. Cooldown period enforcement
    2. Minimum change threshold
    3. ACOS stability checks
    4. Hysteresis bands
    5. Historical smoothing
    6. Oscillation detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Re-entry Controller
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.cooldown_days = config.get('bid_change_cooldown_days', 3)
        self.min_change_threshold = config.get('min_bid_change_threshold', 0.05)
        self.stability_window = config.get('acos_stability_window', 1)
        self.acos_target = config.get('acos_target', 0.09)  # 9% target ACOS
        self.hysteresis_lower = config.get('acos_hysteresis_lower', 0.25)
        self.hysteresis_upper = config.get('acos_hysteresis_upper', 0.35)
        self.smoothing_recent = config.get('historical_smoothing_weight_recent', 0.7)
        self.smoothing_older = config.get('historical_smoothing_weight_older', 0.3)
        self.oscillation_lookback = config.get('oscillation_lookback_days', 14)
        self.oscillation_threshold = config.get('oscillation_direction_change_threshold', 3)
        
        self.logger.info(f"Re-entry Controller initialized: {self.cooldown_days}-day cooldown, "
                        f"ACOS target {self.acos_target:.0%} (bands: {self.hysteresis_lower:.0%}-{self.hysteresis_upper:.0%}), "
                        f"stability window {self.stability_window} cycle(s)")
    
    def should_adjust_bid(self, 
                          entity_id: int,
                          entity_type: str,
                          current_bid: float,
                          proposed_bid: float,
                          last_change_date: Optional[datetime],
                          last_bid: Optional[float],
                          acos_history: List[Dict[str, Any]],
                          bid_change_history: List[Dict[str, Any]]) -> ReEntryControlResult:
        """
        Determine if a bid adjustment should be allowed
        
        Args:
            entity_id: Entity identifier
            entity_type: Type of entity (keyword, ad_group, campaign)
            current_bid: Current bid value
            proposed_bid: Proposed new bid value
            last_change_date: Date of last bid change
            last_bid: Previous bid value
            acos_history: Historical ACOS data
            bid_change_history: History of bid changes
            
        Returns:
            ReEntryControlResult with decision and reasoning
        """
        metadata = {
            'entity_id': entity_id,
            'entity_type': entity_type,
            'current_bid': current_bid,
            'proposed_bid': proposed_bid
        }
        
        # Check 1: Cooldown period
        if last_change_date:
            days_since_change = (datetime.now() - last_change_date).days
            metadata['days_since_last_change'] = days_since_change
            
            if days_since_change < self.cooldown_days:
                return ReEntryControlResult(
                    allowed=False,
                    reason=f"In cooldown period ({days_since_change}/{self.cooldown_days} days)",
                    metadata=metadata,
                    days_until_eligible=self.cooldown_days - days_since_change,
                    last_change_date=last_change_date
                )
        
        # Check 2: Minimum change threshold
        change_percentage = abs((proposed_bid - current_bid) / current_bid) if current_bid > 0 else 0
        metadata['change_percentage'] = change_percentage
        
        if change_percentage < self.min_change_threshold:
            return ReEntryControlResult(
                allowed=False,
                reason=f"Change too small ({change_percentage:.1%} < {self.min_change_threshold:.1%} threshold)",
                metadata=metadata
            )
        
        # Check 3: ACOS stability check
        if acos_history and len(acos_history) >= self.stability_window:
            stability_result = self._check_acos_stability(acos_history)
            metadata['acos_stability'] = stability_result
            
            if not stability_result['is_stable']:
                return ReEntryControlResult(
                    allowed=False,
                    reason=f"ACOS trend not stable yet (variance: {stability_result['variance']:.4f})",
                    metadata=metadata
                )
        
        # Check 4: Hysteresis bands
        if acos_history:
            smoothed_acos = self._calculate_smoothed_acos(acos_history)
            metadata['smoothed_acos'] = smoothed_acos
            
            hysteresis_result = self._check_hysteresis_bands(smoothed_acos)
            metadata['hysteresis_check'] = hysteresis_result
            
            if not hysteresis_result['should_adjust']:
                return ReEntryControlResult(
                    allowed=False,
                    reason=f"ACOS within hysteresis bands ({smoothed_acos:.2%} between {self.hysteresis_lower:.2%} and {self.hysteresis_upper:.2%})",
                    metadata=metadata
                )
        
        # Check 5: Oscillation detection
        if bid_change_history:
            oscillation_result = self._detect_oscillation(bid_change_history)
            metadata['oscillation_check'] = oscillation_result
            
            if oscillation_result['is_oscillating']:
                return ReEntryControlResult(
                    allowed=False,
                    reason=f"Bid oscillation detected ({oscillation_result['direction_changes']} direction changes in {self.oscillation_lookback} days)",
                    metadata=metadata
                )
        
        # All checks passed
        return ReEntryControlResult(
            allowed=True,
            reason="All re-entry control checks passed - safe to adjust",
            metadata=metadata
        )
    
    def _check_acos_stability(self, acos_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check if ACOS trend is stable over the stability window
        
        Args:
            acos_history: List of ACOS values with dates
            
        Returns:
            Dictionary with stability information
        """
        # Get most recent values for stability window
        recent_acos = [float(record.get('acos_value', 0)) for record in acos_history[:self.stability_window]]
        
        if len(recent_acos) < self.stability_window:
            return {
                'is_stable': False,
                'reason': 'Insufficient data',
                'variance': None,
                'mean': None
            }
        
        # Calculate variance
        mean_acos = sum(recent_acos) / len(recent_acos)
        variance = sum((x - mean_acos) ** 2 for x in recent_acos) / len(recent_acos)
        std_dev = variance ** 0.5
        
        # Consider stable if std deviation is less than 20% of mean
        is_stable = (std_dev / mean_acos) < 0.20 if mean_acos > 0 else False
        
        return {
            'is_stable': is_stable,
            'variance': variance,
            'std_dev': std_dev,
            'mean': mean_acos,
            'coefficient_of_variation': (std_dev / mean_acos) if mean_acos > 0 else None,
            'values': recent_acos
        }
    
    def _calculate_smoothed_acos(self, acos_history: List[Dict[str, Any]]) -> float:
        """
        Calculate smoothed ACOS using weighted moving average
        
        Args:
            acos_history: List of ACOS values sorted by date (newest first)
            
        Returns:
            Smoothed ACOS value
        """
        if not acos_history:
            return 0.0
        
        # Split into recent (last 7 days) and older (previous 7 days)
        recent_values = [float(record.get('acos_value', 0)) for record in acos_history[:7]]
        older_values = [float(record.get('acos_value', 0)) for record in acos_history[7:14]]
        
        if not recent_values:
            return 0.0
        
        avg_recent = sum(recent_values) / len(recent_values)
        
        if older_values:
            avg_older = sum(older_values) / len(older_values)
            smoothed_acos = (avg_recent * self.smoothing_recent + 
                           avg_older * self.smoothing_older)
        else:
            # Only recent data available
            smoothed_acos = avg_recent
        
        return smoothed_acos
    
    def _check_hysteresis_bands(self, smoothed_acos: float) -> Dict[str, Any]:
        """
        Check if ACOS is outside hysteresis bands to trigger adjustment
        
        Hysteresis bands prevent minor fluctuations from triggering changes.
        Only adjust if ACOS goes significantly above or below target.
        
        Args:
            smoothed_acos: Smoothed ACOS value
            
        Returns:
            Dictionary with hysteresis check result
        """
        should_adjust = False
        direction = None
        
        # If ACOS < lower band (6%), it's too good - consider increasing bid for more exposure
        if smoothed_acos < self.hysteresis_lower:
            should_adjust = True
            direction = 'increase'
        
        # If ACOS > upper band (12%), it's too high - need to decrease bid
        elif smoothed_acos > self.hysteresis_upper:
            should_adjust = True
            direction = 'decrease'
        
        return {
            'should_adjust': should_adjust,
            'direction': direction,
            'smoothed_acos': smoothed_acos,
            'lower_band': self.hysteresis_lower,
            'upper_band': self.hysteresis_upper,
            'target': self.acos_target
        }
    
    def _detect_oscillation(self, bid_change_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect if bid is oscillating (rapidly changing direction)
        
        Args:
            bid_change_history: List of recent bid changes
            
        Returns:
            Dictionary with oscillation detection results
        """
        if len(bid_change_history) < 2:
            return {
                'is_oscillating': False,
                'direction_changes': 0,
                'reason': 'Insufficient history'
            }
        
        # Count direction changes
        direction_changes = 0
        prev_direction = None
        
        for change in bid_change_history:
            change_amount = float(change.get('change_amount', 0))
            current_direction = 1 if change_amount > 0 else -1
            
            if prev_direction is not None and current_direction != prev_direction:
                direction_changes += 1
            
            prev_direction = current_direction
        
        is_oscillating = direction_changes >= self.oscillation_threshold
        
        return {
            'is_oscillating': is_oscillating,
            'direction_changes': direction_changes,
            'threshold': self.oscillation_threshold,
            'lookback_days': self.oscillation_lookback,
            'recent_changes': len(bid_change_history),
            'recommendation': 'Pause adjustments to allow stabilization' if is_oscillating else 'Normal'
        }
    
    def calculate_safe_bid_adjustment(self,
                                     current_bid: float,
                                     proposed_adjustment: float,
                                     bid_floor: float,
                                     bid_cap: float,
                                     max_adjustment_pct: float = 0.30) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate a safe bid adjustment respecting all limits
        
        Args:
            current_bid: Current bid value
            proposed_adjustment: Proposed adjustment percentage (e.g., 0.15 for +15%)
            bid_floor: Minimum allowed bid
            bid_cap: Maximum allowed bid
            max_adjustment_pct: Maximum adjustment per iteration (default 30%)
            
        Returns:
            Tuple of (new_bid, metadata)
        """
        # Cap the adjustment
        capped_adjustment = max(-max_adjustment_pct, min(max_adjustment_pct, proposed_adjustment))
        
        # Calculate new bid
        new_bid = current_bid * (1 + capped_adjustment)
        
        # Apply floor and cap
        new_bid = max(bid_floor, min(bid_cap, new_bid))
        
        # Calculate actual adjustment achieved
        actual_adjustment = (new_bid - current_bid) / current_bid if current_bid > 0 else 0
        
        metadata = {
            'current_bid': current_bid,
            'proposed_adjustment': proposed_adjustment,
            'capped_adjustment': capped_adjustment,
            'new_bid': new_bid,
            'actual_adjustment': actual_adjustment,
            'bid_floor': bid_floor,
            'bid_cap': bid_cap,
            'was_capped': abs(proposed_adjustment) > max_adjustment_pct,
            'hit_floor': new_bid == bid_floor,
            'hit_cap': new_bid == bid_cap
        }
        
        return new_bid, metadata


class BidChangeTracker:
    """
    Utility class for tracking and logging bid changes
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def create_change_record(self,
                           entity_type: str,
                           entity_id: int,
                           entity_name: str,
                           old_bid: float,
                           new_bid: float,
                           reason: str,
                           acos: Optional[float] = None,
                           roas: Optional[float] = None,
                           ctr: Optional[float] = None,
                           conversions: Optional[int] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a bid change record for logging to database
        
        Args:
            entity_type: Type of entity (keyword, ad_group, campaign)
            entity_id: Entity identifier
            entity_name: Entity name
            old_bid: Previous bid value
            new_bid: New bid value
            reason: Reason for change
            acos: ACOS at time of change
            roas: ROAS at time of change
            ctr: CTR at time of change
            conversions: Conversions at time of change
            metadata: Additional metadata
            
        Returns:
            Dictionary ready for database insertion
        """
        change_amount = new_bid - old_bid
        change_percentage = (change_amount / old_bid * 100) if old_bid > 0 else 0
        
        record = {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_name': entity_name,
            'change_date': datetime.now(),
            'old_bid': old_bid,
            'new_bid': new_bid,
            'change_amount': change_amount,
            'change_percentage': change_percentage,
            'reason': reason,
            'triggered_by': 'ai_rule_engine',
            'acos_at_change': acos,
            'roas_at_change': roas,
            'ctr_at_change': ctr,
            'conversions_at_change': conversions,
            'metadata': metadata or {}
        }
        
        self.logger.info(
            f"Bid change: {entity_type} {entity_id} ({entity_name}) - "
            f"${old_bid:.2f} → ${new_bid:.2f} ({change_percentage:+.1f}%) - {reason}"
        )
        
        return record

