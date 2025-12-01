"""
Model Rollback Mechanism (#16)

Provides ability to rollback to previous model version if metrics degrade in production.
"""

import logging
import os
import pickle
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path


class ModelRollbackManager:
    """
    Manages model versioning and rollback functionality (#16)
    """
    
    def __init__(self, model_path: str, max_versions: int = 5):
        """
        Initialize rollback manager
        
        Args:
            model_path: Base path for model files
            max_versions: Maximum number of versions to keep
        """
        self.model_path = model_path
        self.max_versions = max_versions
        self.logger = logging.getLogger(__name__)
        
        # Create models directory if it doesn't exist
        if self.model_path:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
    
    def get_model_version_path(self, version: int) -> str:
        """Get path for a specific model version"""
        base_path = Path(self.model_path)
        return str(base_path.parent / f"{base_path.stem}_v{version}{base_path.suffix}")
    
    def save_model_version(self, model: Any, model_version: int, scaler: Any, 
                          metadata: Dict[str, Any]) -> bool:
        """
        Save a model version with metadata
        
        Args:
            model: Trained model
            model_version: Version number
            scaler: Feature scaler
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        version_path = self.get_model_version_path(model_version)
        
        try:
            model_data = {
                'model': model,
                'model_version': model_version,
                'scaler': scaler,
                'saved_at': datetime.now().isoformat(),
                'metadata': metadata
            }
            
            with open(version_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.logger.info(f"Model version {model_version} saved to {version_path}")
            
            # Clean up old versions
            self._cleanup_old_versions(model_version)
            
            return True
        except Exception as e:
            self.logger.error(f"Error saving model version {model_version}: {e}")
            return False
    
    def load_model_version(self, version: int) -> Optional[Dict[str, Any]]:
        """
        Load a specific model version
        
        Args:
            version: Version number to load
            
        Returns:
            Model data dictionary or None
        """
        version_path = self.get_model_version_path(version)
        
        if not os.path.exists(version_path):
            self.logger.warning(f"Model version {version} not found at {version_path}")
            return None
        
        try:
            with open(version_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.logger.info(f"Model version {version} loaded from {version_path}")
            return model_data
        except Exception as e:
            self.logger.error(f"Error loading model version {version}: {e}")
            return None
    
    def get_available_versions(self) -> List[int]:
        """Get list of available model versions"""
        base_path = Path(self.model_path)
        versions = []
        
        for file_path in base_path.parent.glob(f"{base_path.stem}_v*{base_path.suffix}"):
            try:
                # Extract version number from filename
                version_str = file_path.stem.split('_v')[1]
                version = int(version_str)
                versions.append(version)
            except (ValueError, IndexError):
                continue
        
        return sorted(versions, reverse=True)
    
    def rollback_to_version(self, target_version: int, current_version: int) -> bool:
        """
        Rollback to a previous model version
        
        Args:
            target_version: Version to rollback to
            current_version: Current active version
            
        Returns:
            True if successful
        """
        if target_version >= current_version:
            self.logger.error(f"Cannot rollback to version {target_version} >= current {current_version}")
            return False
        
        model_data = self.load_model_version(target_version)
        if not model_data:
            return False
        
        # Save as current model
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            self.logger.info(
                f"Rolled back from version {current_version} to version {target_version}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error during rollback: {e}")
            return False
    
    def _cleanup_old_versions(self, current_version: int) -> None:
        """Remove old model versions beyond max_versions limit"""
        available_versions = self.get_available_versions()
        
        # Keep current version and max_versions - 1 older versions
        versions_to_keep = set([current_version])
        versions_to_keep.update(available_versions[:self.max_versions - 1])
        
        for version in available_versions:
            if version not in versions_to_keep:
                version_path = self.get_model_version_path(version)
                try:
                    os.remove(version_path)
                    self.logger.info(f"Removed old model version {version}")
                except Exception as e:
                    self.logger.warning(f"Error removing old version {version}: {e}")

