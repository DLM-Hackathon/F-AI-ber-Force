"""
Run all tests and verification checks
"""

import sys
import subprocess
import os


def run_command(command, description):
    """Run a command and report results"""
    print("\n" + "="*70)
    print(f"TEST: {description}")
    print("="*70)
    print(f"Command: {command}")
    print("-"*70)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            print(f"✓ {description} - PASSED")
            return True
        else:
            print(f"✗ {description} - FAILED")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ {description} - ERROR: {e}")
        return False


def check_file_exists(filepath, description):
    """Check if a file exists"""
    print(f"\nChecking {description}...")
    if os.path.exists(filepath):
        print(f"✓ {filepath} exists")
        return True
    else:
        print(f"✗ {filepath} not found")
        return False


def main():
    """Run all tests"""
    print("="*70)
    print("DISPATCH SUCCESS PREDICTOR - FULL TEST SUITE")
    print("="*70)
    
    results = []
    
    # Check required files
    print("\n" + "="*70)
    print("CHECKING REQUIRED FILES")
    print("="*70)
    
    required_files = [
        ('config.py', 'Configuration file'),
        ('data_loader.py', 'Data loader'),
        ('preprocessor.py', 'Preprocessor'),
        ('model.py', 'Model file'),
        ('train_model.py', 'Training script'),
        ('predict.py', 'Prediction script'),
        ('api.py', 'API server'),
        ('requirements.txt', 'Requirements'),
        ('.env', 'Environment variables (create from env.example)'),
    ]
    
    for filepath, description in required_files:
        result = check_file_exists(filepath, description)
        results.append((description, result))
    
    # Test 1: Database Connection
    result = run_command(
        'python test_connection.py',
        'Database Connection Test'
    )
    results.append(('Database Connection', result))
    
    # Test 2: Data Loading
    result = run_command(
        'python -c "from data_loader import load_data; df = load_data(); print(f\'Loaded {len(df)} records\')"',
        'Data Loading Test'
    )
    results.append(('Data Loading', result))
    
    # Test 3: Preprocessing
    result = run_command(
        'python -c "from data_loader import load_data; from preprocessor import DataPreprocessor; df = load_data(); p = DataPreprocessor(); X, y = p.prepare_features(df); print(f\'Features: {X.shape}\')"',
        'Data Preprocessing Test'
    )
    results.append(('Data Preprocessing', result))
    
    # Test 4: Model Training (if no model exists)
    if not os.path.exists('models/dispatch_success_model.pkl'):
        print("\n⚠️  No trained model found. Training now...")
        result = run_command(
            'python train_model.py',
            'Model Training'
        )
        results.append(('Model Training', result))
    else:
        print("\n✓ Model already exists, skipping training")
        results.append(('Model Training', True))
    
    # Test 5: Prediction
    result = run_command(
        'python predict.py --distance 25 --skill-match 1',
        'Single Prediction Test'
    )
    results.append(('Single Prediction', result))
    
    # Test 6: Example Usage (quick test)
    result = run_command(
        'python -c "from predict import DispatchPredictor; p = DispatchPredictor(); r = p.predict_single(25, 1); print(f\'Prediction: {r}\')"',
        'Python API Test'
    )
    results.append(('Python API', result))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed\n")
    
    for description, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {description}")
    
    print("\n" + "="*70)
    
    if passed == total:
        print("✓ ALL TESTS PASSED - System is ready!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Run predictions: python predict.py --distance 25 --skill-match 1")
        print("  2. Start API: python api.py")
        print("  3. Run examples: python example_usage.py")
        print("  4. Explore data: jupyter notebook explore_data.ipynb")
        return 0
    else:
        print("✗ SOME TESTS FAILED - Please review errors above")
        print("="*70)
        print("\nTroubleshooting:")
        print("  1. Check .env file has correct database credentials")
        print("  2. Ensure PostgreSQL is running")
        print("  3. Verify tables exist: dispatch_history_10k, technicians_10k")
        print("  4. Run: python test_connection.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())

