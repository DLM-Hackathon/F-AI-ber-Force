"""
Prediction script for dispatch success and duration
"""

import argparse
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from config import MODEL_CONFIG, FEATURE_COLUMNS


class DispatchPredictor:
    """Class for making predictions on new dispatch requests"""
    
    def __init__(self, success_model_path: str = None, duration_model_path: str = None, preprocessor_path: str = None):
        """Initialize predictor with saved models and preprocessor"""
        self.success_model_path = success_model_path or MODEL_CONFIG['success_model_path']
        self.duration_model_path = duration_model_path or MODEL_CONFIG['duration_model_path']
        self.preprocessor_path = preprocessor_path or MODEL_CONFIG['preprocessor_path']
        
        self.success_model = None
        self.duration_model = None
        self.preprocessor = None
        self.load_models()
    
    def load_models(self):
        """Load the trained models and preprocessor"""
        # Load success model
        if not Path(self.success_model_path).exists():
            raise FileNotFoundError(f"Success model file not found: {self.success_model_path}")
        
        with open(self.success_model_path, 'rb') as f:
            self.success_model = pickle.load(f)
        print(f"✓ Success model loaded from {self.success_model_path}")
        
        # Load duration model
        if not Path(self.duration_model_path).exists():
            raise FileNotFoundError(f"Duration model file not found: {self.duration_model_path}")
        
        with open(self.duration_model_path, 'rb') as f:
            self.duration_model = pickle.load(f)
        print(f"✓ Duration model loaded from {self.duration_model_path}")
        
        # Load preprocessor
        if not Path(self.preprocessor_path).exists():
            raise FileNotFoundError(f"Preprocessor file not found: {self.preprocessor_path}")
        
        with open(self.preprocessor_path, 'rb') as f:
            self.preprocessor = pickle.load(f)
        print(f"✓ Preprocessor loaded from {self.preprocessor_path}")
    
    def predict_single(self, ticket_type: str, order_type: str, priority: str, 
                      required_skill: str, technician_skill: str, distance: float, 
                      expected_duration: float) -> dict:
        """
        Predict success and duration for a single dispatch
        
        Args:
            ticket_type: Type of ticket (e.g., 'Installation', 'Repair', etc.)
            order_type: Type of order
            priority: Priority level (e.g., 'High', 'Medium', 'Low')
            required_skill: Skill required for the dispatch
            technician_skill: Technician's skill
            distance: Distance in km (calculated from lat/lon)
            expected_duration: Expected duration in minutes
        
        Returns:
            Dictionary with predictions and probabilities
        """
        # Calculate skill match
        skill_match = 1 if required_skill == technician_skill else 0
        
        # Create feature dataframe
        features = pd.DataFrame({
            'ticket_type': [ticket_type],
            'order_type': [order_type],
            'priority': [priority],
            'required_skill': [required_skill],
            'technician_skill': [technician_skill],
            'distance': [distance],
            'expected_duration': [expected_duration],
            'skill_match': [skill_match]
        })
        
        # Preprocess features
        features_processed, _, _ = self.preprocessor.prepare_features(features, fit_encoders=False)
        
        # Make predictions
        success_prediction = self.success_model.predict(features_processed)[0]
        success_probability = self.success_model.predict_proba(features_processed)[0]
        duration_prediction = self.duration_model.predict(features_processed)[0]
        
        return {
            'success_prediction': bool(success_prediction),
            'success_probability': float(success_probability[1]),
            'failure_probability': float(success_probability[0]),
            'estimated_duration': float(duration_prediction),
            'expected_duration': expected_duration,
            'duration_difference': float(duration_prediction - expected_duration),
            'inputs': {
                'ticket_type': ticket_type,
                'order_type': order_type,
                'priority': priority,
                'required_skill': required_skill,
                'technician_skill': technician_skill,
                'distance': distance,
                'skill_match': bool(skill_match)
            }
        }
    
    def predict_batch(self, dispatches: pd.DataFrame) -> pd.DataFrame:
        """
        Predict success and duration for multiple dispatches
        
        Args:
            dispatches: DataFrame with required columns
        
        Returns:
            DataFrame with predictions
        """
        # Ensure required columns exist
        required_cols = ['ticket_type', 'order_type', 'priority', 'required_skill', 
                        'technician_skill', 'distance', 'expected_duration']
        missing_cols = [col for col in required_cols if col not in dispatches.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Calculate skill match if not present
        if 'skill_match' not in dispatches.columns:
            dispatches['skill_match'] = (dispatches['required_skill'] == dispatches['technician_skill']).astype(int)
        
        # Preprocess features
        features = dispatches[FEATURE_COLUMNS].copy()
        features_processed, _, _ = self.preprocessor.prepare_features(features, fit_encoders=False)
        
        # Make predictions
        success_predictions = self.success_model.predict(features_processed)
        success_probabilities = self.success_model.predict_proba(features_processed)
        duration_predictions = self.duration_model.predict(features_processed)
        
        # Add to dataframe
        result = dispatches.copy()
        result['success_prediction'] = success_predictions
        result['success_probability'] = success_probabilities[:, 1]
        result['failure_probability'] = success_probabilities[:, 0]
        result['estimated_duration'] = duration_predictions
        result['duration_difference'] = duration_predictions - result['expected_duration']
        
        return result
    
    def get_recommendation(self, ticket_type: str, order_type: str, priority: str,
                          required_skill: str, technician_skill: str, distance: float,
                          expected_duration: float) -> str:
        """
        Get a detailed recommendation for the dispatch
        
        Returns:
            Recommendation string
        """
        result = self.predict_single(ticket_type, order_type, priority, required_skill,
                                     technician_skill, distance, expected_duration)
        
        prob = result['success_probability']
        est_duration = result['estimated_duration']
        exp_duration = result['expected_duration']
        duration_diff = result['duration_difference']
        
        if prob >= 0.8:
            confidence = "High"
            recommendation = "PROCEED - High probability of success"
        elif prob >= 0.6:
            confidence = "Medium"
            recommendation = "PROCEED WITH CAUTION - Moderate probability of success"
        elif prob >= 0.4:
            confidence = "Low"
            recommendation = "REVIEW - Low probability of success, consider reassignment"
        else:
            confidence = "Very Low"
            recommendation = "DO NOT PROCEED - Very low probability of success, reassign dispatch"
        
        # Duration warning
        duration_warning = ""
        if duration_diff > exp_duration * 0.3:  # More than 30% longer than expected
            duration_warning = f"\n⚠️  WARNING: Estimated duration is {duration_diff:.0f} minutes longer than expected"
        elif duration_diff < 0:
            duration_warning = f"\n✓ Duration likely {abs(duration_diff):.0f} minutes shorter than expected"
        
        return f"""
Dispatch Recommendation
{'='*70}
Ticket Type: {ticket_type}
Order Type: {order_type}
Priority: {priority}
Required Skill: {required_skill}
Technician Skill: {technician_skill}
Distance: {distance:.1f} km
Skill Match: {'Yes' if required_skill == technician_skill else 'No'}

Success Prediction: {'SUCCESS ✓' if result['success_prediction'] else 'FAILURE ✗'}
Success Probability: {prob:.1%}
Confidence: {confidence}

Duration Estimates:
  Expected: {exp_duration:.0f} minutes
  Estimated: {est_duration:.0f} minutes
  Difference: {duration_diff:+.0f} minutes{duration_warning}

Recommendation: {recommendation}
{'='*70}
        """


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Predict dispatch success and duration')
    parser.add_argument('--ticket-type', type=str, required=True, help='Ticket type')
    parser.add_argument('--order-type', type=str, required=True, help='Order type')
    parser.add_argument('--priority', type=str, required=True, help='Priority level')
    parser.add_argument('--required-skill', type=str, required=True, help='Required skill')
    parser.add_argument('--technician-skill', type=str, required=True, help='Technician skill')
    parser.add_argument('--distance', type=float, required=True, help='Distance in km')
    parser.add_argument('--expected-duration', type=float, required=True, help='Expected duration in minutes')
    
    args = parser.parse_args()
    
    # Make prediction
    predictor = DispatchPredictor()
    recommendation = predictor.get_recommendation(
        args.ticket_type, args.order_type, args.priority,
        args.required_skill, args.technician_skill,
        args.distance, args.expected_duration
    )
    print(recommendation)


if __name__ == "__main__":
    main()
