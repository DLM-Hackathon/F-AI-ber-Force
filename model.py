"""
Machine learning model for dispatch success prediction
"""

import pandas as pd
import numpy as np
import pickle
import json
import os
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from typing import Dict, Any, Tuple
from config import MODEL_CONFIG


class DispatchSuccessPredictor:
    """Machine learning model for predicting dispatch success AND duration"""
    
    def __init__(self, model_type: str = 'random_forest'):
        """
        Initialize the predictor
        
        Args:
            model_type: Type of model ('random_forest', 'gradient_boosting', 'logistic_regression')
        """
        self.model_type = model_type
        self.success_model = self._create_success_model(model_type)
        self.duration_model = self._create_duration_model(model_type)
        self.is_trained = False
        self.feature_importance_success = None
        self.feature_importance_duration = None
    
    def _create_success_model(self, model_type: str):
        """Create the classification model for success prediction"""
        if model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=MODEL_CONFIG['random_state'],
                n_jobs=-1
            )
        elif model_type == 'gradient_boosting':
            return GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=MODEL_CONFIG['random_state']
            )
        elif model_type == 'logistic_regression':
            return LogisticRegression(
                random_state=MODEL_CONFIG['random_state'],
                max_iter=1000
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def _create_duration_model(self, model_type: str):
        """Create the regression model for duration prediction"""
        if model_type in ['random_forest', 'gradient_boosting']:
            return RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=MODEL_CONFIG['random_state'],
                n_jobs=-1
            )
        elif model_type == 'logistic_regression':
            # Use RandomForestRegressor as default for regression
            return RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=MODEL_CONFIG['random_state'],
                n_jobs=-1
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def train(self, X_train: pd.DataFrame, y_success_train: pd.Series, y_duration_train: pd.Series = None):
        """Train both success and duration models"""
        print(f"\n=== Training {self.model_type} models ===")
        
        # Train success model
        print("\n[1/2] Training Success Prediction Model...")
        self.success_model.fit(X_train, y_success_train)
        
        # Store feature importance for success model
        if hasattr(self.success_model, 'feature_importances_'):
            self.feature_importance_success = pd.DataFrame({
                'feature': X_train.columns,
                'importance': self.success_model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            print("\n=== Feature Importance (Success Model) ===")
            print(self.feature_importance_success)
        
        # Train duration model if target provided
        if y_duration_train is not None:
            print("\n[2/2] Training Duration Prediction Model...")
            self.duration_model.fit(X_train, y_duration_train)
            
            # Store feature importance for duration model
            if hasattr(self.duration_model, 'feature_importances_'):
                self.feature_importance_duration = pd.DataFrame({
                    'feature': X_train.columns,
                    'importance': self.duration_model.feature_importances_
                }).sort_values('importance', ascending=False)
                
                print("\n=== Feature Importance (Duration Model) ===")
                print(self.feature_importance_duration)
        
        self.is_trained = True
        print("\n[OK] Model training completed")
    
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Make predictions for both success and duration"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        success_pred = self.success_model.predict(X)
        duration_pred = self.duration_model.predict(X)
        
        return success_pred, duration_pred
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict success probabilities"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        return self.success_model.predict_proba(X)
    
    def predict_success(self, X: pd.DataFrame) -> np.ndarray:
        """Predict success only"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        return self.success_model.predict(X)
    
    def predict_duration(self, X: pd.DataFrame) -> np.ndarray:
        """Predict duration only"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        return self.duration_model.predict(X)
    
    def evaluate(self, X_test: pd.DataFrame, y_success_test: pd.Series, y_duration_test: pd.Series = None) -> Dict[str, Any]:
        """
        Evaluate both model performances
        
        Returns:
            Dictionary containing evaluation metrics for both models
        """
        print(f"\n=== Evaluating {self.model_type} models ===")
        
        metrics = {}
        
        # Evaluate Success Model
        print("\n=== SUCCESS PREDICTION MODEL ===")
        y_success_pred = self.predict_success(X_test)
        y_success_proba = self.predict_proba(X_test)[:, 1]
        
        metrics['success'] = {
            'accuracy': accuracy_score(y_success_test, y_success_pred),
            'precision': precision_score(y_success_test, y_success_pred, zero_division=0),
            'recall': recall_score(y_success_test, y_success_pred, zero_division=0),
            'f1_score': f1_score(y_success_test, y_success_pred, zero_division=0),
            'roc_auc': roc_auc_score(y_success_test, y_success_proba),
            'confusion_matrix': confusion_matrix(y_success_test, y_success_pred).tolist()
        }
        
        print(f"\nAccuracy:  {metrics['success']['accuracy']:.4f}")
        print(f"Precision: {metrics['success']['precision']:.4f}")
        print(f"Recall:    {metrics['success']['recall']:.4f}")
        print(f"F1 Score:  {metrics['success']['f1_score']:.4f}")
        print(f"ROC AUC:   {metrics['success']['roc_auc']:.4f}")
        
        print("\n=== Confusion Matrix ===")
        cm = metrics['success']['confusion_matrix']
        print(f"                Predicted")
        print(f"               Fail  Success")
        print(f"Actual Fail    {cm[0][0]:4d}  {cm[0][1]:4d}")
        print(f"       Success {cm[1][0]:4d}  {cm[1][1]:4d}")
        
        # Evaluate Duration Model
        if y_duration_test is not None:
            print("\n\n=== DURATION PREDICTION MODEL ===")
            y_duration_pred = self.predict_duration(X_test)
            
            metrics['duration'] = {
                'mae': mean_absolute_error(y_duration_test, y_duration_pred),
                'rmse': np.sqrt(mean_squared_error(y_duration_test, y_duration_pred)),
                'r2': r2_score(y_duration_test, y_duration_pred),
                'mean_actual': float(y_duration_test.mean()),
                'mean_predicted': float(y_duration_pred.mean())
            }
            
            print(f"\nMean Absolute Error: {metrics['duration']['mae']:.2f} minutes")
            print(f"Root Mean Squared Error: {metrics['duration']['rmse']:.2f} minutes")
            print(f"R² Score: {metrics['duration']['r2']:.4f}")
            print(f"Mean Actual Duration: {metrics['duration']['mean_actual']:.2f} minutes")
            print(f"Mean Predicted Duration: {metrics['duration']['mean_predicted']:.2f} minutes")
        
        return metrics
    
    def save(self, success_model_path: str = None, duration_model_path: str = None):
        """Save the trained models"""
        if not self.is_trained:
            raise ValueError("Models must be trained before saving")
        
        success_model_path = success_model_path or MODEL_CONFIG['success_model_path']
        duration_model_path = duration_model_path or MODEL_CONFIG['duration_model_path']
        
        # Create directory if it doesn't exist
        Path(success_model_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save success model
        with open(success_model_path, 'wb') as f:
            pickle.dump(self.success_model, f)
        print(f"[OK] Success model saved to {success_model_path}")
        
        # Save duration model
        with open(duration_model_path, 'wb') as f:
            pickle.dump(self.duration_model, f)
        print(f"[OK] Duration model saved to {duration_model_path}")
    
    def load(self, success_model_path: str = None, duration_model_path: str = None):
        """Load trained models"""
        success_model_path = success_model_path or MODEL_CONFIG['success_model_path']
        duration_model_path = duration_model_path or MODEL_CONFIG['duration_model_path']
        
        if not os.path.exists(success_model_path):
            raise FileNotFoundError(f"Success model file not found: {success_model_path}")
        
        with open(success_model_path, 'rb') as f:
            self.success_model = pickle.load(f)
        print(f"[OK] Success model loaded from {success_model_path}")
        
        if os.path.exists(duration_model_path):
            with open(duration_model_path, 'rb') as f:
                self.duration_model = pickle.load(f)
            print(f"[OK] Duration model loaded from {duration_model_path}")
        
        self.is_trained = True


def compare_models(X_train: pd.DataFrame, y_train: pd.Series, 
                   X_test: pd.DataFrame, y_test: pd.Series) -> pd.DataFrame:
    """
    Compare different model types
    
    Returns:
        DataFrame with comparison results
    """
    models = ['random_forest', 'gradient_boosting', 'logistic_regression']
    results = []
    
    for model_type in models:
        print(f"\n{'='*60}")
        print(f"Training and evaluating {model_type}")
        print(f"{'='*60}")
        
        predictor = DispatchSuccessPredictor(model_type=model_type)
        predictor.train(X_train, y_train)
        metrics = predictor.evaluate(X_test, y_test)
        
        results.append({
            'model': model_type,
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'f1_score': metrics['f1_score'],
            'roc_auc': metrics['roc_auc']
        })
    
    results_df = pd.DataFrame(results)
    print(f"\n{'='*60}")
    print("=== Model Comparison ===")
    print(f"{'='*60}")
    print(results_df.to_string(index=False))
    
    return results_df


if __name__ == "__main__":
    from data_loader import load_data
    from preprocessor import DataPreprocessor
    
    print("Testing dispatch success predictor...")
    
    # Load and prepare data
    df = load_data()
    preprocessor = DataPreprocessor()
    X, y = preprocessor.prepare_features(df)
    X_train, X_test, y_train, y_test = preprocessor.split_data(X, y)
    
    # Compare models
    comparison = compare_models(X_train, y_train, X_test, y_test)
    
    # Train and save best model (Random Forest typically performs well)
    print("\n=== Training final model ===")
    predictor = DispatchSuccessPredictor(model_type='random_forest')
    predictor.train(X_train, y_train)
    metrics = predictor.evaluate(X_test, y_test)
    predictor.save()
    
    # Save metrics
    metrics_path = MODEL_CONFIG['metrics_path']
    Path(metrics_path).parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[OK] Metrics saved to {metrics_path}")

