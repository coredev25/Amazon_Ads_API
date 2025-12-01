"""
Cross-Account / Portfolio Learning (#28)

Implements:
- Pool data across accounts with privacy controls
- Portfolio-level pattern learning
- Federated learning support
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


class PrivacyController:
    """
    Privacy controls for cross-account data sharing (#28)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_differential_privacy = config.get('enable_differential_privacy', False)
        self.epsilon = config.get('differential_privacy_epsilon', 1.0)  # Privacy budget
        self.min_accounts_for_pooling = config.get('min_accounts_for_pooling', 3)
    
    def anonymize_entity_id(self, entity_id: int, account_id: str) -> str:
        """
        Anonymize entity ID using account-specific salt
        
        Args:
            entity_id: Original entity ID
            account_id: Account identifier
            
        Returns:
            Anonymized entity ID hash
        """
        salt = self.config.get('privacy_salt', 'default_salt')
        combined = f"{account_id}_{entity_id}_{salt}"
        hash_obj = hashlib.sha256(combined.encode())
        return hash_obj.hexdigest()[:16]  # Truncate to 16 chars
    
    def add_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """
        Add Laplace noise for differential privacy
        
        Args:
            value: Original value
            sensitivity: Sensitivity of the function
            
        Returns:
            Noisy value
        """
        if not self.enable_differential_privacy:
            return value
        
        try:
            import random
            scale = sensitivity / self.epsilon
            noise = np.random.laplace(0, scale)
            return value + noise
        except Exception:
            return value
    
    def aggregate_with_privacy(self, values: List[float], aggregation_type: str = 'mean') -> float:
        """
        Aggregate values with privacy protection
        
        Args:
            values: List of values to aggregate
            aggregation_type: 'mean', 'sum', 'median'
            
        Returns:
            Aggregated value with noise if differential privacy enabled
        """
        if not values:
            return 0.0
        
        if aggregation_type == 'mean':
            result = np.mean(values)
        elif aggregation_type == 'sum':
            result = np.sum(values)
        elif aggregation_type == 'median':
            result = np.median(values)
        else:
            result = np.mean(values)
        
        # Add noise if differential privacy enabled
        if self.enable_differential_privacy:
            sensitivity = 1.0 if aggregation_type == 'mean' else len(values)
            result = self.add_noise(result, sensitivity)
        
        return float(result)


class PortfolioLearningEngine:
    """
    Cross-account / portfolio learning engine (#28)
    Learns patterns across multiple accounts while preserving privacy
    """
    
    def __init__(self, config: Dict[str, Any], db_connector=None):
        self.config = config
        self.db = db_connector
        self.logger = logging.getLogger(__name__)
        self.enable_portfolio_learning = config.get('enable_portfolio_learning', False)
        self.privacy_controller = PrivacyController(config)
        self.portfolio_model = None
        self.scaler = None
    
    def aggregate_portfolio_features(self, account_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Aggregate features across accounts in portfolio
        
        Args:
            account_data: List of account-level feature dictionaries
            
        Returns:
            Aggregated portfolio features
        """
        if not account_data:
            return {}
        
        # Aggregate common features
        aggregated = {}
        
        # Aggregate metrics with privacy
        acos_values = [a.get('avg_acos', 0) for a in account_data if a.get('avg_acos')]
        roas_values = [a.get('avg_roas', 0) for a in account_data if a.get('avg_roas')]
        ctr_values = [a.get('avg_ctr', 0) for a in account_data if a.get('avg_ctr')]
        
        aggregated['portfolio_avg_acos'] = self.privacy_controller.aggregate_with_privacy(acos_values, 'mean')
        aggregated['portfolio_avg_roas'] = self.privacy_controller.aggregate_with_privacy(roas_values, 'mean')
        aggregated['portfolio_avg_ctr'] = self.privacy_controller.aggregate_with_privacy(ctr_values, 'mean')
        
        # Aggregate counts
        total_accounts = len(account_data)
        aggregated['portfolio_num_accounts'] = total_accounts
        
        # Category distribution (anonymized)
        category_counts = {}
        for account in account_data:
            category = account.get('primary_category', 'unknown')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Add top categories (with noise if privacy enabled)
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (category, count) in enumerate(top_categories):
            noisy_count = self.privacy_controller.add_noise(float(count), sensitivity=1.0)
            aggregated[f'portfolio_category_{i+1}_share'] = noisy_count / total_accounts if total_accounts > 0 else 0
        
        return aggregated
    
    def train_portfolio_model(self, portfolio_outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train model on portfolio-level aggregated data
        
        Args:
            portfolio_outcomes: List of outcomes with portfolio features
            
        Returns:
            Training results
        """
        if not self.enable_portfolio_learning or not SKLEARN_AVAILABLE:
            return {'status': 'skipped', 'reason': 'portfolio_learning_disabled_or_sklearn_unavailable'}
        
        if len(portfolio_outcomes) < 50:
            return {'status': 'skipped', 'reason': 'insufficient_portfolio_data'}
        
        try:
            # Extract features and labels
            features = []
            labels = []
            
            for outcome in portfolio_outcomes:
                feature_vector = [
                    outcome.get('portfolio_avg_acos', 0),
                    outcome.get('portfolio_avg_roas', 0),
                    outcome.get('portfolio_avg_ctr', 0),
                    outcome.get('portfolio_num_accounts', 0),
                    outcome.get('entity_acos', 0),
                    outcome.get('entity_roas', 0),
                    outcome.get('adjustment_percentage', 0)
                ]
                
                # Add category shares
                for i in range(5):
                    feature_vector.append(outcome.get(f'portfolio_category_{i+1}_share', 0))
                
                features.append(feature_vector)
                labels.append(1 if outcome.get('outcome') == 'success' else 0)
            
            # Normalize features
            self.scaler = StandardScaler()
            features_scaled = self.scaler.fit_transform(features)
            
            # Train model
            self.portfolio_model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.portfolio_model.fit(features_scaled, labels)
            
            # Evaluate
            predictions = self.portfolio_model.predict(features_scaled)
            accuracy = np.mean(predictions == labels)
            
            return {
                'status': 'success',
                'model_type': 'portfolio_random_forest',
                'accuracy': float(accuracy),
                'num_samples': len(portfolio_outcomes)
            }
        except Exception as e:
            self.logger.error(f"Error training portfolio model: {e}")
            return {'status': 'error', 'reason': str(e)}
    
    def predict_with_portfolio_context(self, entity_features: Dict[str, Any],
                                      portfolio_features: Dict[str, Any]) -> float:
        """
        Predict success probability using both entity and portfolio features
        
        Args:
            entity_features: Entity-specific features
            portfolio_features: Portfolio-level aggregated features
            
        Returns:
            Success probability (0.0 to 1.0)
        """
        if not self.portfolio_model:
            return 0.5  # Default
        
        try:
            # Combine features
            feature_vector = [
                portfolio_features.get('portfolio_avg_acos', 0),
                portfolio_features.get('portfolio_avg_roas', 0),
                portfolio_features.get('portfolio_avg_ctr', 0),
                portfolio_features.get('portfolio_num_accounts', 0),
                entity_features.get('acos', 0),
                entity_features.get('roas', 0),
                entity_features.get('adjustment_percentage', 0)
            ]
            
            # Add category shares
            for i in range(5):
                feature_vector.append(portfolio_features.get(f'portfolio_category_{i+1}_share', 0))
            
            # Normalize and predict
            feature_vector_scaled = self.scaler.transform([feature_vector])
            probability = self.portfolio_model.predict_proba(feature_vector_scaled)[0, 1]
            
            return float(probability)
        except Exception as e:
            self.logger.warning(f"Error in portfolio prediction: {e}")
            return 0.5
    
    def get_portfolio_insights(self, account_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate portfolio-level insights
        
        Args:
            account_data: List of account data
            
        Returns:
            Portfolio insights
        """
        if not account_data:
            return {}
        
        insights = {
            'total_accounts': len(account_data),
            'avg_performance': {},
            'best_practices': [],
            'warnings': []
        }
        
        # Calculate averages
        acos_values = [a.get('avg_acos', 0) for a in account_data if a.get('avg_acos', 0) > 0]
        roas_values = [a.get('avg_roas', 0) for a in account_data if a.get('avg_roas', 0) > 0]
        
        if acos_values:
            insights['avg_performance']['acos'] = float(np.mean(acos_values))
        if roas_values:
            insights['avg_performance']['roas'] = float(np.mean(roas_values))
        
        # Identify best practices (top performers)
        if roas_values:
            threshold = np.percentile(roas_values, 75)
            top_performers = [a for a in account_data if a.get('avg_roas', 0) >= threshold]
            if top_performers:
                insights['best_practices'].append(f"{len(top_performers)} accounts performing above 75th percentile")
        
        return insights

