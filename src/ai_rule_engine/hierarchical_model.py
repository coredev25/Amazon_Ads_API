"""
Hierarchical/Cluster-based Model for Cross-ASIN Transfer Learning (#18)

Implements hierarchical models that learn from ASIN clusters to improve predictions
for low-volume ASINs by transferring knowledge from related products.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


class HierarchicalModelTrainer:
    """
    Hierarchical model trainer for cross-ASIN transfer learning (#18)
    
    Uses ASIN-level cluster features (category, price_tier, fulfillment) to enable
    knowledge transfer from high-volume ASINs to low-volume ASINs.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize hierarchical model trainer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_hierarchical = config.get('enable_hierarchical_models', True)
        self.cluster_models: Dict[str, Any] = {}  # category -> model
        self.global_model = None
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
    
    def _extract_cluster_features(self, outcome: 'PerformanceOutcome') -> Dict[str, Any]:
        """
        Extract ASIN cluster features for hierarchical modeling (#18)
        
        Args:
            outcome: Performance outcome
            
        Returns:
            Dictionary with cluster identifiers
        """
        before_metrics = outcome.before_metrics or {}
        
        return {
            'category': before_metrics.get('entity_category', 'unknown'),
            'price_tier': before_metrics.get('entity_price_tier', 'mid'),
            'fulfillment': before_metrics.get('entity_fulfillment', 'FBA'),
            'asin': before_metrics.get('asin') or before_metrics.get('product_asin')
        }
    
    def _get_cluster_key(self, cluster_features: Dict[str, Any]) -> str:
        """
        Generate cluster key from features
        
        Args:
            cluster_features: Cluster feature dictionary
            
        Returns:
            Cluster key string
        """
        # Use category and price_tier as primary cluster identifiers
        category = cluster_features.get('category', 'unknown')
        price_tier = cluster_features.get('price_tier', 'mid')
        return f"{category}_{price_tier}"
    
    def train_hierarchical_model(self, outcomes: List['PerformanceOutcome'],
                                 base_features_fn) -> Dict[str, Any]:
        """
        Train hierarchical model with cluster-based learning (#18)
        
        Args:
            outcomes: List of performance outcomes
            base_features_fn: Function to extract base features from outcome
            
        Returns:
            Training results
        """
        if not SKLEARN_AVAILABLE:
            self.logger.warning("scikit-learn not available, skipping hierarchical model")
            return {'status': 'skipped', 'reason': 'sklearn_not_available'}
        
        if not self.enable_hierarchical:
            return {'status': 'skipped', 'reason': 'hierarchical_models_disabled'}
        
        self.logger.info(f"Training hierarchical model with {len(outcomes)} outcomes")
        
        # Group outcomes by cluster
        cluster_outcomes: Dict[str, List['PerformanceOutcome']] = {}
        for outcome in outcomes:
            if not outcome.eligible_for_training:
                continue
            
            cluster_features = self._extract_cluster_features(outcome)
            cluster_key = self._get_cluster_key(cluster_features)
            
            if cluster_key not in cluster_outcomes:
                cluster_outcomes[cluster_key] = []
            cluster_outcomes[cluster_key].append(outcome)
        
        self.logger.info(f"Found {len(cluster_outcomes)} clusters")
        
        # Train global model on all data
        all_features = []
        all_labels = []
        for outcome in outcomes:
            if not outcome.eligible_for_training:
                continue
            features = base_features_fn(outcome)
            if features:
                all_features.append(features)
                all_labels.append(1 if outcome.outcome == 'success' else 0)
        
        if len(all_features) < 50:
            return {'status': 'skipped', 'reason': 'insufficient_data'}
        
        # Train global model
        X_global = np.array(all_features)
        y_global = np.array(all_labels)
        
        if self.scaler:
            X_global = self.scaler.fit_transform(X_global)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X_global, y_global, test_size=0.2, random_state=42
        )
        
        self.global_model = GradientBoostingClassifier(
            n_estimators=100, random_state=42, max_depth=5
        )
        self.global_model.fit(X_train, y_train)
        
        global_test_acc = accuracy_score(y_test, self.global_model.predict(X_test))
        global_test_auc = roc_auc_score(y_test, self.global_model.predict_proba(X_test)[:, 1])
        
        # Train cluster-specific models for clusters with sufficient data
        cluster_results = {}
        for cluster_key, cluster_outcomes_list in cluster_outcomes.items():
            if len(cluster_outcomes_list) < 20:  # Need at least 20 samples per cluster
                continue
            
            cluster_features = []
            cluster_labels = []
            for outcome in cluster_outcomes_list:
                features = base_features_fn(outcome)
                if features:
                    cluster_features.append(features)
                    cluster_labels.append(1 if outcome.outcome == 'success' else 0)
            
            if len(cluster_features) < 20:
                continue
            
            X_cluster = np.array(cluster_features)
            y_cluster = np.array(cluster_labels)
            
            if self.scaler:
                X_cluster = self.scaler.transform(X_cluster)
            
            X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
                X_cluster, y_cluster, test_size=0.2, random_state=42
            )
            
            cluster_model = GradientBoostingClassifier(
                n_estimators=50, random_state=42, max_depth=4
            )
            cluster_model.fit(X_train_c, y_train_c)
            
            cluster_test_acc = accuracy_score(y_test_c, cluster_model.predict(X_test_c))
            cluster_test_auc = roc_auc_score(y_test_c, cluster_model.predict_proba(X_test_c)[:, 1])
            
            self.cluster_models[cluster_key] = cluster_model
            cluster_results[cluster_key] = {
                'samples': len(cluster_outcomes_list),
                'test_accuracy': cluster_test_acc,
                'test_auc': cluster_test_auc
            }
        
        results = {
            'status': 'success',
            'global_model': {
                'test_accuracy': global_test_acc,
                'test_auc': global_test_auc
            },
            'cluster_models': cluster_results,
            'num_clusters': len(self.cluster_models)
        }
        
        self.logger.info(
            f"Hierarchical model trained: {len(self.cluster_models)} cluster models, "
            f"global AUC={global_test_auc:.3f}"
        )
        
        return results
    
    def predict_with_hierarchy(self, features: List[float],
                              cluster_features: Dict[str, Any]) -> float:
        """
        Predict using hierarchical model (cluster model if available, else global) (#18)
        
        Args:
            features: Feature vector
            cluster_features: Cluster feature dictionary
            
        Returns:
            Prediction probability
        """
        if not self.global_model:
            return 0.5  # Fallback
        
        cluster_key = self._get_cluster_key(cluster_features)
        
        # Use cluster model if available, else global model
        model = self.cluster_models.get(cluster_key, self.global_model)
        
        try:
            X = np.array([features])
            if self.scaler:
                X = self.scaler.transform(X)
            
            proba = model.predict_proba(X)[0, 1]
            return float(proba)
        except Exception as e:
            self.logger.warning(f"Error in hierarchical prediction: {e}")
            return 0.5

