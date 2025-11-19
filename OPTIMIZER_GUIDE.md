# Dispatch Optimization Engine - User Guide

## Overview

The **Dispatch Optimization Engine** optimizes technician assignments for all current dispatches based on:
- **50% Success Probability** (from hybrid ML + business rules model)
- **35% Workload Balance** (ideal ≤80%, avoid >100%)
- **10% Travel Distance** (minimize km to customer)
- **5% Estimated Overrun** (minimize duration overruns)

---

## Quick Start

```bash
# Run the optimizer
python optimize_dispatches.py

# Expected runtime: ~10 minutes for 432 dispatches
```

---

## What It Does

### Phase 1: Greedy Assignment (~2-3 minutes)
1. Sorts dispatches by priority: **Critical → High → Normal → Low**
2. Within priority, sorts by appointment start time (earlier first)
3. For each dispatch:
   - Evaluates ALL available technicians
   - Checks time conflicts, workload capacity, shift hours
   - Calculates weighted score
   - Assigns to best scoring technician
   - Updates technician's schedule and workload

### Phase 2: Post-Optimization (~7-8 minutes, 3 passes)
1. **Pairwise Swaps**: Try swapping technicians between dispatch pairs
2. **Single Reassignments**: Reassign problem dispatches to better technicians
3. **Priority Focus**: Extra effort on Critical/High priority improvements
4. Stops early if no improvements found

---

## Constraints & Rules

### 🚨 HARD CONSTRAINTS (Never Bypassed)

#### Calendar Availability
- **Technicians can ONLY be assigned on days when `Available = 1` in their calendar**
- **This constraint is NEVER relaxed, even for Critical priority or in fallback strategies**
- If a technician has `Available = 0` or no calendar entry for a date, they are automatically excluded
- Purpose: Respects technician time off, training days, and other unavailability

### ✅ Time Constraints (Soft - Can Be Relaxed)
- **Preferred**: Non-overlapping appointments with 30-min buffer
- **Exception for Critical**: Allow overlap if success ≥ 20% better than next option
- **Exception for High**: Allow overlap if success ≥ 25% better than next option
- **Max Concurrent**: 2 appointments at same time
- **Shift Hours**: Total scheduled time ≤ available work hours

### ✅ Workload Limits (Soft - Can Be Relaxed)
| Priority | Rule |
|----------|------|
| **Low** | Hard block at 100% capacity |
| **Normal** | Hard block at 100% capacity |
| **High** | Allow up to 120% with heavy penalty |
| **Critical** | Allow up to 120% with heavy penalty |

### ✅ Shift Time Matching (Soft - Can Be Relaxed)
- Appointment times must fall within `Start_time` to `End_time` from calendar
- **Exception**: Critical tickets can extend past `End_time` if success ≥50% better

### ✅ Fallback Strategy (Progressive Relaxation)
If no valid assignment found, progressively relax soft constraints:
1. Relax 30-min buffer → 15 min
2. Relax 15-min buffer → 0 min  
3. Allow 3 concurrent appointments
4. Allow shift overtime (up to 1 hour)
5. Allow workload up to 110%
6. Assign to best success probability (relax all soft constraints)

**Important:** Calendar availability (`Available = 1`) is a HARD CONSTRAINT and is NEVER relaxed.

---

## Outputs

### 1. `optimized_assignments.csv`
Main output with recommended assignments:
```
dispatch_id, ticket_type, priority, required_skill,
assigned_technician_id,      ← Current assignment
optimized_technician_id,     ← Recommended assignment
success_probability,         ← Predicted success (0-1)
estimated_duration,          ← Predicted duration (min)
distance,                    ← Travel distance (km)
skill_match,                 ← 1=match, 0=no match
score,                       ← Optimization score
has_warnings,                ← Any constraint violations?
warning_count                ← Number of warnings
```

### 2. `optimization_warnings.csv`
Detailed warnings for problematic assignments:
```
dispatch_id, technician_id, warning
200000001, T900005, "Workload would be 105% (>100%)"
200000042, T900112, "FALLBACK: Allowing overtime"
```

### 3. `optimization_report.txt`
Comparison metrics before/after:
- Average success probability
- Skill match rate
- Average travel distance
- Workload distribution
  - % technicians below 40% capacity
  - % technicians above 100% capacity
- Optimization statistics

---

## Example Output

```
======================================================================
DISPATCH OPTIMIZATION ENGINE
======================================================================

Objective Weights:
  - Success Probability: 50%
  - Workload Balance:    35%
  - Travel Distance:     10%
  - Estimated Overrun:    5%

Loading ML models...
[OK] Models loaded

[1/6] Loading data from database...
  [OK] Loaded 432 dispatches
  [OK] Loaded 140 technicians
  [OK] Loaded 1250 calendar entries

[2/6] Running Phase 1: Greedy Assignment...
  Progress: 50/432 dispatches assigned...
  Progress: 100/432 dispatches assigned...
  Progress: 150/432 dispatches assigned...
  ...
  [OK] Phase 1 complete in 2.3 seconds
  Assigned: 432/432
  Forced assignments: 12
  Overlap exceptions: 3

[3/6] Running Phase 2: Post-Optimization (3 passes)...

  Pass 1/3:
    Attempting pairwise swaps...
    - Swaps improved: 0
    Attempting single reassignments...
    - Reassignments improved: 8
    Pass 1 complete in 2.8s: 8 improvements

  Pass 2/3:
    Attempting pairwise swaps...
    - Swaps improved: 0
    Attempting single reassignments...
    - Reassignments improved: 3
    Pass 2 complete in 2.7s: 3 improvements

  Pass 3/3:
    Attempting pairwise swaps...
    - Swaps improved: 0
    Attempting single reassignments...
    - Reassignments improved: 1
    Pass 3 complete in 2.6s: 1 improvements

  [OK] Post-optimization complete: 12 total improvements

[4/6] Generating outputs...
  [OK] Saved optimized_assignments.csv
  [OK] Saved optimization_warnings.csv (12 warnings)

[5/6] Generating comparison report...

======================================================================
OPTIMIZATION COMPARISON REPORT
======================================================================

### OVERALL METRICS ###

Average Success Probability:
  Optimized: 85.3%

Skill Match Rate:
  Optimized: 78.5%

Average Travel Distance:
  Optimized: 42.1 km

### WORKLOAD DISTRIBUTION ###

Average Workload: 65.2%
Technicians below 40% capacity: 22.1%
Technicians above 100% capacity: 2.1%

### OPTIMIZATION STATISTICS ###

Total dispatches: 432
Forced assignments: 12
Overlap exceptions: 3
Workload violations: 2

======================================================================

  [OK] Saved optimization_report.txt

[6/6] Summary...

======================================================================
OPTIMIZATION COMPLETE
======================================================================

Total runtime: 9.8 seconds

Outputs generated:
  - optimized_assignments.csv (432 assignments)
  - optimization_warnings.csv (12 warnings)
  - optimization_report.txt

======================================================================
```

---

## Reviewing Results

### 1. Check Overall Improvements
```bash
# Review the comparison report
cat optimization_report.txt

# Look for:
# - Success probability improvement
# - Workload balance improvement
# - Warnings/violations
```

### 2. Review Warnings
```bash
# Check which dispatches had issues
cat optimization_warnings.csv | head -20

# Common warnings:
# - "Workload would be X% (>100%)" 
# - "FALLBACK: Allowing overtime"
# - "FALLBACK: Allowing 3 concurrent"
```

### 3. Compare Before/After
```python
import pandas as pd

results = pd.read_csv('optimized_assignments.csv')

# See which assignments changed
changed = results[results['assigned_technician_id'] != results['optimized_technician_id']]
print(f"Changed assignments: {len(changed)}/{len(results)}")

# See biggest improvements
improved = changed.sort_values('success_probability', ascending=False)
print(improved[['dispatch_id', 'priority', 'success_probability']].head(10))
```

---

## Customization

### Adjust Optimization Weights
Edit `optimize_dispatches.py`:
```python
class DispatchOptimizer:
    def __init__(self, ...):
        # Adjust these weights (must sum to 100)
        self.WEIGHT_SUCCESS = 60.0    # More emphasis on success
        self.WEIGHT_WORKLOAD = 25.0   # Less on workload
        self.WEIGHT_DISTANCE = 10.0
        self.WEIGHT_OVERRUN = 5.0
```

### Change Number of Optimization Passes
```python
# In main():
optimizer.run_post_optimization(dispatches, technicians, calendar, num_passes=5)  # More passes
```

### Adjust Hybrid Model Weight
```python
# Use more business rules, less ML
optimizer = DispatchOptimizer(preprocessor, success_model, duration_model, 
                              rule_weight=0.8)  # 80% rules, 20% ML
```

---

## Troubleshooting

### "Could not assign dispatch X"
- Check if technician calendar has entries for that date
- Verify appointment times are reasonable
- Check if all technicians are at 100%+ capacity

### Too many warnings
- Consider relaxing constraints
- Add more technicians
- Adjust shift hours in calendar

### Runtime > 10 minutes
- Reduce number of optimization passes
- Simplify post-optimization (edit try_reassignments sample size)

---

## Next Steps

1. **Review Results**: Check optimized_assignments.csv and warnings
2. **Validate Sample**: Manually check 10-20 assignments make sense
3. **Test in Staging**: Apply to test environment first
4. **Implement DB Updates**: Once validated, add database update functionality
5. **Monitor Performance**: Track actual success rates vs predicted

---

## Files

- `optimize_dispatches.py`: Main optimization engine
- `business_rules.py`: Rule-based success probability calculations
- `config.py`: Configuration and feature definitions
- `data_loader.py`: Database connection and data loading
- Models: `dispatch_success_model.pkl`, `dispatch_duration_model.pkl`, `preprocessor.pkl`

---

## Support

For issues or questions:
1. Check `optimization_warnings.csv` for constraint violations
2. Review `optimization_report.txt` for overall metrics
3. Verify database connectivity and data quality
4. Ensure ML models are trained and up-to-date

