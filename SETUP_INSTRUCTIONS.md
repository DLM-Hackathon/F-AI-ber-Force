# Setup Instructions - Dispatch Success Predictor

Complete setup guide for the Dispatch Success Predictor system.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database with access to `team_faiber_force` database
- Tables: `dispatch_history_10k` and `technicians_10k`
- pip (Python package manager)

## Step-by-Step Setup

### Step 1: Verify Python Installation

```bash
python --version
```

Should show Python 3.8 or higher.

### Step 2: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

This will install:
- pandas, numpy (data processing)
- scikit-learn (machine learning)
- psycopg2-binary (PostgreSQL connection)
- python-dotenv (environment variables)
- fastapi, uvicorn (API - optional)
- matplotlib, seaborn (visualization - optional)

### Step 3: Configure Database Connection

1. **Copy the example environment file:**

```bash
cp env.example .env
```

2. **Edit `.env` file with your database credentials:**

On Windows:
```bash
notepad .env
```

On Mac/Linux:
```bash
nano .env
```

Update the values:
```
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=team_faiber_force
DB_USER=your_username
DB_PASSWORD=your_password
```

3. **Save and close the file**

### Step 4: Test Database Connection

```bash
python test_connection.py
```

**Expected output:**
```
======================================================================
DATABASE CONNECTION TEST
======================================================================

[1/4] Testing database connection...
   ✓ Connection successful

[2/4] Checking if required tables exist...
   ✓ dispatch_history_10k table found
   ✓ technicians_10k table found

[3/4] Checking sample data...
   ✓ dispatch_history_10k has 3 sample records
   ✓ technicians_10k has 3 sample records

[4/4] Testing data join query...
   ✓ Successfully fetched XXXX joined records

======================================================================
✓ ALL TESTS PASSED - Database is ready!
======================================================================
```

**If you see errors:**

- **Connection refused**: Check if PostgreSQL is running
- **Authentication failed**: Verify username/password in `.env`
- **Table does not exist**: Verify table names and database

### Step 5: Train the Model

```bash
python train_model.py
```

**Expected output:**
```
======================================================================
DISPATCH SUCCESS PREDICTION - MODEL TRAINING
======================================================================

[1/5] Loading data from database...
✓ Loaded XXXX records

[2/5] Preprocessing data...
=== Data Exploration ===
...

[3/5] Skipping model comparison...

[4/5] Training final random_forest model...
=== Training random_forest model ===
...

[5/5] Evaluating and saving model...
=== Evaluating random_forest model ===

Accuracy:  0.XXXX
Precision: 0.XXXX
Recall:    0.XXXX
F1 Score:  0.XXXX
ROC AUC:   0.XXXX

======================================================================
TRAINING COMPLETED SUCCESSFULLY
======================================================================
```

This creates a `models/` directory with:
- `dispatch_success_model.pkl` (trained model)
- `scaler.pkl` (feature scaler)
- `model_metrics.json` (performance metrics)

**Training Options:**

```bash
# Compare all models (takes longer but shows which is best)
python train_model.py --compare

# Train a specific model type
python train_model.py --model-type gradient_boosting
python train_model.py --model-type logistic_regression
```

### Step 6: Test Predictions

```bash
# Test a prediction
python predict.py --distance 25.5 --skill-match 1
```

**Expected output:**
```
✓ Model loaded from models/dispatch_success_model.pkl
✓ Scaler loaded from models/scaler.pkl

Dispatch Recommendation
==================================================
Distance: 25.5 units
Skill Match: Yes

Prediction: SUCCESS
Success Probability: XX.X%
Confidence: High

Recommendation: PROCEED - High probability of success
==================================================
```

### Step 7: Run Example Scripts

```bash
# Run all usage examples
python example_usage.py
```

This demonstrates:
- Single predictions
- Batch predictions
- Detailed recommendations
- Decision support scenarios

### Step 8 (Optional): Start API Server

```bash
# Start the FastAPI server
python api.py
```

**Expected output:**
```
✓ Model loaded successfully
INFO:     Started server process [XXXX]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test the API:**

```bash
# Health check
curl http://localhost:8000/health

# Make a prediction
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"distance": 25.5, "skill_match": 1}'
```

**View API documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Step 9 (Optional): Explore Data

```bash
# Start Jupyter
jupyter notebook
```

Then open `explore_data.ipynb` for interactive data exploration.

## Verification Checklist

- [ ] Python 3.8+ installed
- [ ] All packages installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with correct credentials
- [ ] Database connection test passed
- [ ] Model trained successfully
- [ ] Predictions working
- [ ] (Optional) API server running
- [ ] (Optional) Jupyter notebook accessible

## Project Structure

After setup, your directory should look like this:

```
F-AI-ber-Force-1/
├── .env                      # Your database credentials (not in git)
├── .gitignore               # Git ignore rules
├── env.example              # Environment template
├── requirements.txt         # Python dependencies
│
├── config.py                # Configuration
├── data_loader.py          # Database access
├── preprocessor.py         # Data preprocessing
├── model.py                # ML models
│
├── train_model.py          # Training script
├── predict.py              # Prediction script
├── api.py                  # REST API
│
├── test_connection.py      # DB test utility
├── example_usage.py        # Usage examples
├── explore_data.ipynb      # Jupyter notebook
│
├── models/                 # Created after training
│   ├── dispatch_success_model.pkl
│   ├── scaler.pkl
│   └── model_metrics.json
│
├── README.md               # Main documentation
├── QUICKSTART.md          # Quick start guide
├── SETUP_INSTRUCTIONS.md  # This file
└── PROJECT_SUMMARY.md     # Technical overview
```

## Common Issues and Solutions

### Issue 1: ModuleNotFoundError

**Error**: `ModuleNotFoundError: No module named 'pandas'`

**Solution**:
```bash
pip install -r requirements.txt
```

### Issue 2: Connection Error

**Error**: `Error connecting to database: could not connect to server`

**Solutions**:
1. Check PostgreSQL is running
2. Verify host and port in `.env`
3. Check firewall settings
4. Test connection manually:
   ```bash
   psql -h localhost -U postgres -d team_faiber_force
   ```

### Issue 3: Authentication Failed

**Error**: `Error connecting to database: password authentication failed`

**Solutions**:
1. Verify username and password in `.env`
2. Check user has access to database:
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE team_faiber_force TO your_user;
   ```

### Issue 4: Table Not Found

**Error**: `relation "dispatch_history_10k" does not exist`

**Solutions**:
1. Verify you're connected to correct database
2. Check table names (case sensitive)
3. List tables:
   ```sql
   \dt
   ```

### Issue 5: Model Not Found

**Error**: `FileNotFoundError: Model file not found`

**Solution**:
```bash
# Train the model first
python train_model.py
```

### Issue 6: Permission Denied (Windows)

**Error**: Creating `.env` file or `models/` directory fails

**Solution**:
- Run Command Prompt as Administrator
- Or create directory manually
- Check folder permissions

### Issue 7: Port Already in Use (API)

**Error**: `OSError: [Errno 48] Address already in use`

**Solution**:
```bash
# Use different port
uvicorn api:app --port 8001

# Or kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Mac/Linux:
lsof -ti:8000 | xargs kill -9
```

## Performance Expectations

- **Data Loading**: 1-5 seconds (depends on network and data size)
- **Model Training**: 1-3 minutes for 10K records
- **Single Prediction**: < 10 milliseconds
- **Batch Prediction (100 records)**: < 50 milliseconds
- **API Response Time**: < 100 milliseconds

## Next Steps After Setup

1. **Understand the Data**:
   - Review `explore_data.ipynb`
   - Check data distributions
   - Analyze feature importance

2. **Integrate into Your System**:
   - Use Python API for in-application predictions
   - Use REST API for microservices
   - Use CLI for batch processing

3. **Monitor Performance**:
   - Track prediction accuracy
   - Monitor API latency
   - Log failed predictions

4. **Iterate and Improve**:
   - Collect feedback on predictions
   - Retrain model with new data
   - Add new features as needed

## Getting Help

1. **Check documentation**:
   - README.md (overview)
   - QUICKSTART.md (quick guide)
   - PROJECT_SUMMARY.md (technical details)

2. **Run diagnostics**:
   ```bash
   python test_connection.py
   ```

3. **Check logs**:
   - Model training logs
   - API server logs
   - Database query logs

4. **Review examples**:
   ```bash
   python example_usage.py
   ```

## Security Reminders

⚠️ **IMPORTANT**: 
- Never commit `.env` file to git
- Keep database credentials secure
- Add authentication to API in production
- Use HTTPS for API in production
- Regularly update dependencies

## Maintenance

### Regular Tasks

1. **Update Dependencies** (monthly):
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Retrain Model** (weekly/monthly based on data):
   ```bash
   python train_model.py
   ```

3. **Backup Models**:
   ```bash
   cp -r models/ models_backup_$(date +%Y%m%d)/
   ```

4. **Monitor Database**:
   - Check table sizes
   - Review slow queries
   - Archive old data

## Support

For issues or questions:
- Check this setup guide
- Review error messages carefully
- Run test_connection.py for diagnostics
- Review example_usage.py for patterns

---

**Setup Complete!** 🎉

You're now ready to predict dispatch success with machine learning!

