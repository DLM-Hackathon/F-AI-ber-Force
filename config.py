"""
Configuration file for Dispatch Success Predictor
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'options': f"-c search_path={os.getenv('DB_SCHEMA', 'team_faiber_force')}"
}

# Model configuration
MODEL_CONFIG = {
    'test_size': 0.2,
    'random_state': 42,
    'success_model_path': 'models/dispatch_success_model.pkl',
    'duration_model_path': 'models/dispatch_duration_model.pkl',
    'preprocessor_path': 'models/preprocessor.pkl',
    'metrics_path': 'models/model_metrics.json',
    # Kept for backwards compatibility
    'model_path': 'models/dispatch_success_model.pkl',
    'scaler_path': 'models/scaler.pkl'
}

# Feature configuration
FEATURE_COLUMNS = [
    'ticket_type',
    'order_type', 
    'priority',
    'required_skill',
    'technician_skill',
    'distance',
    'expected_duration',
    'skill_match',
    'workload_ratio'
]

# Categorical features that need encoding
CATEGORICAL_FEATURES = [
    'ticket_type',
    'order_type',
    'priority',
    'required_skill',
    'technician_skill'
]

# Numerical features
NUMERICAL_FEATURES = [
    'distance',
    'expected_duration',
    'skill_match',
    'workload_ratio'
]

TARGET_COLUMN_SUCCESS = 'success'
TARGET_COLUMN_DURATION = 'actual_duration'

