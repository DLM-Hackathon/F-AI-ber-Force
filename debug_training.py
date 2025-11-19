"""
Debug version of training to identify the issue
"""

from data_loader import load_data
from preprocessor import DataPreprocessor
import pandas as pd

print("="*70)
print("DEBUG: TRAINING DATA ANALYSIS")
print("="*70)

# Step 1: Load data
print("\n[1] Loading data...")
df = load_data()
print(f"✓ Loaded {len(df)} records")

print("\n[2] Checking column types...")
print("\nAll columns and their types:")
for col in df.columns:
    dtype = df[col].dtype
    sample_value = df[col].iloc[0] if len(df) > 0 else "N/A"
    print(f"  {col:<30} | {dtype:<15} | Sample: {sample_value}")

print("\n[3] Checking for string values in expected numeric columns...")
numeric_expected = ['distance', 'expected_duration', 'skill_match']
for col in numeric_expected:
    if col in df.columns:
        print(f"\n{col}:")
        print(f"  dtype: {df[col].dtype}")
        print(f"  unique values: {df[col].nunique()}")
        print(f"  sample values: {df[col].head().tolist()}")
        
        # Check if any non-numeric values
        try:
            pd.to_numeric(df[col], errors='coerce')
            print(f"  ✓ Can convert to numeric")
        except Exception as e:
            print(f"  ✗ Error converting to numeric: {e}")

print("\n[4] Initializing preprocessor...")
preprocessor = DataPreprocessor()

print("\n[5] Checking which features will be used...")
print(f"Feature columns defined: {preprocessor.feature_columns}")
print(f"Categorical features: {preprocessor.categorical_features}")
print(f"Numerical features: {preprocessor.numerical_features}")

print("\n[6] Checking which features are available in the data...")
available = [col for col in preprocessor.feature_columns if col in df.columns]
missing = [col for col in preprocessor.feature_columns if col not in df.columns]
print(f"Available: {available}")
print(f"Missing: {missing}")

print("\n[7] Attempting to prepare features...")
try:
    X, y_success, y_duration = preprocessor.prepare_features(df, fit_encoders=True)
    print(f"✓ Features prepared successfully!")
    print(f"  X shape: {X.shape}")
    print(f"  X columns: {X.columns.tolist()}")
    print(f"  X dtypes:\n{X.dtypes}")
except Exception as e:
    print(f"✗ Error preparing features:")
    print(f"  {type(e).__name__}: {e}")
    
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()

print("\n" + "="*70)
print("DEBUG COMPLETE")
print("="*70)

