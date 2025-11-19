# Quick Start Guide

Get up and running with the Dispatch Success Predictor in 5 minutes!

## Step 1: Install Dependencies (1 min)

```bash
pip install -r requirements.txt
```

## Step 2: Configure Database (1 min)

1. Copy the environment file:
```bash
cp env.example .env
```

2. Edit `.env` with your PostgreSQL credentials:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=team_faiber_force
DB_USER=your_username
DB_PASSWORD=your_password
```

## Step 3: Test Connection (30 sec)

```bash
python test_connection.py
```

This will verify:
- ✓ Database connection works
- ✓ Required tables exist
- ✓ Data can be queried
- ✓ Join query works correctly

## Step 4: Train Model (2-3 min)

```bash
python train_model.py
```

This will:
- Load data from PostgreSQL
- Preprocess and engineer features
- Train Random Forest model
- Evaluate performance
- Save model to `models/` directory

## Step 5: Make Predictions (30 sec)

### Command Line
```bash
python predict.py --distance 25.5 --skill-match 1
```

### Python Script
```python
from predict import DispatchPredictor

predictor = DispatchPredictor()
result = predictor.predict_single(distance=25.5, skill_match=1)
print(f"Success Probability: {result['success_probability']:.2%}")
```

### Run Examples
```bash
python example_usage.py
```

## Optional: Start API Server

```bash
python api.py
```

Then test it:
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"distance": 25.5, "skill_match": 1}'
```

## Common Issues

### ImportError: No module named 'psycopg2'
```bash
pip install psycopg2-binary
```

### Connection refused
- Check if PostgreSQL is running
- Verify credentials in `.env`
- Check firewall settings

### Table does not exist
- Verify table names: `dispatch_history_10k`, `technicians_10k`
- Check you're connected to the right database

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore [example_usage.py](example_usage.py) for usage patterns
- Try different models with `--compare` flag
- Integrate predictions into your dispatch system

## Need Help?

Run the test connection script for diagnostics:
```bash
python test_connection.py
```

This will show exactly what's working and what's not.

