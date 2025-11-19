# Predicting Current Dispatches - Usage Guide

## 📋 Overview

You now have two powerful scripts to work with your `current_dispatches_csv` table:

1. **`predict_current_dispatches.py`** - Predict outcomes for assigned dispatches
2. **`suggest_technicians.py`** - Find best technicians for any dispatch

---

## 🎯 Script 1: Predict Assigned Dispatches

### What It Does
- Loads dispatches from `current_dispatches_csv` that have assigned technicians
- Predicts success probability and estimated duration
- Provides recommendations and risk analysis
- Saves results to CSV

### Usage

```bash
python predict_current_dispatches.py
```

### Output

**Console Output:**
```
======================================================================
CURRENT DISPATCHES PREDICTION
======================================================================

[1/3] Loading current dispatches from database...
✓ Loaded 150 dispatches

[2/3] Making predictions...
✓ Features prepared: (150, 8)
✓ Predictions complete

[3/3] Saving results...
✓ Results saved to current_dispatches_predictions.csv

PREDICTION SUMMARY
Total Dispatches: 150
Predicted Successful: 127 (84.7%)
Predicted Failures: 23 (15.3%)

Average Success Probability: 82.3%
Average Expected Duration: 65.2 minutes
Average Estimated Duration: 71.8 minutes

TOP 10 RISKIEST DISPATCHES
...
```

**CSV Output:** `current_dispatches_predictions.csv`

Columns include:
- All original dispatch fields
- `success_prediction` - Will it succeed? (True/False)
- `success_probability` - Confidence (0-100%)
- `estimated_duration` - Predicted actual time
- `duration_difference` - How much longer/shorter than expected
- `recommendation` - Action to take (PROCEED, REVIEW, etc.)
- `confidence` - High, Medium, Low, Very Low

---

## 🎯 Script 2: Suggest Best Technicians

### What It Does
- Evaluates ALL technicians for each dispatch
- Calculates success probability for each possible assignment
- Ranks technicians by overall score (success, distance, skill match, capacity)
- Suggests top N best options per dispatch

### Usage

**For All Dispatches:**
```bash
python suggest_technicians.py
```

**For Only Unassigned Dispatches:**
```bash
python suggest_technicians.py --unassigned-only
```

**Get Top 10 Suggestions Per Dispatch:**
```bash
python suggest_technicians.py --top-n 10
```

### Output

**Console Output:**
```
======================================================================
TECHNICIAN SUGGESTION ENGINE
======================================================================

Loading models...
✓ Models loaded

Loading dispatches from database...
✓ Loaded 45 dispatches
Loading technicians...
✓ Loaded 500 technicians

Analyzing 45 dispatches with 500 technicians...
Evaluating 22,500 possible assignments...

Processing dispatch DISP001 (1/45)...
  Best: Alice Johnson (Success: 89.2%, Distance: 12.3km, Skill Match: Yes)

TOP 5 TECHNICIAN RECOMMENDATIONS PER DISPATCH

Dispatch ID: DISP001
  Ticket Type: Installation
  Required Skill: Fiber
  Priority: High

  Top 5 Technicians:
    1. Alice Johnson        Success: 89.2% | Distance: 12.3km | Skill: Fiber          | Match: ✓ | Score: 145.2
    2. Bob Smith            Success: 85.1% | Distance: 15.8km | Skill: Fiber          | Match: ✓ | Score: 138.7
    3. Charlie Davis        Success: 81.3% | Distance: 10.5km | Skill: Copper         | Match: ✗ | Score: 122.4
    ...
```

**CSV Output:** `technician_suggestions.csv`

Columns include:
- `dispatch_id` - Dispatch identifier
- `rank` - Ranking (1 = best option)
- `technician_id` - Technician ID
- `technician_name` - Technician name
- `success_probability` - Predicted success rate
- `estimated_duration` - How long it will take
- `distance` - Distance to customer
- `skill_match` - Does skill match? (1/0)
- `score` - Overall score
- `current_assignments` - Current workload
- `workload_capacity` - Maximum capacity

---

## 📊 Use Cases

### Use Case 1: Daily Operations Review

Check today's assigned dispatches:

```bash
python predict_current_dispatches.py
```

**Look for:**
- Dispatches with low success probability (<60%)
- Dispatches with significant duration overrun
- High-priority dispatches with medium/low confidence

**Action:**
- Reassign risky dispatches
- Allocate extra time for overrun predictions
- Provide additional support for low-confidence assignments

---

### Use Case 2: Optimize Unassigned Dispatches

Find best technicians for unassigned work:

```bash
python suggest_technicians.py --unassigned-only --top-n 3
```

**Review the suggestions:**
- Top ranked = best overall choice
- Consider skill match vs. distance tradeoffs
- Check technician workload capacity

**Action:**
- Assign top-ranked technician if available
- If unavailable, go to #2 or #3
- Document assignment decision

---

### Use Case 3: Re-evaluate Current Assignments

Maybe current assignments aren't optimal:

```bash
# Step 1: Get predictions for current assignments
python predict_current_dispatches.py

# Step 2: See if better technicians exist
python suggest_technicians.py --top-n 5
```

**Compare:**
- Current assignment success probability
- vs. Best available technician success probability

**Action:**
- If significant improvement possible (>10% higher success), consider reassignment
- Balance with other factors (technician preference, location, etc.)

---

### Use Case 4: Capacity Planning

Understand overall dispatch health:

```bash
python predict_current_dispatches.py
```

**Analyze summary:**
- What % of dispatches are predicted to succeed?
- How much longer will things take than expected?
- Which ticket types have lowest success rates?

**Action:**
- Request more technicians with specific skills
- Adjust expected durations for future planning
- Identify training needs

---

## 🔧 Advanced Usage

### Filter Results in Excel/Python

After running predictions, you can filter the CSV:

**Example: High-priority risky dispatches**
```python
import pandas as pd

results = pd.read_csv('current_dispatches_predictions.csv')

risky_high_priority = results[
    (results['priority'] == 'High') & 
    (results['success_probability'] < 0.6)
]

print(f"Found {len(risky_high_priority)} high-priority risky dispatches")
risky_high_priority.to_csv('action_required.csv', index=False)
```

### Integrate with Other Systems

Load predictions and push to your dispatch system:

```python
import pandas as pd

# Load predictions
predictions = pd.read_csv('current_dispatches_predictions.csv')

# For each risky dispatch
for _, dispatch in predictions[predictions['confidence'] == 'Low'].iterrows():
    dispatch_id = dispatch['dispatch_id']
    probability = dispatch['success_probability']
    
    # Your code to update dispatch system
    # update_dispatch_risk(dispatch_id, probability)
```

---

## 📝 Notes

### Required Database Columns

**current_dispatches_csv table must have:**
- `Dispatch_id`
- `Ticket_type`
- `Order_type`
- `Priority`
- `Required_skill`
- `Assigned_technician_id` (can be NULL for suggestions)
- `Customer_latitude`
- `Customer_longitude`
- `Duration_min`
- `Status`
- `Appointment_start_time`

### Performance

- **Predict assigned**: Fast (~1 sec per 100 dispatches)
- **Suggest technicians**: Slower (~1 min per 10 dispatches if 500 technicians)
  - For large datasets, consider filtering technicians first (by location, skill, availability)

### Scoring Logic in Suggestions

The score combines multiple factors:
```python
score = (
    success_probability * 100 +      # Most important (0-100 points)
    (1 - distance/max_distance) * 20 +  # Closer is better (0-20 points)
    skill_match * 30 +                # Skill match bonus (0-30 points)
    available_capacity_ratio * 10    # Workload consideration (0-10 points)
)
```

You can adjust these weights in `suggest_technicians.py` if needed!

---

## 🚀 Quick Commands Reference

| Task | Command |
|------|---------|
| Predict assigned dispatches | `python predict_current_dispatches.py` |
| Suggest technicians (all) | `python suggest_technicians.py` |
| Suggest for unassigned only | `python suggest_technicians.py --unassigned-only` |
| Top 10 suggestions | `python suggest_technicians.py --top-n 10` |
| Save to different file | Edit script or redirect: `> my_results.csv` |

---

**Ready to optimize your dispatches!** 🎯

