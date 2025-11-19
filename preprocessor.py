"""
Data preprocessing and feature engineering for dispatch success prediction
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from typing import Tuple, Dict
from config import (FEATURE_COLUMNS, TARGET_COLUMN_SUCCESS, TARGET_COLUMN_DURATION, 
                     CATEGORICAL_FEATURES, NUMERICAL_FEATURES, MODEL_CONFIG)


class DataPreprocessor:
    """Handles data preprocessing and feature engineering"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_columns = FEATURE_COLUMNS
        self.categorical_features = CATEGORICAL_FEATURES
        self.numerical_features = NUMERICAL_FEATURES
        self.target_column_success = TARGET_COLUMN_SUCCESS
        self.target_column_duration = TARGET_COLUMN_DURATION
    
    def explore_data(self, df: pd.DataFrame):
        """Print exploratory data analysis"""
        print("\n=== Data Exploration ===")
        print(f"Dataset shape: {df.shape}")
        print(f"\nColumns: {df.columns.tolist()}")
        print(f"\nData types:\n{df.dtypes}")
        print(f"\nMissing values:\n{df.isnull().sum()}")
        print(f"\nBasic statistics:\n{df.describe()}")
        
        # Target distribution
        if self.target_column_success in df.columns:
            print(f"\n=== Target Variable Distribution ({self.target_column_success}) ===")
            print(df[self.target_column_success].value_counts())
            print(f"Success rate: {df[self.target_column_success].mean():.2%}")
        
        if self.target_column_duration in df.columns:
            print(f"\n=== Duration Statistics ({self.target_column_duration}) ===")
            print(f"  Mean: {df[self.target_column_duration].mean():.2f} minutes")
            print(f"  Median: {df[self.target_column_duration].median():.2f} minutes")
            print(f"  Std: {df[self.target_column_duration].std():.2f} minutes")
        
        # Feature distributions
        print("\n=== Feature Distributions ===")
        for col in self.feature_columns:
            if col in df.columns:
                print(f"\n{col}:")
                # Only compute numeric statistics for numerical features
                if col in self.numerical_features:
                    print(f"  Mean: {df[col].mean():.2f}")
                    print(f"  Std: {df[col].std():.2f}")
                    print(f"  Min: {df[col].min():.2f}")
                    print(f"  Max: {df[col].max():.2f}")
                elif col in self.categorical_features:
                    print(f"  Type: Categorical")
                    print(f"  Unique values: {df[col].nunique()}")
                    print(f"  Top values: {df[col].value_counts().head(3).to_dict()}")
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create additional features from raw data
        """
        df = df.copy()
        
        # Ensure skill_match exists (should be created in SQL query)
        if 'skill_match' not in df.columns:
            if 'required_skill' in df.columns and 'technician_skill' in df.columns:
                df['skill_match'] = (df['required_skill'] == df['technician_skill']).astype(int)
        
        # Additional feature: distance categories
        df['distance_category'] = pd.cut(
            df['distance'], 
            bins=[0, 10, 25, 50, 100, float('inf')],
            labels=['very_short', 'short', 'medium', 'long', 'very_long']
        )
        
        # Interaction feature: distance * skill_mismatch
        if 'skill_match' in df.columns:
            df['distance_skill_interaction'] = df['distance'] * (1 - df['skill_match'])
        
        return df
    
    def prepare_features(self, df: pd.DataFrame, fit_encoders: bool = True) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare features for modeling
        
        Args:
            df: Input dataframe
            fit_encoders: Whether to fit encoders/scaler (True for training, False for prediction)
        
        Returns:
            X: Feature matrix
            y_success: Success target variable (if available)
            y_duration: Duration target variable (if available)
        """
        df = self.create_features(df)
        
        # Select feature columns
        available_features = [col for col in self.feature_columns if col in df.columns]
        
        if not available_features:
            raise ValueError(f"None of the required features {self.feature_columns} found in dataframe")
        
        X = df[available_features].copy()
        
        # Encode categorical features
        for col in self.categorical_features:
            if col in X.columns:
                if fit_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
                else:
                    if col in self.label_encoders:
                        # Handle unseen categories
                        X[col] = X[col].astype(str)
                        # Map unseen labels to -1
                        known_labels = set(self.label_encoders[col].classes_)
                        X[col] = X[col].apply(lambda x: x if x in known_labels else 'UNKNOWN')
                        
                        # Add UNKNOWN to encoder if needed
                        if 'UNKNOWN' not in self.label_encoders[col].classes_:
                            self.label_encoders[col].classes_ = np.append(
                                self.label_encoders[col].classes_, 'UNKNOWN'
                            )
                        
                        X[col] = self.label_encoders[col].transform(X[col])
        
        # Handle missing values for numerical features
        for col in X.columns:
            if col in self.numerical_features:
                X[col] = X[col].fillna(X[col].mean())
        
        # Scale all features
        if fit_encoders:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = self.scaler.transform(X)
        
        X_scaled = pd.DataFrame(X_scaled, columns=available_features, index=X.index)
        
        # Get target variables if available
        y_success = None
        y_duration = None
        
        if self.target_column_success in df.columns:
            y_success = df[self.target_column_success].copy()
        
        if self.target_column_duration in df.columns:
            y_duration = df[self.target_column_duration].copy()
        
        return X_scaled, y_success, y_duration
    
    def split_data(
        self, 
        X: pd.DataFrame, 
        y_success: pd.Series = None,
        y_duration: pd.Series = None,
        test_size: float = None, 
        random_state: int = None
    ) -> Tuple:
        """
        Split data into training and testing sets for both targets
        """
        test_size = test_size or MODEL_CONFIG['test_size']
        random_state = random_state or MODEL_CONFIG['random_state']
        
        if y_success is not None:
            X_train, X_test, y_success_train, y_success_test = train_test_split(
                X, y_success, test_size=test_size, random_state=random_state, stratify=y_success
            )
            
            print(f"\n=== Data Split ===")
            print(f"Training set: {X_train.shape[0]} samples")
            print(f"Test set: {X_test.shape[0]} samples")
            print(f"Training success rate: {y_success_train.mean():.2%}")
            print(f"Test success rate: {y_success_test.mean():.2%}")
            
            if y_duration is not None:
                # Use same indices for duration split
                y_duration_train = y_duration.loc[X_train.index]
                y_duration_test = y_duration.loc[X_test.index]
                
                print(f"Training avg duration: {y_duration_train.mean():.1f} min")
                print(f"Test avg duration: {y_duration_test.mean():.1f} min")
                
                return X_train, X_test, y_success_train, y_success_test, y_duration_train, y_duration_test
            
            return X_train, X_test, y_success_train, y_success_test, None, None
        
        return None, None, None, None, None, None


if __name__ == "__main__":
    from data_loader import load_data
    
    print("Testing data preprocessor...")
    
    # Load data
    df = load_data()
    
    # Initialize preprocessor
    preprocessor = DataPreprocessor()
    
    # Explore data
    preprocessor.explore_data(df)
    
    # Prepare features
    X, y = preprocessor.prepare_features(df)
    print(f"\n=== Prepared Features ===")
    print(f"Feature matrix shape: {X.shape}")
    print(f"Target variable shape: {y.shape}")
    
    # Split data
    X_train, X_test, y_train, y_test = preprocessor.split_data(X, y)

