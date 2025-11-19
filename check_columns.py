"""
Check actual column names in the database to identify case-sensitivity issues
"""

import os
from data_loader import DataLoader

def check_columns():
    """Check column names for both tables"""
    loader = DataLoader()
    
    try:
        loader.connect()
        schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        
        print("="*70)
        print("CHECKING COLUMN NAMES IN DATABASE")
        print("="*70)
        print(f"Schema: {schema}\n")
        
        # Check dispatch_history_10k columns
        print("="*70)
        print("TABLE: dispatch_history_10k")
        print("="*70)
        
        query1 = f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = '{schema}'
          AND table_name = 'dispatch_history_10k'
        ORDER BY ordinal_position;
        """
        
        import pandas as pd
        df1 = pd.read_sql_query(query1, loader.connection)
        
        if len(df1) > 0:
            print("\nActual column names (copy these EXACTLY):\n")
            for idx, row in df1.iterrows():
                col_name = row['column_name']
                data_type = row['data_type']
                
                # Check if column name has capital letters
                if col_name != col_name.lower():
                    needs_quotes = '  ⚠️  NEEDS QUOTES (has capital letters)'
                else:
                    needs_quotes = ''
                
                print(f"  {col_name:<40} ({data_type}){needs_quotes}")
        else:
            print("  ✗ Table not found or no columns returned")
        
        # Check technicians_10k columns
        print("\n" + "="*70)
        print("TABLE: technicians_10k")
        print("="*70)
        
        query2 = f"""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = '{schema}'
          AND table_name = 'technicians_10k'
        ORDER BY ordinal_position;
        """
        
        df2 = pd.read_sql_query(query2, loader.connection)
        
        if len(df2) > 0:
            print("\nActual column names (copy these EXACTLY):\n")
            for idx, row in df2.iterrows():
                col_name = row['column_name']
                data_type = row['data_type']
                
                # Check if column name has capital letters
                if col_name != col_name.lower():
                    needs_quotes = '  ⚠️  NEEDS QUOTES (has capital letters)'
                else:
                    needs_quotes = ''
                
                print(f"  {col_name:<40} ({data_type}){needs_quotes}")
        else:
            print("  ✗ Table not found or no columns returned")
        
        # Summary
        print("\n" + "="*70)
        print("IMPORTANT: PostgreSQL Column Name Rules")
        print("="*70)
        print("""
Unquoted column names: converted to lowercase
  Example: SELECT my_column        → finds "my_column" or "MY_COLUMN"
  
Quoted column names: case-sensitive, must match exactly
  Example: SELECT "My_Column"      → finds only "My_Column"
  
If a column has ANY capital letters, you MUST use quotes in SQL queries!
        """)
        
        loader.disconnect()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure:")
        print("  1. Your .env file has correct credentials")
        print("  2. Database = postgres")
        print("  3. Schema = team_faiber_force")
        return False
    
    return True

if __name__ == "__main__":
    check_columns()

