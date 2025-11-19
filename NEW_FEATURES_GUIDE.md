# New Features Usage Guide

## 🎯 What's New

Your dispatch predictor now predicts **TWO things**:
1. **Success Probability** - Will the dispatch succeed?
2. **Estimated Duration** - How long will it actually take?

And uses **MORE INPUTS** for better accuracy:
- Ticket Type
- Order Type  
- Priority
- Required Skill
- Technician's Skill
- Distance (calculated from coordinates)
- Expected Duration

---

## 🚀 Quick Start

### 1. Train the New Models

```bash
python train_model.py
```

This will:
- ✓ Load data with new fields from database
- ✓ Calculate distances from lat/lon coordinates  
- ✓ Train success prediction model (classifier)
- ✓ Train duration estimation model (regressor)
- ✓ Save 3 files: success model, duration model, preprocessor

### 2. Make a Prediction

```bash
python predict.py \
    --ticket-type "Installation" \
    --order-type "Standard" \
    --priority "High" \
    --required-skill "Fiber" \
    --technician-skill "Fiber" \
    --distance 25.5 \
    --expected-duration 60
```

**Output:**
```
Dispatch Recommendation
======================================================================
Ticket Type: Installation
Order Type: Standard
Priority: High
Required Skill: Fiber
Technician Skill: Fiber
Distance: 25.5 km
Skill Match: Yes

Success Prediction: SUCCESS ✓
Success Probability: 87.3%
Confidence: High

Duration Estimates:
  Expected: 60 minutes
  Estimated: 68 minutes
  Difference: +8 minutes
✓ Duration likely 8 minutes shorter than expected

Recommendation: PROCEED - High probability of success
======================================================================
```

---

## 💻 Python API Usage

### Basic Example

```python
from predict import DispatchPredictor

# Initialize
predictor = DispatchPredictor()

# Make prediction
result = predictor.predict_single(
    ticket_type="Installation",
    order_type="Standard",
    priority="High",
    required_skill="Fiber",
    technician_skill="Fiber",
    distance=25.5,
    expected_duration=60
)

# Access results
print(f"Success Probability: {result['success_probability']:.1%}")
print(f"Estimated Duration: {result['estimated_duration']:.0f} minutes")
print(f"vs Expected: {result['expected_duration']:.0f} minutes")
print(f"Difference: {result['duration_difference']:+.0f} minutes")
```

### Batch Predictions

```python
import pandas as pd
from predict import DispatchPredictor

# Create dispatch data
dispatches = pd.DataFrame({
    'ticket_type': ['Installation', 'Repair', 'Maintenance'],
    'order_type': ['Standard', 'Emergency', 'Standard'],
    'priority': ['High', 'Critical', 'Medium'],
    'required_skill': ['Fiber', 'Copper', 'Fiber'],
    'technician_skill': ['Fiber', 'Fiber', 'Copper'],
    'distance': [25.5, 45.2, 12.8],
    'expected_duration': [60, 90, 45]
})

# Predict
predictor = DispatchPredictor()
results = predictor.predict_batch(dispatches)

# View results
print(results[['success_probability', 'estimated_duration', 'duration_difference']])
```

---

## 🌐 REST API Usage

### Start API Server

```bash
python api.py
```

API available at: `http://localhost:8000`

### Single Prediction

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_type": "Installation",
    "order_type": "Standard",
    "priority": "High",
    "required_skill": "Fiber",
    "technician_skill": "Fiber",
    "distance": 25.5,
    "expected_duration": 60
  }'
```

**Response:**
```json
{
  "success_prediction": true,
  "success_probability": 0.873,
  "failure_probability": 0.127,
  "estimated_duration": 68.2,
  "expected_duration": 60.0,
  "duration_difference": 8.2,
  "recommendation": "PROCEED - High probability of success (Warning: 8 min longer)",
  "inputs": {
    "ticket_type": "Installation",
    "order_type": "Standard",
    "priority": "High",
    "required_skill": "Fiber",
    "technician_skill": "Fiber",
    "distance": 25.5,
    "skill_match": true
  }
}
```

### Batch Prediction

```bash
curl -X POST "http://localhost:8000/predict/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "dispatches": [
      {
        "ticket_type": "Installation",
        "order_type": "Standard",
        "priority": "High",
        "required_skill": "Fiber",
        "technician_skill": "Fiber",
        "distance": 25.5,
        "expected_duration": 60
      },
      {
        "ticket_type": "Repair",
        "order_type": "Emergency",
        "priority": "Critical",
        "required_skill": "Copper",
        "technician_skill": "Fiber",
        "distance": 45.2,
        "expected_duration": 90
      }
    ]
  }'
```

### Interactive API Documentation

Visit: `http://localhost:8000/docs`

---

## 🎨 Understanding the Outputs

### Success Prediction

```python
{
    'success_prediction': True,      # Binary: will it succeed?
    'success_probability': 0.873,    # Confidence: 87.3%
    'failure_probability': 0.127     # Opposite: 12.7%
}
```

**Interpretation:**
- `>80%` = High confidence, proceed
- `60-80%` = Moderate confidence, caution
- `40-60%` = Low confidence, review
- `<40%` = Very low, do not proceed

### Duration Estimation

```python
{
    'expected_duration': 60.0,       # What we think it will take
    'estimated_duration': 68.2,      # What model predicts
    'duration_difference': +8.2      # Difference (+ means longer)
}
```

**Interpretation:**
- **Positive difference** = Will likely take longer than expected
- **Negative difference** = Will likely be faster than expected
- **>30% difference** = Triggers warning in recommendation

### Recommendations

```
PROCEED - High probability of success
PROCEED WITH CAUTION - Moderate probability
REVIEW - Low probability, consider reassignment
DO NOT PROCEED - Very low probability
```

Recommendations may include duration warnings:
```
PROCEED - High probability (Warning: 15 min longer than expected)
```

---

## 📊 Real-World Use Cases

### Use Case 1: Dispatch Assignment

```python
from predict import DispatchPredictor

predictor = DispatchPredictor()

def should_assign(ticket_type, order_type, priority, required_skill,
                 technician_skill, distance, expected_duration):
    result = predictor.predict_single(
        ticket_type, order_type, priority,
        required_skill, technician_skill,
        distance, expected_duration
    )
    
    # Decision logic
    if result['success_probability'] < 0.5:
        return False, "Low success probability"
    
    if result['duration_difference'] > expected_duration * 0.5:
        return False, "Duration significantly longer than expected"
    
    return True, "Good to go"

# Use it
can_assign, reason = should_assign(
    "Installation", "Standard", "High",
    "Fiber", "Fiber", 25.5, 60
)
print(f"Assign: {can_assign} - {reason}")
```

### Use Case 2: Resource Planning

```python
import pandas as pd
from predict import DispatchPredictor

# Load pending dispatches
dispatches = pd.DataFrame({
    'dispatch_id': [1, 2, 3, 4, 5],
    'ticket_type': ['Installation', 'Repair', 'Maintenance', 'Installation', 'Repair'],
    'order_type': ['Standard', 'Emergency', 'Standard', 'Standard', 'Standard'],
    'priority': ['High', 'Critical', 'Medium', 'High', 'Low'],
    'required_skill': ['Fiber', 'Copper', 'Fiber', 'Fiber', 'Copper'],
    'technician_skill': ['Fiber', 'Fiber', 'Copper', 'Fiber', 'Copper'],
    'distance': [25, 45, 12, 30, 18],
    'expected_duration': [60, 90, 45, 60, 75]
})

# Predict
predictor = DispatchPredictor()
results = predictor.predict_batch(dispatches)

# Calculate total estimated time
total_estimated = results['estimated_duration'].sum()
total_expected = results['expected_duration'].sum()

print(f"Expected total time: {total_expected:.0f} minutes")
print(f"Estimated total time: {total_estimated:.0f} minutes")
print(f"Difference: {total_estimated - total_expected:+.0f} minutes")

# Find risky dispatches
risky = results[results['success_probability'] < 0.6]
print(f"\nRisky dispatches: {len(risky)}")
print(risky[['dispatch_id', 'success_probability', 'estimated_duration']])
```

### Use Case 3: Technician Selection

```python
from predict import DispatchPredictor
import pandas as pd

predictor = DispatchPredictor()

# Job requirements
job = {
    'ticket_type': 'Installation',
    'order_type': 'Standard',
    'priority': 'High',
    'required_skill': 'Fiber',
    'expected_duration': 60
}

# Available technicians
technicians = pd.DataFrame({
    'tech_id': [101, 102, 103, 104],
    'tech_name': ['Alice', 'Bob', 'Charlie', 'Diana'],
    'skill': ['Fiber', 'Copper', 'Fiber', 'Fiber'],
    'distance_from_customer': [15.2, 25.5, 8.3, 42.1]
})

# Evaluate each technician
technicians['ticket_type'] = job['ticket_type']
technicians['order_type'] = job['order_type']
technicians['priority'] = job['priority']
technicians['required_skill'] = job['required_skill']
technicians['expected_duration'] = job['expected_duration']
technicians = technicians.rename(columns={
    'skill': 'technician_skill',
    'distance_from_customer': 'distance'
})

results = predictor.predict_batch(technicians)

# Find best technician
best_idx = results['success_probability'].idxmax()
best_tech = results.loc[best_idx]

print(f"Best Technician: {best_tech['tech_name']}")
print(f"  Success Probability: {best_tech['success_probability']:.1%}")
print(f"  Estimated Duration: {best_tech['estimated_duration']:.0f} min")
print(f"  Distance: {best_tech['distance']:.1f} km")
```

---

## 🔍 Feature Importance

After training, you can see which features matter most:

**For Success Prediction:**
1. skill_match (~40%)
2. priority (~20%)
3. distance (~15%)
4. ticket_type (~10%)
5. Others (~15%)

**For Duration Estimation:**
1. expected_duration (~35%)
2. distance (~25%)
3. ticket_type (~15%)
4. priority (~10%)
5. Others (~15%)

---

## ⚠️ Important Notes

### Distance Calculation

Distance is now **automatically calculated** from coordinates using the Haversine formula:
- Input: customer lat/lon and technician lat/lon
- Output: Distance in kilometers
- No need to pre-calculate or store distance

### Skill Matching

Skill match is **automatically calculated**:
- Compares `required_skill` with `technician_skill`
- Exact match = 1, no match = 0
- You don't need to provide this; it's computed automatically

### Duration Warnings

The system flags dispatches where estimated duration exceeds expected by >30%:
```
Warning: 15 min longer than expected
```

This helps identify:
- Underestimated tasks
- Complex assignments
- Resource planning issues

---

## 📞 Getting Help

**Test your setup:**
```bash
python test_connection.py  # Verify database connection
```

**Retrain models:**
```bash
python train_model.py      # Train with latest data
```

**See all options:**
```bash
python predict.py --help   # Command-line help
```

**API docs:**
Visit `http://localhost:8000/docs` after starting API

---

## 🎯 Key Improvements Over Previous Version

| Aspect | Before | After |
|--------|--------|-------|
| **Inputs** | 2 features | 8 features |
| **Outputs** | Success only | Success + Duration |
| **Accuracy** | Good | Better (more context) |
| **Use Cases** | Assignment decisions | Assignment + Planning + Selection |
| **Insights** | Will it succeed? | Will it succeed? How long? |

---

**Ready to use the enhanced predictor!** 🚀

