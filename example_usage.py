"""
Example usage of the Dispatch Success Predictor
"""

from predict import DispatchPredictor
import pandas as pd


def example_single_prediction():
    """Example: Single dispatch prediction"""
    print("="*70)
    print("EXAMPLE 1: Single Dispatch Prediction")
    print("="*70)
    
    # Initialize predictor
    predictor = DispatchPredictor()
    
    # Scenario 1: Short distance with skill match
    print("\n📍 Scenario 1: Short distance (10 units) + Skill Match")
    result = predictor.predict_single(distance=10, skill_match=1)
    print(f"   Success Probability: {result['success_probability']:.1%}")
    print(f"   Prediction: {'SUCCESS ✓' if result['success_prediction'] else 'FAILURE ✗'}")
    
    # Scenario 2: Long distance without skill match
    print("\n📍 Scenario 2: Long distance (80 units) + No Skill Match")
    result = predictor.predict_single(distance=80, skill_match=0)
    print(f"   Success Probability: {result['success_probability']:.1%}")
    print(f"   Prediction: {'SUCCESS ✓' if result['success_prediction'] else 'FAILURE ✗'}")
    
    # Scenario 3: Medium distance with skill match
    print("\n📍 Scenario 3: Medium distance (30 units) + Skill Match")
    result = predictor.predict_single(distance=30, skill_match=1)
    print(f"   Success Probability: {result['success_probability']:.1%}")
    print(f"   Prediction: {'SUCCESS ✓' if result['success_prediction'] else 'FAILURE ✗'}")


def example_batch_prediction():
    """Example: Batch dispatch predictions"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Batch Dispatch Predictions")
    print("="*70)
    
    # Initialize predictor
    predictor = DispatchPredictor()
    
    # Create sample dispatches
    dispatches = pd.DataFrame({
        'dispatch_id': [1, 2, 3, 4, 5],
        'distance': [15.0, 45.0, 8.0, 75.0, 25.0],
        'skill_match': [1, 1, 0, 0, 1],
        'technician_name': ['John', 'Sarah', 'Mike', 'Lisa', 'Tom']
    })
    
    print("\n📋 Dispatches to evaluate:")
    print(dispatches.to_string(index=False))
    
    # Make predictions
    results = predictor.predict_batch(dispatches)
    
    print("\n📊 Prediction Results:")
    display_cols = ['dispatch_id', 'technician_name', 'distance', 'skill_match', 
                    'success_prediction', 'success_probability']
    print(results[display_cols].to_string(index=False))
    
    # Summary
    success_count = results['success_prediction'].sum()
    print(f"\n✓ Predicted Successes: {success_count}/{len(results)}")
    print(f"✗ Predicted Failures: {len(results) - success_count}/{len(results)}")


def example_recommendation():
    """Example: Get detailed recommendations"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Detailed Dispatch Recommendations")
    print("="*70)
    
    # Initialize predictor
    predictor = DispatchPredictor()
    
    # Test different scenarios
    scenarios = [
        (5, 1, "Short distance with skill match"),
        (25, 1, "Medium distance with skill match"),
        (25, 0, "Medium distance without skill match"),
        (60, 0, "Long distance without skill match"),
    ]
    
    for distance, skill_match, description in scenarios:
        print(f"\n{'='*70}")
        print(f"Scenario: {description}")
        recommendation = predictor.get_recommendation(distance, skill_match)
        print(recommendation)


def example_decision_support():
    """Example: Using predictions for decision support"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Decision Support System")
    print("="*70)
    
    # Initialize predictor
    predictor = DispatchPredictor()
    
    # Scenario: Need to assign a dispatch, have multiple technicians
    print("\n🎯 Task: Assign dispatch for a job requiring Skill A")
    print("   Location: 35 units away")
    print("\n👥 Available Technicians:")
    
    technicians = pd.DataFrame({
        'technician_id': [101, 102, 103],
        'name': ['Alice', 'Bob', 'Charlie'],
        'skill': ['Skill A', 'Skill B', 'Skill A'],
        'distance': [35, 35, 35]
    })
    
    # Add skill match
    technicians['skill_match'] = (technicians['skill'] == 'Skill A').astype(int)
    
    print(technicians[['technician_id', 'name', 'skill']].to_string(index=False))
    
    # Predict for each technician
    results = predictor.predict_batch(technicians)
    
    print("\n📊 Success Predictions:")
    for _, row in results.iterrows():
        print(f"   {row['name']:10} (Skill: {row['skill']:8}) -> "
              f"Success Probability: {row['success_probability']:.1%}")
    
    # Recommendation
    best_tech = results.loc[results['success_probability'].idxmax()]
    print(f"\n✅ RECOMMENDATION: Assign to {best_tech['name']} "
          f"(Success Probability: {best_tech['success_probability']:.1%})")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("DISPATCH SUCCESS PREDICTOR - EXAMPLE USAGE")
    print("="*70)
    
    try:
        example_single_prediction()
        example_batch_prediction()
        example_recommendation()
        example_decision_support()
        
        print("\n" + "="*70)
        print("✓ All examples completed successfully!")
        print("="*70)
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("\n💡 TIP: Train the model first by running:")
        print("   python train_model.py")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    main()

