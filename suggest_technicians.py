"""
Suggest best technicians for dispatches (assigned or unassigned)
"""

import os
import pandas as pd
import pickle
from pathlib import Path
from data_loader import DataLoader
from config import MODEL_CONFIG


def load_unassigned_or_all_dispatches(only_unassigned=False):
    """Load dispatches from database"""
    loader = DataLoader()
    loader.connect()
    
    try:
        schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        
        # Get dispatches
        where_clause = 'WHERE cd."Assigned_technician_id" IS NULL' if only_unassigned else ''
        
        query = f"""
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
            cd."City" as city,
            cd."County" as county,
            cd."State" as state,
            cd."Optimized_technician_id" as optimized_technician_id,
            cd."Optimization_status" as optimization_status,
            cd."Optimization_confidence" as optimization_confidence
        FROM 
            {schema}.current_dispatches_csv cd
        {where_clause};
        """
        
        print(f"Loading {'unassigned ' if only_unassigned else ''}dispatches from database...")
        dispatches = pd.read_sql_query(query, loader.connection)
        print(f"✓ Loaded {len(dispatches)} dispatches")
        
        # Get all available technicians
        tech_query = f"""
        SELECT 
            t."Technician_id" as technician_id,
            t."Name" as technician_name,
            t."Primary_skill" as technician_skill,
            t."Latitude" as technician_latitude,
            t."Longitude" as technician_longitude,
            t."Current_assignments" as current_assignments,
            t."Workload_capacity" as workload_capacity
        FROM 
            {schema}.technicians_10k t;
        """
        
        print("Loading technicians...")
        technicians = pd.read_sql_query(tech_query, loader.connection)
        print(f"✓ Loaded {len(technicians)} technicians")
        
        return dispatches, technicians
        
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        raise
    finally:
        loader.disconnect()


def evaluate_technicians_for_dispatch(dispatch, technicians, preprocessor, success_model, duration_model):
    """Evaluate all technicians for a single dispatch"""
    
    # Create a row for each technician
    options = []
    for _, tech in technicians.iterrows():
        # Calculate distance
        import math
        
        lat1, lon1 = math.radians(dispatch['customer_latitude']), math.radians(dispatch['customer_longitude'])
        lat2, lon2 = math.radians(tech['technician_latitude']), math.radians(tech['technician_longitude'])
        
        distance = 6371 * math.acos(
            math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1) + 
            math.sin(lat1) * math.sin(lat2)
        )
        
        skill_match = 1 if dispatch['required_skill'] == tech['technician_skill'] else 0
        
        options.append({
            'dispatch_id': dispatch['dispatch_id'],
            'technician_id': tech['technician_id'],
            'technician_name': tech['technician_name'],
            'technician_skill': tech['technician_skill'],
            'current_assignments': tech['current_assignments'],
            'workload_capacity': tech['workload_capacity'],
            'distance': distance,
            'ticket_type': dispatch['ticket_type'],
            'order_type': dispatch['order_type'],
            'priority': dispatch['priority'],
            'required_skill': dispatch['required_skill'],
            'expected_duration': dispatch['expected_duration'],
            'skill_match': skill_match
        })
    
    options_df = pd.DataFrame(options)
    
    # Prepare features and predict
    features = options_df[['ticket_type', 'order_type', 'priority', 'required_skill',
                           'technician_skill', 'distance', 'expected_duration', 'skill_match']].copy()
    
    X, _, _ = preprocessor.prepare_features(features, fit_encoders=False)
    
    options_df['success_probability'] = success_model.predict_proba(X)[:, 1]
    options_df['estimated_duration'] = duration_model.predict(X)
    
    # Calculate a score (you can adjust weights)
    options_df['score'] = (
        options_df['success_probability'] * 100 +  # Success is most important
        (1 - options_df['distance'] / options_df['distance'].max()) * 20 +  # Closer is better
        options_df['skill_match'] * 30 +  # Skill match is important
        ((options_df['workload_capacity'] - options_df['current_assignments']) / 
         options_df['workload_capacity'].max()) * 10  # Available capacity
    )
    
    return options_df.sort_values('score', ascending=False)


def main(only_unassigned=False, top_n=5):
    """Main execution"""
    print("="*70)
    print("TECHNICIAN SUGGESTION ENGINE")
    print("="*70)
    
    # Load models
    print("\nLoading models...")
    preprocessor_path = MODEL_CONFIG['preprocessor_path']
    with open(preprocessor_path, 'rb') as f:
        preprocessor = pickle.load(f)
    
    success_model_path = MODEL_CONFIG['success_model_path']
    with open(success_model_path, 'rb') as f:
        success_model = pickle.load(f)
    
    duration_model_path = MODEL_CONFIG['duration_model_path']
    with open(duration_model_path, 'rb') as f:
        duration_model = pickle.load(f)
    
    print("✓ Models loaded")
    
    # Load data
    dispatches, technicians = load_unassigned_or_all_dispatches(only_unassigned)
    
    if len(dispatches) == 0:
        print("\n⚠️  No dispatches found")
        return
    
    print(f"\nAnalyzing {len(dispatches)} dispatches with {len(technicians)} technicians...")
    print(f"Evaluating {len(dispatches) * len(technicians)} possible assignments...")
    
    # Process each dispatch
    all_results = []
    
    for idx, dispatch in dispatches.iterrows():
        print(f"\nProcessing dispatch {dispatch['dispatch_id']} ({idx+1}/{len(dispatches)})...")
        
        options = evaluate_technicians_for_dispatch(
            dispatch, technicians, preprocessor, success_model, duration_model
        )
        
        # Keep top N options for this dispatch
        top_options = options.head(top_n).copy()
        top_options['rank'] = range(1, len(top_options) + 1)
        all_results.append(top_options)
        
        # Show best option
        best = top_options.iloc[0]
        print(f"  Best: {best['technician_name']} "
              f"(Success: {best['success_probability']:.1%}, "
              f"Distance: {best['distance']:.1f}km, "
              f"Skill Match: {'Yes' if best['skill_match'] else 'No'})")
    
    # Combine all results
    results = pd.concat(all_results, ignore_index=True)
    
    # Save results
    output_file = 'technician_suggestions.csv'
    results.to_csv(output_file, index=False)
    print(f"\n✓ Detailed results saved to {output_file}")
    
    # Create summary report
    print("\n" + "="*70)
    print("SUMMARY REPORT")
    print("="*70)
    
    best_assignments = results[results['rank'] == 1]
    
    print(f"\nTotal Dispatches: {len(dispatches)}")
    print(f"Average Success Probability (Best Match): {best_assignments['success_probability'].mean():.1%}")
    print(f"Average Distance (Best Match): {best_assignments['distance'].mean():.1f} km")
    print(f"Skill Match Rate (Best Match): {best_assignments['skill_match'].mean():.1%}")
    
    print(f"\nEstimated Success Rate if all assigned to best match: {best_assignments['success_probability'].mean():.1%}")
    
    # Show detailed recommendations for each dispatch
    print("\n" + "="*70)
    print(f"TOP {top_n} TECHNICIAN RECOMMENDATIONS PER DISPATCH")
    print("="*70)
    
    for dispatch_id in dispatches['dispatch_id'].head(10):  # Show first 10 dispatches
        dispatch_options = results[results['dispatch_id'] == dispatch_id]
        
        print(f"\nDispatch ID: {dispatch_id}")
        print(f"  Ticket Type: {dispatch_options.iloc[0]['ticket_type']}")
        print(f"  Required Skill: {dispatch_options.iloc[0]['required_skill']}")
        print(f"  Priority: {dispatch_options.iloc[0]['priority']}")
        print(f"\n  Top {top_n} Technicians:")
        
        for _, opt in dispatch_options.iterrows():
            print(f"    {opt['rank']}. {opt['technician_name']:<20} "
                  f"Success: {opt['success_probability']:>5.1%} | "
                  f"Distance: {opt['distance']:>5.1f}km | "
                  f"Skill: {opt['technician_skill']:<15} | "
                  f"Match: {'✓' if opt['skill_match'] else '✗'} | "
                  f"Score: {opt['score']:.1f}")
    
    print("\n" + "="*70)
    print(f"✓ COMPLETE - Full results in {output_file}")
    print("="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Suggest best technicians for dispatches')
    parser.add_argument('--unassigned-only', action='store_true',
                       help='Only process unassigned dispatches')
    parser.add_argument('--top-n', type=int, default=5,
                       help='Number of top technicians to suggest per dispatch (default: 5)')
    
    args = parser.parse_args()
    
    main(only_unassigned=args.unassigned_only, top_n=args.top_n)

