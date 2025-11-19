"""
Calculate Dispatch Grades for historical data
"""
import pandas as pd
import numpy as np
from data_loader import DataLoader
import os

def calculate_dispatch_grade(distance, overrun, productive_dispatch, first_time_fix, 
                             use_probabilities=False, success_prob=None):
    """
    Calculate Dispatch Grade (0-100 scale)
    
    Args:
        distance: Distance in km
        overrun: Duration overrun in minutes (negative = early, positive = late)
        productive_dispatch: Binary (1/0) or probability if use_probabilities=True
        first_time_fix: Binary (1/0) or probability if use_probabilities=True
        use_probabilities: If True, use success_prob for both productive and FTF
        success_prob: Success probability (0-1) when use_probabilities=True
    
    Returns:
        grade: Total grade (0-100)
    """
    grade = 0
    
    # === DISTANCE SCORE (30 pts max, exponential decay) ===
    # 0 pts at 250+ km, 30 pts at 0 km
    max_distance_for_zero = 250
    if distance >= max_distance_for_zero:
        distance_score = 0
    else:
        # Exponential decay: score = 30 * exp(-k * distance)
        # At 250km: exp(-k * 250) ≈ 0, so k ≈ 0.02
        k = 0.02
        distance_score = 30 * np.exp(-k * distance)
        distance_score = max(0, min(30, distance_score))
    
    grade += distance_score
    
    # === DURATION SCORE (30 pts base, bonus for early, penalty for late) ===
    # On-time (0 overrun) = 30 pts
    # Early finish gets bonus (up to 6 pts for -30 min)
    # Late finish gets penalty (0 pts at +90 min)
    
    if overrun <= 0:
        # Early finish - bonus points
        # -30 min = +6 pts bonus
        bonus = min(6, abs(overrun) / 30 * 6)
        duration_score = 30 + bonus
    else:
        # Late finish - penalty
        # +90 min = 0 pts
        penalty_rate = 30 / 90  # Lose 30 pts over 90 min
        duration_score = max(0, 30 - (overrun * penalty_rate))
    
    grade += duration_score
    
    # === PRODUCTIVE DISPATCH (25 pts) ===
    if use_probabilities and success_prob is not None:
        productive_score = success_prob * 25
    else:
        productive_score = productive_dispatch * 25
    
    grade += productive_score
    
    # === FIRST TIME FIX (15 pts) ===
    if use_probabilities and success_prob is not None:
        ftf_score = success_prob * 15
    else:
        ftf_score = first_time_fix * 15
    
    grade += ftf_score
    
    # Cap at 100
    grade = min(100, grade)
    
    return grade


# Load historical data with grades
loader = DataLoader()
loader.connect()

schema = os.getenv('DB_SCHEMA', 'team_faiber_force')

query = f"""
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
    AND dh."Appointment_end_time" IS NOT NULL
    AND dh."First_time_fix" IS NOT NULL;
"""

print("\n" + "="*70)
print("HISTORICAL DISPATCH GRADES")
print("="*70)
print("\nLoading historical dispatch data...")
df = pd.read_sql_query(query, loader.connection)
loader.disconnect()

print(f"Loaded {len(df)} historical dispatches")

# Calculate overrun
df['appointment_start_time'] = pd.to_datetime(df['appointment_start_time'])
df['appointment_end_time'] = pd.to_datetime(df['appointment_end_time'])
df['scheduled_time'] = (df['appointment_end_time'] - df['appointment_start_time']).dt.total_seconds() / 60
df['overrun'] = df['actual_duration'] - df['scheduled_time']

# Calculate grades
print("\nCalculating Dispatch Grades...")
grades = []
for _, row in df.iterrows():
    grade = calculate_dispatch_grade(
        distance=row['distance'],
        overrun=row['overrun'],
        productive_dispatch=row['productive_dispatch'],
        first_time_fix=row['first_time_fix'],
        use_probabilities=False
    )
    grades.append(grade)

df['dispatch_grade'] = grades

# Statistics
print("\n" + "="*70)
print("GRADE STATISTICS")
print("="*70)
print(f"\nAverage Grade:  {df['dispatch_grade'].mean():.2f}/100")
print(f"Median Grade:   {df['dispatch_grade'].median():.2f}/100")
print(f"Min Grade:      {df['dispatch_grade'].min():.2f}/100")
print(f"Max Grade:      {df['dispatch_grade'].max():.2f}/100")
print(f"Std Dev:        {df['dispatch_grade'].std():.2f}")

# Grade distribution
print(f"\n### GRADE DISTRIBUTION ###")
print(f"90-100 (A):  {(df['dispatch_grade'] >= 90).sum()} ({(df['dispatch_grade'] >= 90).sum()/len(df)*100:.1f}%)")
print(f"80-89 (B):   {((df['dispatch_grade'] >= 80) & (df['dispatch_grade'] < 90)).sum()} ({((df['dispatch_grade'] >= 80) & (df['dispatch_grade'] < 90)).sum()/len(df)*100:.1f}%)")
print(f"70-79 (C):   {((df['dispatch_grade'] >= 70) & (df['dispatch_grade'] < 80)).sum()} ({((df['dispatch_grade'] >= 70) & (df['dispatch_grade'] < 80)).sum()/len(df)*100:.1f}%)")
print(f"60-69 (D):   {((df['dispatch_grade'] >= 60) & (df['dispatch_grade'] < 70)).sum()} ({((df['dispatch_grade'] >= 60) & (df['dispatch_grade'] < 70)).sum()/len(df)*100:.1f}%)")
print(f"0-59 (F):    {(df['dispatch_grade'] < 60).sum()} ({(df['dispatch_grade'] < 60).sum()/len(df)*100:.1f}%)")

# Component breakdown
print(f"\n### AVERAGE COMPONENT SCORES ###")

# Calculate average component scores
distance_scores = []
duration_scores = []
productive_scores = []
ftf_scores = []

for _, row in df.iterrows():
    # Distance
    distance = row['distance']
    if distance >= 250:
        distance_score = 0
    else:
        k = 0.02
        distance_score = 30 * np.exp(-k * distance)
        distance_score = max(0, min(30, distance_score))
    distance_scores.append(distance_score)
    
    # Duration
    overrun = row['overrun']
    if overrun <= 0:
        bonus = min(6, abs(overrun) / 30 * 6)
        duration_score = 30 + bonus
    else:
        penalty_rate = 30 / 90
        duration_score = max(0, 30 - (overrun * penalty_rate))
    duration_scores.append(duration_score)
    
    # Productive
    productive_scores.append(row['productive_dispatch'] * 25)
    
    # FTF
    ftf_scores.append(row['first_time_fix'] * 15)

print(f"Distance Score:           {np.mean(distance_scores):.2f}/30 pts")
print(f"Duration Score:           {np.mean(duration_scores):.2f}/30 pts")
print(f"Productive Dispatch:      {np.mean(productive_scores):.2f}/25 pts")
print(f"First Time Fix:           {np.mean(ftf_scores):.2f}/15 pts")

print("\n" + "="*70)
print(f"\nHistorical Dispatch Grade: {df['dispatch_grade'].mean():.2f}/100")
print("="*70 + "\n")

