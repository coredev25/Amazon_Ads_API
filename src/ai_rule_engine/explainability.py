"""
Model Explainability with SHAP Values (#29)

Implements:
- SHAP (SHapley Additive exPlanations) for model predictions
- Feature importance analysis
- Prediction explanations for human-readable reasons
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    import shap
    SHAP_AVAILABLE = True
except Exception:
    SHAP_AVAILABLE = False
    shap = None

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


class ModelExplainer:
    """
    Model explainability using SHAP values (#29)
    Provides human-readable explanations for ML-driven actions
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_explainability = config.get('enable_explainability', False)
        self.explainer = None
        self.feature_names = []
        self.model = None
    
    def initialize_explainer(self, model, training_data: np.ndarray, feature_names: List[str]) -> bool:
        """
        Initialize SHAP explainer with model and training data
        
        Args:
            model: Trained model (sklearn or compatible)
            training_data: Training data used to train model
            feature_names: Names of features
            
        Returns:
            True if successful
        """
        if not self.enable_explainability or not SHAP_AVAILABLE:
            return False
        
        try:
            self.model = model
            self.feature_names = feature_names
            
            # Choose explainer based on model type
            if isinstance(model, (RandomForestClassifier, GradientBoostingClassifier)):
                # Tree-based models: use TreeExplainer (fast and exact)
                self.explainer = shap.TreeExplainer(model)
            elif isinstance(model, LogisticRegression):
                # Linear models: use LinearExplainer (fast)
                self.explainer = shap.LinearExplainer(model, training_data)
            else:
                # Generic models: use KernelExplainer (slower but works for any model)
                # Use subset of training data for speed
                background_data = training_data[:100] if len(training_data) > 100 else training_data
                self.explainer = shap.KernelExplainer(model.predict_proba, background_data)
            
            self.logger.info(f"SHAP explainer initialized for {type(model).__name__}")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing SHAP explainer: {e}")
            return False
    
    def explain_prediction(self, instance: np.ndarray, top_k: int = 5) -> Dict[str, Any]:
        """
        Generate SHAP explanation for a single prediction
        
        Args:
            instance: Feature vector for prediction (1D array)
            top_k: Number of top features to highlight
            
        Returns:
            Explanation dictionary with SHAP values and human-readable reasons
        """
        if not self.explainer or not SHAP_AVAILABLE:
            return {
                'status': 'unavailable',
                'reason': 'explainer_not_initialized_or_shap_unavailable'
            }
        
        try:
            # Reshape instance if needed
            if instance.ndim == 1:
                instance = instance.reshape(1, -1)
            
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(instance)
            
            # Handle multi-class models (use class 1 for binary classification)
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # Use positive class
            
            # Get feature contributions
            feature_contributions = {}
            shap_array = shap_values[0] if shap_values.ndim > 1 else shap_values
            
            for i, feature_name in enumerate(self.feature_names):
                if i < len(shap_array):
                    feature_contributions[feature_name] = float(shap_array[i])
            
            # Sort by absolute contribution
            sorted_features = sorted(
                feature_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            
            # Get top K features
            top_features = sorted_features[:top_k]
            
            # Generate human-readable explanation
            explanation_parts = []
            for feature_name, contribution in top_features:
                direction = "increases" if contribution > 0 else "decreases"
                magnitude = abs(contribution)
                explanation_parts.append(
                    f"{feature_name} {direction} success probability by {magnitude:.3f}"
                )
            
            # Calculate base value and prediction
            base_value = float(self.explainer.expected_value[1] if isinstance(self.explainer.expected_value, np.ndarray) else self.explainer.expected_value)
            prediction = float(self.model.predict_proba(instance)[0, 1])
            
            return {
                'status': 'success',
                'prediction': prediction,
                'base_value': base_value,
                'feature_contributions': feature_contributions,
                'top_features': {name: contrib for name, contrib in top_features},
                'explanation': '; '.join(explanation_parts),
                'shap_values': shap_values.tolist() if hasattr(shap_values, 'tolist') else shap_values
            }
        except Exception as e:
            self.logger.error(f"Error generating SHAP explanation: {e}")
            return {
                'status': 'error',
                'reason': str(e)
            }
    
    def explain_batch(self, instances: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Generate explanations for multiple predictions
        
        Args:
            instances: Feature vectors (2D array)
            top_k: Number of top features per prediction
            
        Returns:
            List of explanation dictionaries
        """
        explanations = []
        for i in range(len(instances)):
            explanation = self.explain_prediction(instances[i], top_k)
            explanation['instance_id'] = i
            explanations.append(explanation)
        return explanations
    
    def get_feature_importance(self, training_data: np.ndarray, num_samples: int = 100) -> Dict[str, float]:
        """
        Calculate global feature importance using SHAP
        
        Args:
            training_data: Training data
            num_samples: Number of samples to use for importance calculation
            
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if not self.explainer or not SHAP_AVAILABLE:
            return {}
        
        try:
            # Sample subset for speed
            sample_indices = np.random.choice(len(training_data), min(num_samples, len(training_data)), replace=False)
            sample_data = training_data[sample_indices]
            
            # Calculate SHAP values
            shap_values = self.explainer.shap_values(sample_data)
            
            # Handle multi-class
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
            
            # Calculate mean absolute SHAP value per feature
            importance = {}
            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            
            for i, feature_name in enumerate(self.feature_names):
                if i < len(mean_abs_shap):
                    importance[feature_name] = float(mean_abs_shap[i])
            
            # Normalize to sum to 1
            total = sum(importance.values())
            if total > 0:
                importance = {k: v / total for k, v in importance.items()}
            
            return importance
        except Exception as e:
            self.logger.error(f"Error calculating feature importance: {e}")
            return {}
    
    def save_explanation(self, explanation: Dict[str, Any], entity_id: int, 
                        entity_type: str, recommendation_id: str) -> bool:
        """
        Save explanation to database for later review
        
        Args:
            explanation: Explanation dictionary
            entity_id: Entity ID
            entity_type: Entity type
            recommendation_id: Recommendation ID
            
        Returns:
            True if successful
        """
        # This would save to a database table
        # For now, just log it
        self.logger.info(
            f"Explanation for {entity_type} {entity_id} (rec: {recommendation_id}): "
            f"{explanation.get('explanation', 'N/A')}"
        )
        return True
    
    def generate_summary_report(self, explanations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary report from multiple explanations
        
        Args:
            explanations: List of explanation dictionaries
            
        Returns:
            Summary report
        """
        if not explanations:
            return {}
        
        # Aggregate feature contributions
        feature_totals = {}
        for exp in explanations:
            if exp.get('status') == 'success':
                for feature, contribution in exp.get('feature_contributions', {}).items():
                    feature_totals[feature] = feature_totals.get(feature, 0) + abs(contribution)
        
        # Sort by total contribution
        top_features = sorted(feature_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_explanations': len(explanations),
            'successful_explanations': sum(1 for e in explanations if e.get('status') == 'success'),
            'top_contributing_features': {name: total for name, total in top_features},
            'avg_prediction': np.mean([e.get('prediction', 0) for e in explanations if e.get('status') == 'success'])
        }

