"""
Make predictions on current dispatches from the database
Supports hybrid ML + rule-based predictions for better accuracy
"""

import os
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from data_loader import DataLoader
from config import MODEL_CONFIG, DB_CONFIG
from business_rules import DispatchBusinessRules, blend_probabilities


def load_current_dispatches():
    """Load current dispatches from database with technician info"""
    loader = DataLoader()
    loader.connect()
    
    try:
        schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        
        # Query to get current dispatches with technician information and workload
        query = f"""
        WITH daily_counts AS (
            SELECT 
                "Assigned_technician_id",
                DATE("Appointment_start_datetime") as dispatch_date,
                COUNT(*) as daily_dispatch_count
            FROM {schema}.current_dispatches_csv
            WHERE "Assigned_technician_id" IS NOT NULL
            GROUP BY "Assigned_technician_id", DATE("Appointment_start_datetime")
        )
        SELECT 
            cd."Dispatch_id" as dispatch_id,
            cd."Ticket_type" as ticket_type,
            cd."Order_type" as order_type,
            cd."Priority" as priority,
            cd."Required_skill" as required_skill,
            cd."Assigned_technician_id" as assigned_technician_id,
            cd."Customer_latitude" as customer_latitude,
            cd."Customer_longitude" as customer_longitude,
            cd."Duration_min" as expected_duration,
            cd."Status" as status,
            cd."Appointment_start_datetime" as appointment_start_datetime,
            cd."Appointment_end_datetime" as appointment_end_datetime,
            cd."Street" as street,
            cd."City" as city,
            cd."County" as county,
            cd."State" as state,
            cd."Postal_code" as postal_code,
            cd."Optimized_technician_id" as optimized_technician_id,
            cd."Optimization_status" as optimization_status,
            cd."Optimization_confidence" as optimization_confidence,
            t."Technician_id" as technician_id,
            t."Name" as technician_name,
            t."Primary_skill" as technician_skill,
            t."Latitude" as technician_latitude,
            t."Longitude" as technician_longitude,
            tc."Max_assignments" as max_assignments,
            -- Calculate distance using Haversine formula (in kilometers)
            (6371 * acos(
                cos(radians(cd."Customer_latitude")) * 
                cos(radians(t."Latitude")) * 
                cos(radians(t."Longitude") - radians(cd."Customer_longitude")) + 
                sin(radians(cd."Customer_latitude")) * 
                sin(radians(t."Latitude"))
            )) as distance,
            CASE 
                WHEN cd."Required_skill" = t."Primary_skill" THEN 1 
                ELSE 0 
            END as skill_match,
            -- Workload ratio: daily assignments / max assignments for that date
            CAST(dc.daily_dispatch_count AS FLOAT) / NULLIF(tc."Max_assignments", 0) as workload_ratio
        FROM 
            {schema}.current_dispatches_csv cd
        LEFT JOIN 
            {schema}.technicians_10k t 
        ON 
            cd."Assigned_technician_id" = t."Technician_id"
        LEFT JOIN
            {schema}.technician_calendar_10k tc
        ON
            cd."Assigned_technician_id" = tc."Technician_id"
            AND DATE(cd."Appointment_start_datetime") = tc."Date"::date
        LEFT JOIN
            daily_counts dc
        ON
            cd."Assigned_technician_id" = dc."Assigned_technician_id"
            AND DATE(cd."Appointment_start_datetime") = dc.dispatch_date
        WHERE 
            cd."Customer_latitude" IS NOT NULL 
            AND cd."Customer_longitude" IS NOT NULL
            AND t."Latitude" IS NOT NULL
            AND t."Longitude" IS NOT NULL
            AND cd."Assigned_technician_id" IS NOT NULL
            AND tc."Max_assignments" IS NOT NULL
            AND tc."Max_assignments" > 0;
        """
        
        print("Loading current dispatches from database...")
        df = pd.read_sql_query(query, loader.connection)
        print(f"[OK] Loaded {len(df)} current dispatches")
        
        return df
        
    except Exception as e:
        print(f"[ERROR] Error loading dispatches: {e}")
        raise
    finally:
        loader.disconnect()


def make_predictions(df, rule_weight=0.7, use_hybrid=True):
    """
    Make predictions on dispatch data using hybrid ML + rule-based approach
    
    Args:
        df: DataFrame with dispatch data
        rule_weight: Weight for rule-based predictions (0-1), default 0.7 = 70% rules
        use_hybrid: If True, blend ML and rules. If False, use only ML predictions.
    
    Returns:
        DataFrame with predictions
    """
    
    # Load preprocessor
    preprocessor_path = MODEL_CONFIG['preprocessor_path']
    if not Path(preprocessor_path).exists():
        raise FileNotFoundError(f"Preprocessor not found: {preprocessor_path}. Run train_model.py first!")
    
    print(f"\nLoading preprocessor from {preprocessor_path}...")
    with open(preprocessor_path, 'rb') as f:
        preprocessor = pickle.load(f)
    print("[OK] Preprocessor loaded")
    
    # Load models
    success_model_path = MODEL_CONFIG['success_model_path']
    duration_model_path = MODEL_CONFIG['duration_model_path']
    
    if not Path(success_model_path).exists():
        raise FileNotFoundError(f"Success model not found: {success_model_path}. Run train_model.py first!")
    
    print(f"Loading success model from {success_model_path}...")
    with open(success_model_path, 'rb') as f:
        success_model = pickle.load(f)
    print("[OK] Success model loaded")
    
    print(f"Loading duration model from {duration_model_path}...")
    with open(duration_model_path, 'rb') as f:
        duration_model = pickle.load(f)
    print("[OK] Duration model loaded")
    
    # Prepare features
    print("\nPreparing features...")
    features = df[['ticket_type', 'order_type', 'priority', 'required_skill', 
                   'technician_skill', 'distance', 'expected_duration', 'skill_match', 'workload_ratio']].copy()
    
    X, _, _ = preprocessor.prepare_features(features, fit_encoders=False)
    print(f"[OK] Features prepared: {X.shape}")
    
    # Make ML predictions
    print("\nMaking ML predictions...")
    ml_success_predictions = success_model.predict(X)
    ml_success_probabilities = success_model.predict_proba(X)[:, 1]
    duration_predictions = duration_model.predict(X)
    print("[OK] ML predictions complete")
    
    # Calculate rule-based probabilities
    if use_hybrid:
        print(f"\nCalculating rule-based probabilities (weight: {rule_weight:.0%})...")
        rules = DispatchBusinessRules()
        rule_probabilities = rules.calculate_probabilities(df)
        print("[OK] Rule-based probabilities calculated")
        
        # Blend probabilities
        print(f"Blending predictions ({rule_weight:.0%} rules, {1-rule_weight:.0%} ML)...")
        blended_probabilities = np.array([
            blend_probabilities(ml_prob, rule_prob, rule_weight)
            for ml_prob, rule_prob in zip(ml_success_probabilities, rule_probabilities)
        ])
        success_probabilities = blended_probabilities
        success_predictions = (blended_probabilities >= 0.5).astype(int)
        print("[OK] Hybrid predictions complete")
    else:
        success_probabilities = ml_success_probabilities
        success_predictions = ml_success_predictions
        rule_probabilities = None
    
    # Add predictions to dataframe
    results = df.copy()
    results['success_prediction'] = success_predictions
    results['success_probability'] = success_probabilities
    results['failure_probability'] = 1 - success_probabilities
    results['estimated_duration'] = duration_predictions
    results['duration_difference'] = duration_predictions - results['expected_duration']
    
    # Add recommendation
    def get_recommendation(row):
        prob = row['success_probability']
        duration_diff = row['duration_difference']
        
        if prob >= 0.8:
            rec = "PROCEED"
            confidence = "High"
        elif prob >= 0.6:
            rec = "PROCEED WITH CAUTION"
            confidence = "Medium"
        elif prob >= 0.4:
            rec = "REVIEW"
            confidence = "Low"
        else:
            rec = "DO NOT PROCEED"
            confidence = "Very Low"
        
        # Add duration warning
        if duration_diff > row['expected_duration'] * 0.3:
            rec += f" (Warning: +{duration_diff:.0f} min)"
        
        return rec
    
    def get_confidence(row):
        prob = row['success_probability']
        if prob >= 0.8:
            return "High"
        elif prob >= 0.6:
            return "Medium"
        elif prob >= 0.4:
            return "Low"
        else:
            return "Very Low"
    
    results['recommendation'] = results.apply(get_recommendation, axis=1)
    results['confidence'] = results.apply(get_confidence, axis=1)
    
    return results


def main():
    """Main execution"""
    print("="*70)
    print("CURRENT DISPATCHES PREDICTION")
    print("="*70)
    
    # Step 1: Load dispatches
    print("\n[1/3] Loading current dispatches from database...")
    df = load_current_dispatches()
    
    if len(df) == 0:
        print("\n⚠️  No dispatches found in current_dispatches_csv table")
        print("Make sure the table exists and has data with assigned technicians")
        return
    
    print(f"\nFound {len(df)} dispatches to predict")
    print(f"Unique technicians: {df['technician_id'].nunique()}")
    print(f"Ticket types: {df['ticket_type'].unique().tolist()}")
    
    # Step 2: Make predictions
    print("\n[2/3] Making predictions...")
    results = make_predictions(df)
    
    # Step 3: Save results
    print("\n[3/3] Saving results...")
    
    # Save to CSV
    output_file = 'current_dispatches_predictions.csv'
    results.to_csv(output_file, index=False)
    print(f"[OK] Results saved to {output_file}")
    
    # Print summary statistics
    print("\n" + "="*70)
    print("PREDICTION SUMMARY")
    print("="*70)
    
    print(f"\nTotal Dispatches: {len(results)}")
    print(f"Predicted Successful: {results['success_prediction'].sum()} ({results['success_prediction'].mean():.1%})")
    print(f"Predicted Failures: {(~results['success_prediction']).sum()} ({(~results['success_prediction']).mean():.1%})")
    
    print(f"\nAverage Success Probability: {results['success_probability'].mean():.1%}")
    print(f"Average Expected Duration: {results['expected_duration'].mean():.1f} minutes")
    print(f"Average Estimated Duration: {results['estimated_duration'].mean():.1f} minutes")
    print(f"Average Duration Difference: {results['duration_difference'].mean():+.1f} minutes")
    
    print("\nRecommendation Breakdown:")
    print(results['recommendation'].value_counts().to_string())
    
    print("\nConfidence Levels:")
    print(results['confidence'].value_counts().to_string())
    
    # Show top risky dispatches
    print("\n" + "="*70)
    print("TOP 10 RISKIEST DISPATCHES (Lowest Success Probability)")
    print("="*70)
    
    risky = results.nsmallest(10, 'success_probability')
    display_cols = ['dispatch_id', 'technician_name', 'ticket_type', 'priority', 
                    'distance', 'skill_match', 'success_probability', 'recommendation']
    print(risky[display_cols].to_string(index=False))
    
    # Show dispatches with significant duration overrun
    print("\n" + "="*70)
    print("TOP 10 DISPATCHES WITH LONGEST ESTIMATED OVERRUN")
    print("="*70)
    
    overrun = results.nlargest(10, 'duration_difference')
    display_cols = ['dispatch_id', 'technician_name', 'ticket_type', 'expected_duration', 
                    'estimated_duration', 'duration_difference']
    print(overrun[display_cols].to_string(index=False))
    
    print("\n" + "="*70)
    print(f"[OK] COMPLETE - Results saved to {output_file}")
    print("="*70)


if __name__ == "__main__":
    main()

