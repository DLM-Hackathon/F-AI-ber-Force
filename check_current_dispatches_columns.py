"""
Check column names in current_dispatches_csv table
"""

import os
from data_loader import DataLoader

def check_current_dispatches_columns():
    """Check column names in current_dispatches_csv"""
    loader = DataLoader()
    
    try:
        loader.connect()
        schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        
        print("="*70)
        print("CHECKING CURRENT_DISPATCHES_CSV COLUMNS")
        print("="*70)
        print(f"Schema: {schema}\n")
        
        query = f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = '{schema}'
          AND table_name = 'current_dispatches_csv'
        ORDER BY ordinal_position;
        """
        
        import pandas as pd
        df = pd.read_sql_query(query, loader.connection)
        
        if len(df) > 0:
            print("Actual column names in current_dispatches_csv:\n")
            for idx, row in df.iterrows():
                col_name = row['column_name']
                data_type = row['data_type']
                
                # Check if column name has capital letters
                if col_name != col_name.lower():
                    needs_quotes = '  ⚠️  NEEDS QUOTES'
                else:
                    needs_quotes = ''
                
                print(f"  {col_name:<50} ({data_type}){needs_quotes}")
                
            print("\n" + "="*70)
            print("Copy the EXACT column names above to update the script")
            print("="*70)
        else:
            print("  ✗ Table 'current_dispatches_csv' not found in schema")
            print(f"\nAvailable tables in schema '{schema}':")
            
            tables_query = f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = '{schema}'
            ORDER BY table_name;
            """
            tables_df = pd.read_sql_query(tables_query, loader.connection)
            for table in tables_df['table_name']:
                print(f"  - {table}")
        
        loader.disconnect()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_current_dispatches_columns()

