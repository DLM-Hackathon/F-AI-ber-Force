"""
Test database connection and verify data availability
"""

from data_loader import DataLoader
import sys



def test_connection():
    """Test database connection and data access"""
    import os
    print("="*70)
    print("DATABASE CONNECTION TEST")
    print("="*70)
    print(f"Database: {os.getenv('DB_NAME', 'postgres')}")
    print(f"Schema: {os.getenv('DB_SCHEMA', 'team_faiber_force')}")
    print("="*70)
    
    loader = DataLoader()
    
    # Test 1: Connection
    print("\n[1/4] Testing database connection...")
    try:
        loader.connect()
        print("   ✓ Connection successful")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("\n💡 TIP: Check your .env file with database credentials")
        return False
    
    # Test 2: Check tables exist
    print("\n[2/4] Checking if required tables exist...")
    try:
        # Try to get table info
        dispatch_info = loader.get_table_info('dispatch_history_10k')
        tech_info = loader.get_table_info('technicians_10k')
        
        if len(dispatch_info) > 0:
            print("   ✓ dispatch_history_10k table found")
            print(f"     Columns: {', '.join(dispatch_info['column_name'].tolist())}")
        else:
            print("   ✗ dispatch_history_10k table not found")
            
        if len(tech_info) > 0:
            print("   ✓ technicians_10k table found")
            print(f"     Columns: {', '.join(tech_info['column_name'].tolist())}")
        else:
            print("   ✗ technicians_10k table not found")
            
    except Exception as e:
        print(f"   ✗ Error checking tables: {e}")
        return False
    
    # Test 3: Check sample data
    print("\n[3/4] Checking sample data...")
    try:
        dispatch_sample = loader.get_sample_data('dispatch_history_10k', limit=3)
        tech_sample = loader.get_sample_data('technicians_10k', limit=3)
        
        print(f"   ✓ dispatch_history_10k has {len(dispatch_sample)} sample records")
        print(f"   ✓ technicians_10k has {len(tech_sample)} sample records")
        
        print("\n   Sample from dispatch_history_10k:")
        print("   " + str(dispatch_sample.head(3).to_string()).replace('\n', '\n   '))
        
        print("\n   Sample from technicians_10k:")
        print("   " + str(tech_sample.head(3).to_string()).replace('\n', '\n   '))
        
    except Exception as e:
        print(f"   ✗ Error reading sample data: {e}")
        return False
    
    # Test 4: Try to fetch joined data
    print("\n[4/4] Testing data join query...")
    try:
        df = loader.fetch_dispatch_data()
        print(f"   ✓ Successfully fetched {len(df)} joined records")
        
        print(f"\n   Data summary:")
        print(f"   - Total records: {len(df)}")
        print(f"   - Date range: {df['dispatch_time'].min()} to {df['dispatch_time'].max()}" if 'dispatch_time' in df.columns else "")
        print(f"   - Success rate: {df['success'].mean():.2%}" if 'success' in df.columns else "")
        print(f"   - Skill match rate: {df['skill_match'].mean():.2%}" if 'skill_match' in df.columns else "")
        print(f"   - Average distance: {df['distance'].mean():.1f}" if 'distance' in df.columns else "")
        
    except Exception as e:
        print(f"   ✗ Error fetching joined data: {e}")
        return False
    
    loader.disconnect()
    
    print("\n" + "="*70)
    print("✓ ALL TESTS PASSED - Database is ready!")
    print("="*70)
    print("\n💡 Next step: Train the model by running:")
    print("   python train_model.py")
    
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

