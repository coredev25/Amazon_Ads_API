"""
Multi-Armed Bandits & Counterfactual Evaluation (#27)

Implements:
- Multi-armed bandit algorithms for exploration vs exploitation
- Counterfactual evaluation framework
- Thompson Sampling and UCB algorithms
"""

import logging
import random
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False
    stats = None


@dataclass
class Arm:
    """Represents an arm in the multi-armed bandit"""
    arm_id: str
    strategy: str  # e.g., 'aggressive', 'conservative', 'moderate'
    parameters: Dict[str, Any]
    successes: int = 0
    failures: int = 0
    total_pulls: int = 0
    last_updated: Optional[datetime] = None


class ThompsonSamplingBandit:
    """
    Thompson Sampling multi-armed bandit for exploration vs exploitation (#27)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_bandits = config.get('enable_multi_armed_bandits', False)
        self.arms: Dict[str, Arm] = {}
        self.alpha_prior = config.get('bandit_alpha_prior', 1.0)  # Beta prior alpha
        self.beta_prior = config.get('bandit_beta_prior', 1.0)  # Beta prior beta
    
    def add_arm(self, arm_id: str, strategy: str, parameters: Dict[str, Any]) -> None:
        """Add a new arm to the bandit"""
        if arm_id not in self.arms:
            self.arms[arm_id] = Arm(
                arm_id=arm_id,
                strategy=strategy,
                parameters=parameters
            )
            self.logger.info(f"Added bandit arm: {arm_id} ({strategy})")
    
    def select_arm(self) -> Optional[str]:
        """
        Select arm using Thompson Sampling
        
        Returns:
            Selected arm ID or None
        """
        if not self.enable_bandits or not self.arms:
            return None
        
        if not SCIPY_AVAILABLE:
            # Fallback to random selection
            return random.choice(list(self.arms.keys()))
        
        # Thompson Sampling: sample from Beta distribution for each arm
        samples = {}
        for arm_id, arm in self.arms.items():
            # Beta distribution: Beta(alpha + successes, beta + failures)
            alpha = self.alpha_prior + arm.successes
            beta = self.beta_prior + arm.failures
            
            # Sample from Beta distribution
            sample = stats.beta.rvs(alpha, beta)
            samples[arm_id] = sample
        
        # Select arm with highest sample
        selected_arm = max(samples.items(), key=lambda x: x[1])[0]
        return selected_arm
    
    def update_arm(self, arm_id: str, success: bool) -> None:
        """Update arm statistics after observing outcome"""
        if arm_id in self.arms:
            arm = self.arms[arm_id]
            if success:
                arm.successes += 1
            else:
                arm.failures += 1
            arm.total_pulls += 1
            arm.last_updated = datetime.now()
            
            success_rate = arm.successes / arm.total_pulls if arm.total_pulls > 0 else 0
            self.logger.debug(f"Updated arm {arm_id}: {arm.successes}/{arm.total_pulls} ({success_rate:.2%})")
    
    def get_arm_statistics(self) -> Dict[str, Any]:
        """Get statistics for all arms"""
        stats = {}
        for arm_id, arm in self.arms.items():
            success_rate = arm.successes / arm.total_pulls if arm.total_pulls > 0 else 0
            stats[arm_id] = {
                'strategy': arm.strategy,
                'successes': arm.successes,
                'failures': arm.failures,
                'total_pulls': arm.total_pulls,
                'success_rate': success_rate,
                'parameters': arm.parameters
            }
        return stats


class UCBBandit:
    """
    Upper Confidence Bound (UCB) multi-armed bandit (#27)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_bandits = config.get('enable_multi_armed_bandits', False)
        self.arms: Dict[str, Arm] = {}
        self.c = config.get('ucb_exploration_constant', 2.0)  # Exploration constant
        self.total_pulls = 0
    
    def add_arm(self, arm_id: str, strategy: str, parameters: Dict[str, Any]) -> None:
        """Add a new arm to the bandit"""
        if arm_id not in self.arms:
            self.arms[arm_id] = Arm(
                arm_id=arm_id,
                strategy=strategy,
                parameters=parameters
            )
    
    def select_arm(self) -> Optional[str]:
        """
        Select arm using UCB algorithm
        
        Returns:
            Selected arm ID or None
        """
        if not self.enable_bandits or not self.arms:
            return None
        
        # If any arm hasn't been pulled, select it
        for arm_id, arm in self.arms.items():
            if arm.total_pulls == 0:
                return arm_id
        
        # Calculate UCB for each arm
        ucb_values = {}
        for arm_id, arm in self.arms.items():
            if arm.total_pulls == 0:
                ucb_values[arm_id] = float('inf')
            else:
                success_rate = arm.successes / arm.total_pulls
                confidence_interval = self.c * math.sqrt(math.log(self.total_pulls) / arm.total_pulls)
                ucb_values[arm_id] = success_rate + confidence_interval
        
        # Select arm with highest UCB
        selected_arm = max(ucb_values.items(), key=lambda x: x[1])[0]
        return selected_arm
    
    def update_arm(self, arm_id: str, success: bool) -> None:
        """Update arm statistics after observing outcome"""
        if arm_id in self.arms:
            arm = self.arms[arm_id]
            if success:
                arm.successes += 1
            else:
                arm.failures += 1
            arm.total_pulls += 1
            arm.last_updated = datetime.now()
            self.total_pulls += 1


class CounterfactualEvaluator:
    """
    Counterfactual evaluation framework (#27)
    Estimates what would have happened without the intervention
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_counterfactual = config.get('enable_counterfactual_evaluation', False)
    
    def estimate_counterfactual_outcome(self, 
                                       treated_entity: Dict[str, Any],
                                       control_entities: List[Dict[str, Any]],
                                       before_metrics: Dict[str, float],
                                       after_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Estimate counterfactual outcome using control group
        
        Args:
            treated_entity: Entity that received treatment
            control_entities: Similar entities that did not receive treatment
            before_metrics: Metrics before treatment
            after_metrics: Metrics after treatment
            
        Returns:
            Counterfactual analysis results
        """
        if not self.enable_counterfactual:
            return {'status': 'skipped', 'reason': 'counterfactual_disabled'}
        
        try:
            # Calculate average control group change
            control_changes = []
            for control in control_entities:
                control_before = control.get('before_metrics', {})
                control_after = control.get('after_metrics', {})
                
                if control_before and control_after:
                    control_roas_change = control_after.get('roas', 0) - control_before.get('roas', 0)
                    control_changes.append(control_roas_change)
            
            avg_control_change = np.mean(control_changes) if control_changes else 0.0
            
            # Calculate actual change
            actual_change = after_metrics.get('roas', 0) - before_metrics.get('roas', 0)
            
            # Counterfactual: what would have happened without treatment
            counterfactual_outcome = before_metrics.get('roas', 0) + avg_control_change
            
            # Treatment effect
            treatment_effect = actual_change - avg_control_change
            
            return {
                'status': 'success',
                'actual_outcome': after_metrics.get('roas', 0),
                'counterfactual_outcome': float(counterfactual_outcome),
                'treatment_effect': float(treatment_effect),
                'actual_change': float(actual_change),
                'control_change': float(avg_control_change),
                'method': 'control_group_comparison'
            }
        except Exception as e:
            self.logger.error(f"Error in counterfactual evaluation: {e}")
            return {'status': 'error', 'reason': str(e)}
    
    def synthetic_control_method(self,
                                treated_entity: Dict[str, Any],
                                donor_pool: List[Dict[str, Any]],
                                pre_period: List[Dict[str, Any]],
                                post_period: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthetic control method for counterfactual estimation
        
        Args:
            treated_entity: Entity that received treatment
            donor_pool: Pool of similar entities (donors)
            pre_period: Pre-treatment period data
            post_period: Post-treatment period data
            
        Returns:
            Synthetic control analysis results
        """
        if not self.enable_counterfactual:
            return {'status': 'skipped', 'reason': 'counterfactual_disabled'}
        
        try:
            # Simplified synthetic control (in production, would use optimization)
            # Match treated entity to weighted combination of donors
            
            treated_pre = np.mean([d.get('roas', 0) for d in pre_period])
            treated_post = np.mean([d.get('roas', 0) for d in post_period])
            
            # Calculate weights based on pre-period similarity
            weights = []
            for donor in donor_pool:
                donor_pre = np.mean([d.get('roas', 0) for d in pre_period if d.get('entity_id') == donor.get('entity_id')])
                similarity = 1.0 / (1.0 + abs(treated_pre - donor_pre))
                weights.append(similarity)
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            else:
                weights = [1.0 / len(donor_pool)] * len(donor_pool)
            
            # Construct synthetic control
            synthetic_pre = sum(w * np.mean([d.get('roas', 0) for d in pre_period if d.get('entity_id') == donor.get('entity_id')]) 
                               for w, donor in zip(weights, donor_pool))
            synthetic_post = sum(w * np.mean([d.get('roas', 0) for d in post_period if d.get('entity_id') == donor.get('entity_id')]) 
                                for w, donor in zip(weights, donor_pool))
            
            # Treatment effect
            treatment_effect = (treated_post - treated_pre) - (synthetic_post - synthetic_pre)
            
            return {
                'status': 'success',
                'treatment_effect': float(treatment_effect),
                'synthetic_control_pre': float(synthetic_pre),
                'synthetic_control_post': float(synthetic_post),
                'treated_pre': float(treated_pre),
                'treated_post': float(treated_post),
                'method': 'synthetic_control'
            }
        except Exception as e:
            self.logger.error(f"Error in synthetic control: {e}")
            return {'status': 'error', 'reason': str(e)}

