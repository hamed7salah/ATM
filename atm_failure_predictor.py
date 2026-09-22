"""
ATM Failure Prediction - Inference Package

Simple API for predicting ATM failures within the next 30 minutes.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import joblib
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    import lightgbm as lgb
    import xgboost as xgb
    from catboost import CatBoostClassifier
except ImportError:
    print("Warning: Some ML libraries not installed. Install with: pip install lightgbm xgboost catboost")


class ATMFailurePredictor:
    """
    Predicts ATM failures within the next 30 minutes.
    
    Usage:
        predictor = ATMFailurePredictor()
        result = predictor.predict(sensor_data, threshold_policy='balanced')
    """
    
    def __init__(self, models_dir: str = 'models'):
        """
        Initialize predictor by loading model and metadata.
        
        Args:
            models_dir: Directory containing saved models
        """
        self.models_dir = Path(models_dir)
        
        # Load metadata
        with open(self.models_dir / 'final_model_package.json', 'r') as f:
            self.package = json.load(f)
        
        self.model_name = self.package['model_name']
        self.feature_columns = self.package['feature_columns']
        self.thresholds = self.package['thresholds']
        
        # Load model
        self.model = self._load_model()
        
        print(f"ATM Failure Predictor initialized")
        print(f"Model: {self.model_name}")
        print(f"Version: {self.package['model_version']}")
        print(f"Features: {len(self.feature_columns)}")
    
    def _load_model(self):
        """Load the trained model."""
        if self.model_name == 'LightGBM':
            return lgb.Booster(model_file=str(self.models_dir / 'lightgbm_model.txt'))
        elif self.model_name == 'XGBoost':
            model = xgb.Booster()
            model.load_model(str(self.models_dir / 'xgboost_model.json'))
            return model
        elif self.model_name == 'CatBoost':
            model = CatBoostClassifier()
            model.load_model(str(self.models_dir / 'catboost_model.cbm'))
            return model
        else:
            raise ValueError(f"Unknown model: {self.model_name}")
    
    def predict(self, 
                sensor_data: pd.DataFrame, 
                threshold_policy: str = 'balanced') -> Dict[str, Any]:
        """
        Predict failure probability for a single ATM observation.
        
        Args:
            sensor_data: DataFrame with sensor readings (single row or multiple rows)
            threshold_policy: 'safety', 'balanced', or 'low_false_alarm'
        
        Returns:
            Dictionary with prediction results
        """
        # Validate input
        if not isinstance(sensor_data, pd.DataFrame):
            raise ValueError("sensor_data must be a pandas DataFrame")
        
        # Check for required features
        missing_features = set(self.feature_columns) - set(sensor_data.columns)
        if missing_features:
            raise ValueError(f"Missing required features: {missing_features}")
        
        # Select features in correct order
        X = sensor_data[self.feature_columns]
        
        # Handle missing values
        X = X.fillna(0)
        
        # Predict probability
        if self.model_name == 'LightGBM':
            probabilities = self.model.predict(X)
        elif self.model_name == 'XGBoost':
            dmatrix = xgb.DMatrix(X)
            probabilities = self.model.predict(dmatrix)
        elif self.model_name == 'CatBoost':
            probabilities = self.model.predict_proba(X)[:, 1]
        
        # Get threshold
        if threshold_policy not in self.thresholds:
            raise ValueError(f"Invalid threshold_policy. Choose from: {list(self.thresholds.keys())}")
        
        threshold = self.thresholds[threshold_policy]
        
        # Make predictions
        predictions = (probabilities >= threshold).astype(int)
        
        # Return results
        if len(sensor_data) == 1:
            # Single prediction
            return {
                'failure_probability_next_30m': float(probabilities[0]),
                'predicted_failure_next_30m': bool(predictions[0]),
                'threshold': float(threshold),
                'threshold_policy': threshold_policy,
                'model_name': self.model_name,
                'model_version': self.package['model_version'],
                'prediction_timestamp': datetime.now().isoformat()
            }
        else:
            # Batch predictions
            return {
                'failure_probabilities_next_30m': probabilities.tolist(),
                'predicted_failures_next_30m': predictions.tolist(),
                'threshold': float(threshold),
                'threshold_policy': threshold_policy,
                'model_name': self.model_name,
                'model_version': self.package['model_version'],
                'prediction_timestamp': datetime.now().isoformat(),
                'batch_size': len(sensor_data)
            }
    
    def predict_single(self, 
                      sensor_dict: Dict[str, Any], 
                      threshold_policy: str = 'balanced') -> Dict[str, Any]:
        """
        Predict failure probability from a dictionary of sensor readings.
        
        Args:
            sensor_dict: Dictionary with sensor readings
            threshold_policy: 'safety', 'balanced', or 'low_false_alarm'
        
        Returns:
            Dictionary with prediction results
        """
        # Convert dict to DataFrame
        df = pd.DataFrame([sensor_dict])
        return self.predict(df, threshold_policy)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and performance metrics."""
        return {
            'model_name': self.model_name,
            'model_version': self.package['model_version'],
            'training_date': self.package['training_date'],
            'n_features': len(self.feature_columns),
            'thresholds': self.thresholds,
            'performance': self.package['performance']
        }
    
    def get_threshold_info(self, threshold_policy: str) -> Dict[str, Any]:
        """Get information about a specific threshold policy."""
        if threshold_policy not in self.thresholds:
            raise ValueError(f"Invalid threshold_policy. Choose from: {list(self.thresholds.keys())}")
        
        return {
            'policy': threshold_policy,
            'threshold': self.thresholds[threshold_policy],
            'metrics': self.package['threshold_metrics'][threshold_policy]
        }


def main():
    """Example usage."""
    print("="*70)
    print("ATM FAILURE PREDICTOR - EXAMPLE USAGE")
    print("="*70)
    
    # Initialize predictor
    predictor = ATMFailurePredictor()
    
    # Get model info
    print("\nModel Information:")
    info = predictor.get_model_info()
    print(f"  Model: {info['model_name']}")
    print(f"  Version: {info['model_version']}")
    print(f"  Features: {info['n_features']}")
    print(f"  Chronological Test PR-AUC: {info['performance']['chronological_test']['pr_auc']:.6f}")
    print(f"  Unseen ATM Test PR-AUC: {info['performance']['unseen_atm_test']['pr_auc']:.6f}")
    
    # Show threshold policies
    print("\nAvailable Threshold Policies:")
    for policy in ['safety', 'balanced', 'low_false_alarm']:
        threshold_info = predictor.get_threshold_info(policy)
        print(f"\n  {policy.upper()}:")
        print(f"    Threshold: {threshold_info['threshold']:.4f}")
        print(f"    Precision: {threshold_info['metrics']['precision']:.4f}")
        print(f"    Recall: {threshold_info['metrics']['recall']:.4f}")
        print(f"    F2 Score: {threshold_info['metrics']['f2']:.4f}")
    
    print("\n" + "="*70)
    print("Predictor ready for use!")
    print("="*70)


if __name__ == "__main__":
    main()
