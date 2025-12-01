"""
Advanced Models: Time-Series & Causal Inference (#26)

Implements:
- RNN/LSTM models for time-series prediction
- Causal inference models for estimating true effect of bid changes
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    import pandas as pd
    ADVANCED_ML_AVAILABLE = True
except Exception:
    ADVANCED_ML_AVAILABLE = False
    pd = None

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False
    torch = None
    nn = None


class TimeSeriesLSTM(nn.Module):
    """
    LSTM model for time-series prediction of bid success
    """
    
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2, dropout: float = 0.2):
        super(TimeSeriesLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        lstm_out, _ = self.lstm(x)
        # Take the last output
        last_output = lstm_out[:, -1, :]
        output = self.fc(last_output)
        return self.sigmoid(output)


class TimeSeriesModelTrainer:
    """
    Trains time-series models (LSTM/RNN) for better short-term predictions (#26)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_time_series = config.get('enable_time_series_models', False)
        self.sequence_length = config.get('time_series_sequence_length', 14)  # 14 days
        self.model = None
        self.scaler = None
        self.device = torch.device('cuda' if torch.cuda.is_available() and config.get('use_gpu', False) else 'cpu') if TORCH_AVAILABLE else None
    
    def prepare_time_series_data(self, performance_history: List[Dict[str, Any]], 
                                sequence_length: int = 14) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare time-series sequences from performance history
        
        Args:
            performance_history: List of daily performance records
            sequence_length: Length of input sequence
            
        Returns:
            Tuple of (sequences, targets)
        """
        if not ADVANCED_ML_AVAILABLE or not performance_history:
            return np.array([]), np.array([])
        
        # Sort by date
        sorted_data = sorted(performance_history, key=lambda x: x.get('report_date', datetime.now()))
        
        if len(sorted_data) < sequence_length + 1:
            return np.array([]), np.array([])
        
        sequences = []
        targets = []
        
        # Extract features for each day
        feature_cols = ['acos', 'roas', 'ctr', 'cost', 'sales', 'conversions', 'clicks', 'impressions']
        
        for i in range(len(sorted_data) - sequence_length):
            sequence = []
            for j in range(sequence_length):
                day_data = sorted_data[i + j]
                features = [
                    day_data.get('acos', 0),
                    day_data.get('roas', 0),
                    day_data.get('ctr', 0),
                    day_data.get('cost', 0),
                    day_data.get('sales', 0),
                    day_data.get('conversions', 0),
                    day_data.get('clicks', 0),
                    day_data.get('impressions', 0)
                ]
                sequence.append(features)
            
            # Target is next day's success (simplified - would need actual outcome)
            next_day = sorted_data[i + sequence_length]
            target = 1.0 if (next_day.get('roas', 0) > 2.0 and next_day.get('acos', 1.0) < 0.15) else 0.0
            # In production, this would use actual outcome labels
            
            sequences.append(sequence)
            targets.append(target)
        
        return np.array(sequences), np.array(targets)
    
    def train_lstm_model(self, performance_histories: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Train LSTM model on time-series data
        
        Args:
            performance_histories: List of performance histories for different entities
            
        Returns:
            Training results
        """
        if not TORCH_AVAILABLE or not self.enable_time_series:
            return {'status': 'skipped', 'reason': 'torch_not_available_or_disabled'}
        
        self.logger.info(f"Training LSTM model on {len(performance_histories)} time-series")
        
        # Prepare all sequences
        all_sequences = []
        all_targets = []
        
        for history in performance_histories:
            sequences, targets = self.prepare_time_series_data(history, self.sequence_length)
            if len(sequences) > 0:
                all_sequences.append(sequences)
                all_targets.append(targets)
        
        if not all_sequences:
            return {'status': 'error', 'reason': 'no_sequences'}
        
        # Concatenate all sequences
        X = np.concatenate(all_sequences, axis=0)
        y = np.concatenate(all_targets, axis=0)
        
        # Normalize
        self.scaler = StandardScaler()
        batch_size, seq_len, features = X.shape
        X_reshaped = X.reshape(-1, features)
        X_scaled = self.scaler.fit_transform(X_reshaped)
        X_scaled = X_scaled.reshape(batch_size, seq_len, features)
        
        # Convert to tensors
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)
        y_tensor = torch.FloatTensor(y).unsqueeze(1).to(self.device)
        
        # Initialize model
        input_size = features
        self.model = TimeSeriesLSTM(input_size, hidden_size=64, num_layers=2).to(self.device)
        
        # Training
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        
        num_epochs = 50
        batch_size_train = 32
        
        for epoch in range(num_epochs):
            self.model.train()
            total_loss = 0
            
            for i in range(0, len(X_tensor), batch_size_train):
                batch_X = X_tensor[i:i+batch_size_train]
                batch_y = y_tensor[i:i+batch_size_train]
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if (epoch + 1) % 10 == 0:
                self.logger.info(f"Epoch {epoch+1}/{num_epochs}, Loss: {total_loss/len(X_tensor)*batch_size_train:.4f}")
        
        # Evaluate
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(X_tensor)
            predictions_np = predictions.cpu().numpy().flatten()
            accuracy = np.mean((predictions_np > 0.5) == y)
        
        return {
            'status': 'success',
            'model_type': 'lstm',
            'accuracy': float(accuracy),
            'num_sequences': len(X),
            'sequence_length': self.sequence_length
        }
    
    def predict_time_series(self, recent_performance: List[Dict[str, Any]]) -> float:
        """
        Predict success probability using time-series model
        
        Args:
            recent_performance: Recent performance history (at least sequence_length days)
            
        Returns:
            Success probability (0.0 to 1.0)
        """
        if not self.model or not recent_performance or len(recent_performance) < self.sequence_length:
            return 0.5  # Default
        
        try:
            sequences, _ = self.prepare_time_series_data(recent_performance, self.sequence_length)
            if len(sequences) == 0:
                return 0.5
            
            # Use most recent sequence
            sequence = sequences[-1:]
            
            # Normalize
            batch_size, seq_len, features = sequence.shape
            sequence_reshaped = sequence.reshape(-1, features)
            sequence_scaled = self.scaler.transform(sequence_reshaped)
            sequence_scaled = sequence_scaled.reshape(batch_size, seq_len, features)
            
            # Predict
            X_tensor = torch.FloatTensor(sequence_scaled).to(self.device)
            self.model.eval()
            with torch.no_grad():
                prediction = self.model(X_tensor)
                return float(prediction.cpu().numpy()[0, 0])
        except Exception as e:
            self.logger.warning(f"Error in time-series prediction: {e}")
            return 0.5


class CausalInferenceModel:
    """
    Causal inference model for estimating true effect of bid changes (#26)
    Uses difference-in-differences and propensity score matching
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.enable_causal_inference = config.get('enable_causal_inference', False)
    
    def estimate_treatment_effect(self, treated_entities: List[Dict[str, Any]],
                                 control_entities: List[Dict[str, Any]],
                                 before_period: List[Dict[str, Any]],
                                 after_period: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Estimate treatment effect using difference-in-differences
        
        Args:
            treated_entities: Entities that received bid adjustment
            control_entities: Entities that did not receive adjustment
            before_period: Performance before treatment
            after_period: Performance after treatment
            
        Returns:
            Estimated treatment effect
        """
        if not self.enable_causal_inference:
            return {'status': 'skipped', 'reason': 'causal_inference_disabled'}
        
        try:
            # Calculate average outcomes
            treated_before = np.mean([e.get('roas', 0) for e in before_period if e.get('entity_id') in [t.get('entity_id') for t in treated_entities]])
            treated_after = np.mean([e.get('roas', 0) for e in after_period if e.get('entity_id') in [t.get('entity_id') for t in treated_entities]])
            
            control_before = np.mean([e.get('roas', 0) for e in before_period if e.get('entity_id') in [c.get('entity_id') for c in control_entities]])
            control_after = np.mean([e.get('roas', 0) for e in after_period if e.get('entity_id') in [c.get('entity_id') for c in control_entities]])
            
            # Difference-in-differences
            did_effect = (treated_after - treated_before) - (control_after - control_before)
            
            return {
                'status': 'success',
                'treatment_effect': float(did_effect),
                'treated_change': float(treated_after - treated_before),
                'control_change': float(control_after - control_before),
                'method': 'difference_in_differences'
            }
        except Exception as e:
            self.logger.error(f"Error in causal inference: {e}")
            return {'status': 'error', 'reason': str(e)}
    
    def propensity_score_matching(self, treated: List[Dict[str, Any]],
                                 control: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Match treated and control entities using propensity scores
        
        Args:
            treated: Treated entities with features
            control: Control entities with features
            
        Returns:
            Matched pairs and effect estimate
        """
        if not ADVANCED_ML_AVAILABLE or not self.enable_causal_inference:
            return {'status': 'skipped', 'reason': 'ml_not_available_or_disabled'}
        
        try:
            # Simplified propensity score matching
            # In production, would use logistic regression to estimate propensity scores
            
            # Match based on similar features (simplified)
            matched_pairs = []
            for t in treated:
                best_match = None
                best_distance = float('inf')
                
                t_features = [t.get('acos', 0), t.get('roas', 0), t.get('ctr', 0)]
                
                for c in control:
                    c_features = [c.get('acos', 0), c.get('roas', 0), c.get('ctr', 0)]
                    distance = np.sqrt(sum((a - b) ** 2 for a, b in zip(t_features, c_features)))
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_match = c
                
                if best_match:
                    matched_pairs.append((t, best_match))
            
            # Calculate average treatment effect on treated (ATT)
            if matched_pairs:
                effects = []
                for treated_entity, control_entity in matched_pairs:
                    effect = treated_entity.get('outcome_roas', 0) - control_entity.get('outcome_roas', 0)
                    effects.append(effect)
                
                att = np.mean(effects) if effects else 0.0
                
                return {
                    'status': 'success',
                    'average_treatment_effect': float(att),
                    'num_matched_pairs': len(matched_pairs),
                    'method': 'propensity_score_matching'
                }
            
            return {'status': 'error', 'reason': 'no_matches'}
        except Exception as e:
            self.logger.error(f"Error in propensity score matching: {e}")
            return {'status': 'error', 'reason': str(e)}

