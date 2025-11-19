"""
Data loader for extracting dispatch history from PostgreSQL
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from config import DB_CONFIG


class DataLoader:
    """Handles database connection and data extraction"""
    
    def __init__(self, db_config: dict = None):
        """Initialize database connection"""
        self.db_config = db_config or DB_CONFIG
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            print(f"[OK] Connected to database: {self.db_config['database']}")
        except Exception as e:
            print(f"[ERROR] Error connecting to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("[OK] Database connection closed")
    
    def fetch_dispatch_data(self) -> pd.DataFrame:
        """
        Fetch dispatch history with technician skills and calculated distance
        Joins dispatch_history_10k with technicians_10k on assigned_technician_id
        Calculates distance using Haversine formula from lat/lon coordinates
        Calculates workload ratio based on daily assignments vs capacity
        """
        # Get schema name from environment or use default
        schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        
        query = f"""
        WITH daily_counts AS (
            SELECT 
                "Assigned_technician_id",
                DATE("Appointment_start_time") as dispatch_date,
                COUNT(*) as daily_dispatch_count
            FROM {schema}.dispatch_history_10k
            WHERE "Assigned_technician_id" IS NOT NULL
            GROUP BY "Assigned_technician_id", DATE("Appointment_start_time")
        )
        SELECT 
            dh."Dispatch_id" as dispatch_id,
            dh."Ticket_type" as ticket_type,
            dh."Order_type" as order_type,
            dh."Priority" as priority,
            dh."Required_skill" as required_skill,
            dh."Assigned_technician_id" as assigned_technician_id,
            dh."Customer_latitude" as customer_latitude,
            dh."Customer_longitude" as customer_longitude,
            dh."Duration_min" as expected_duration,
            dh."Actual_duration_min" as actual_duration,
            dh."Productive_dispatch" as success,
            dh."Appointment_start_time" as dispatch_time,
            dh."Appointment_end_time" as completion_time,
            t."Primary_skill" as technician_skill,
            t."Latitude" as technician_latitude,
            t."Longitude" as technician_longitude,
            t."Workload_capacity" as workload_capacity,
            -- Calculate distance using Haversine formula (in kilometers)
            -- Formula: 2 * R * asin(sqrt(sin²((lat2-lat1)/2) + cos(lat1) * cos(lat2) * sin²((lon2-lon1)/2)))
            -- R = 6371 km (Earth's radius)
            (6371 * acos(
                cos(radians(dh."Customer_latitude")) * 
                cos(radians(t."Latitude")) * 
                cos(radians(t."Longitude") - radians(dh."Customer_longitude")) + 
                sin(radians(dh."Customer_latitude")) * 
                sin(radians(t."Latitude"))
            )) as distance,
            CASE 
                WHEN dh."Required_skill" = t."Primary_skill" THEN 1 
                ELSE 0 
            END as skill_match,
            -- Workload ratio: daily assignments / capacity
            CAST(dc.daily_dispatch_count AS FLOAT) / NULLIF(t."Workload_capacity", 0) as workload_ratio
        FROM 
            {schema}.dispatch_history_10k dh
        LEFT JOIN 
            {schema}.technicians_10k t 
        ON 
            dh."Assigned_technician_id" = t."Technician_id"
        LEFT JOIN
            daily_counts dc
        ON
            dh."Assigned_technician_id" = dc."Assigned_technician_id"
            AND DATE(dh."Appointment_start_time") = dc.dispatch_date
        WHERE 
            dh."Customer_latitude" IS NOT NULL 
            AND dh."Customer_longitude" IS NOT NULL
            AND t."Latitude" IS NOT NULL
            AND t."Longitude" IS NOT NULL
            AND dh."Productive_dispatch" IS NOT NULL
            AND dh."Actual_duration_min" IS NOT NULL
            AND dh."Assigned_technician_id" IS NOT NULL
            AND t."Workload_capacity" IS NOT NULL
            AND t."Workload_capacity" > 0;
        """
        
        try:
            df = pd.read_sql_query(query, self.connection)
            print(f"[OK] Fetched {len(df)} records from database")
            print(f"[OK] Workload ratio range: {df['workload_ratio'].min():.2f} to {df['workload_ratio'].max():.2f}")
            return df
        except Exception as e:
            print(f"[ERROR] Error fetching data: {e}")
            raise
    
    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """Get column information for a table"""
        schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        query = f"""
        SELECT 
            column_name, 
            data_type, 
            is_nullable
        FROM 
            information_schema.columns
        WHERE 
            table_schema = '{schema}'
            AND table_name = '{table_name}';
        """
        
        try:
            df = pd.read_sql_query(query, self.connection)
            return df
        except Exception as e:
            print(f"[ERROR] Error getting table info: {e}")
            raise
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> pd.DataFrame:
        """Get sample records from a table"""
        schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        query = f"SELECT * FROM {schema}.{table_name} LIMIT {limit};"
        
        try:
            df = pd.read_sql_query(query, self.connection)
            return df
        except Exception as e:
            print(f"[ERROR] Error getting sample data: {e}")
            raise


def load_data() -> pd.DataFrame:
    """Convenience function to load dispatch data"""
    loader = DataLoader()
    loader.connect()
    
    try:
        data = loader.fetch_dispatch_data()
        return data
    finally:
        loader.disconnect()


if __name__ == "__main__":
    # Test data loading
    print("Testing data loader...")
    loader = DataLoader()
    loader.connect()
    
    # Check table structures
    print("\n=== dispatch_history_10k table structure ===")
    print(loader.get_table_info('dispatch_history_10k'))
    
    print("\n=== technicians_10k table structure ===")
    print(loader.get_table_info('technicians_10k'))
    
    # Fetch data
    print("\n=== Loading dispatch data ===")
    df = loader.fetch_dispatch_data()
    print(f"\nDataset shape: {df.shape}")
    print(f"\nFirst few rows:")
    print(df.head())
    print(f"\nData types:")
    print(df.dtypes)
    print(f"\nMissing values:")
    print(df.isnull().sum())
    
    loader.disconnect()

