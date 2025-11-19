"""
Analyze historical data to determine optimal scaling for Dispatch Grade
"""
import pandas as pd
import numpy as np
from data_loader import DataLoader
import os

loader = DataLoader()
loader.connect()

schema = os.getenv('DB_SCHEMA', 'team_faiber_force')

# Query historical dispatch data with all needed fields
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
    dh."Productive_dispatch" as productive_dispatch,
    dh."First_time_fix" as first_time_fix,
    dh."Duration_min" as expected_duration,
    dh."Actual_duration_min" as actual_duration,
    dh."Appointment_start_time" as appointment_start_time,
    dh."Appointment_end_time" as appointment_end_time,
    dh."Customer_latitude" as customer_latitude,
    dh."Customer_longitude" as customer_longitude,
    t."Latitude" as technician_latitude,
    t."Longitude" as technician_longitude,
    -- Calculate distance
    (6371 * acos(
        cos(radians(dh."Customer_latitude")) *
        cos(radians(t."Latitude")) *
        cos(radians(t."Longitude") - radians(dh."Customer_longitude")) +
        sin(radians(dh."Customer_latitude")) *
        sin(radians(t."Latitude"))
    )) as distance
FROM
    {schema}.dispatch_history_10k dh
LEFT JOIN
    {schema}.technicians_10k t
ON
    dh."Assigned_technician_id" = t."Technician_id"
WHERE
    dh."Customer_latitude" IS NOT NULL
    AND dh."Customer_longitude" IS NOT NULL
    AND t."Latitude" IS NOT NULL
    AND t."Longitude" IS NOT NULL
    AND dh."Productive_dispatch" IS NOT NULL
    AND dh."Actual_duration_min" IS NOT NULL
    AND dh."Appointment_start_time" IS NOT NULL
    AND dh."Appointment_end_time" IS NOT NULL;
"""

print("Loading historical dispatch data...")
df = pd.read_sql_query(query, loader.connection)
loader.disconnect()

print(f"Loaded {len(df)} historical dispatches\n")

# Analyze Distance Distribution
print("="*70)
print("DISTANCE ANALYSIS")
print("="*70)
distances = df['distance'].dropna()
print(f"\nDistance Statistics:")
print(f"  Min:        {distances.min():.1f} km")
print(f"  25th %ile:  {distances.quantile(0.25):.1f} km")
print(f"  Median:     {distances.median():.1f} km")
print(f"  75th %ile:  {distances.quantile(0.75):.1f} km")
print(f"  90th %ile:  {distances.quantile(0.90):.1f} km")
print(f"  95th %ile:  {distances.quantile(0.95):.1f} km")
print(f"  99th %ile:  {distances.quantile(0.99):.1f} km")
print(f"  Max:        {distances.max():.1f} km")

# Analyze Duration Overrun
print("\n" + "="*70)
print("DURATION OVERRUN ANALYSIS")
print("="*70)

# Calculate scheduled time and overrun
df['appointment_start_time'] = pd.to_datetime(df['appointment_start_time'])
df['appointment_end_time'] = pd.to_datetime(df['appointment_end_time'])
df['scheduled_time'] = (df['appointment_end_time'] - df['appointment_start_time']).dt.total_seconds() / 60
df['overrun'] = df['actual_duration'] - df['scheduled_time']

overruns = df['overrun'].dropna()
print(f"\nOverrun Statistics:")
print(f"  Min:        {overruns.min():.1f} min (finished early)")
print(f"  25th %ile:  {overruns.quantile(0.25):.1f} min")
print(f"  Median:     {overruns.median():.1f} min")
print(f"  75th %ile:  {overruns.quantile(0.75):.1f} min")
print(f"  90th %ile:  {overruns.quantile(0.90):.1f} min")
print(f"  95th %ile:  {overruns.quantile(0.95):.1f} min")
print(f"  Max:        {overruns.max():.1f} min (finished late)")

# Count finish early vs late
early = (overruns < 0).sum()
on_time = (overruns == 0).sum()
late = (overruns > 0).sum()
print(f"\nFinish Timing:")
print(f"  Early:   {early} ({early/len(overruns)*100:.1f}%)")
print(f"  On-time: {on_time} ({on_time/len(overruns)*100:.1f}%)")
print(f"  Late:    {late} ({late/len(overruns)*100:.1f}%)")

# Analyze Success Rates
print("\n" + "="*70)
print("SUCCESS RATE ANALYSIS")
print("="*70)
productive_rate = df['productive_dispatch'].mean()
ftf_rate = df['first_time_fix'].mean()
print(f"\nProductive Dispatch Rate: {productive_rate:.1%}")
print(f"First Time Fix Rate:      {ftf_rate:.1%}")

# Recommend scaling parameters
print("\n" + "="*70)
print("RECOMMENDED SCALING PARAMETERS")
print("="*70)

# Distance scaling (exponential decay to 0 at ~250 km)
max_distance_for_zero = 250  # User requested 200-300 km
print(f"\nDistance Score (30 pts max, exponential decay):")
print(f"  0 km:       30.0 pts")
print(f"  10 km:      28.5 pts")
print(f"  25 km:      25.0 pts")
print(f"  50 km:      18.5 pts")
print(f"  100 km:     8.5 pts")
print(f"  150 km:     2.5 pts")
print(f"  {max_distance_for_zero}+ km:     0.0 pts")

# Duration scaling (based on actual overrun distribution)
# Most overruns are between -30 and +90 minutes
overrun_for_zero = 90  # 90 min late = 0 points
bonus_max = 30  # -30 min early = 36 points (30 + 6 bonus)
print(f"\nDuration Score (30 pts for on-time, bonus for early, penalty for late):")
print(f"  -30 min (early):  36.0 pts (bonus)")
print(f"  -15 min (early):  33.0 pts (bonus)")
print(f"  0 min (on-time):  30.0 pts")
print(f"  +15 min (late):   25.0 pts")
print(f"  +30 min (late):   20.0 pts")
print(f"  +60 min (late):   10.0 pts")
print(f"  +90 min (late):   0.0 pts")

print("\n" + "="*70)

