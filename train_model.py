"""
Main script to train the dispatch success and duration prediction models
"""

import argparse
import json
import pickle
from pathlib import Path
from data_loader import load_data
from preprocessor import DataPreprocessor
from model import DispatchSuccessPredictor
from config import MODEL_CONFIG


def main(compare: bool = False, model_type: str = 'random_forest'):
    """
    Main training pipeline
    
    Args:
        compare: Whether to compare multiple models
        model_type: Type of model to train
    """
    print("="*70)
    print("DISPATCH SUCCESS & DURATION PREDICTION - MODEL TRAINING")
    print("="*70)
    
    # Step 1: Load data
    print("\n[1/5] Loading data from database...")
    df = load_data()
    print(f"[OK] Loaded {len(df)} records")
    
    # Step 2: Preprocess data
    print("\n[2/5] Preprocessing data...")
    preprocessor = DataPreprocessor()
    preprocessor.explore_data(df)
    X, y_success, y_duration = preprocessor.prepare_features(df, fit_encoders=True)
    
    # Split data
    X_train, X_test, y_success_train, y_success_test, y_duration_train, y_duration_test = preprocessor.split_data(
        X, y_success, y_duration
    )
    
    # Save preprocessor
    preprocessor_path = MODEL_CONFIG['preprocessor_path']
    Path(preprocessor_path).parent.mkdir(parents=True, exist_ok=True)
    with open(preprocessor_path, 'wb') as f:
        pickle.dump(preprocessor, f)
    print(f"[OK] Preprocessor saved to {preprocessor_path}")
    
    # Step 3: Skip model comparison for now
    if compare:
        print("\n[3/5] Model comparison not yet implemented for dual-target models")
        print("     Using default random_forest model")
    else:
        print("\n[3/5] Skipping model comparison...")
    
    # Step 4: Train final model
    print(f"\n[4/5] Training final {model_type} models...")
    predictor = DispatchSuccessPredictor(model_type=model_type)
    predictor.train(X_train, y_success_train, y_duration_train)
    
    # Step 5: Evaluate and save
    print("\n[5/5] Evaluating and saving models...")
    metrics = predictor.evaluate(X_test, y_success_test, y_duration_test)
    predictor.save()
    
    # Save metrics
    metrics_path = MODEL_CONFIG['metrics_path']
    with open(metrics_path, 'w') as f:
        # Convert numpy types to Python types for JSON serialization
        metrics_json = {}
        for key, value in metrics.items():
            if isinstance(value, dict):
                metrics_json[key] = {k: float(v) if isinstance(v, (int, float, np.float32, np.float64)) else v 
                                    for k, v in value.items()}
            else:
                metrics_json[key] = value
        json.dump(metrics_json, f, indent=2)
    print(f"[OK] Metrics saved to {metrics_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("TRAINING COMPLETED SUCCESSFULLY")
    print("="*70)
    print(f"\nModel Type: {model_type}")
    
    print(f"\n=== SUCCESS PREDICTION ===")
    print(f"Accuracy:   {metrics['success']['accuracy']:.2%}")
    print(f"Precision:  {metrics['success']['precision']:.2%}")
    print(f"Recall:     {metrics['success']['recall']:.2%}")
    print(f"F1 Score:   {metrics['success']['f1_score']:.2%}")
    print(f"ROC AUC:    {metrics['success']['roc_auc']:.2%}")
    
    if 'duration' in metrics:
        print(f"\n=== DURATION PREDICTION ===")
        print(f"MAE:        {metrics['duration']['mae']:.2f} minutes")
        print(f"RMSE:       {metrics['duration']['rmse']:.2f} minutes")
        print(f"R² Score:   {metrics['duration']['r2']:.4f}")
    
    print(f"\n=== Files Saved ===")
    print(f"Success Model:  {MODEL_CONFIG['success_model_path']}")
    print(f"Duration Model: {MODEL_CONFIG['duration_model_path']}")
    print(f"Preprocessor:   {MODEL_CONFIG['preprocessor_path']}")
    print(f"Metrics:        {MODEL_CONFIG['metrics_path']}")


if __name__ == "__main__":
    import numpy as np  # Import here for metrics conversion
    
    parser = argparse.ArgumentParser(description='Train dispatch success and duration prediction models')
    parser.add_argument(
        '--compare', 
        action='store_true',
        help='Compare multiple model types (not yet implemented)'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        default='random_forest',
        choices=['random_forest', 'gradient_boosting', 'logistic_regression'],
        help='Type of model to train'
    )
    
    args = parser.parse_args()
    main(compare=args.compare, model_type=args.model_type)
