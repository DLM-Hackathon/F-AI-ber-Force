# Command Reference

Quick reference for all available commands and scripts.

## Setup Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Create Environment File
```bash
# Copy example
cp env.example .env

# Edit with your credentials
# Windows:
notepad .env

# Mac/Linux:
nano .env
```

## Testing Commands

### Test Database Connection
```bash
python test_connection.py
```

### Run All Tests
```bash
python run_all_tests.py
```

## Training Commands

### Basic Training
```bash
# Train with default settings (Random Forest)
python train_model.py
```

### Compare Models
```bash
# Train and compare all models
python train_model.py --compare
```

### Train Specific Model
```bash
# Random Forest (default, recommended)
python train_model.py --model-type random_forest

# Gradient Boosting
python train_model.py --model-type gradient_boosting

# Logistic Regression
python train_model.py --model-type logistic_regression
```

## Prediction Commands

### Command Line Predictions

#### Single Prediction
```bash
# Predict with distance and skill match
python predict.py --distance 25.5 --skill-match 1

# Predict without skill match
python predict.py --distance 50.0 --skill-match 0
```

#### Examples
```bash
# Short distance with skill match (high success probability)
python predict.py --distance 10 --skill-match 1

# Long distance without skill match (low success probability)
python predict.py --distance 80 --skill-match 0

# Medium distance with skill match (moderate success probability)
python predict.py --distance 30 --skill-match 1
```

### Python API Usage

#### Single Prediction
```python
from predict import DispatchPredictor

# Initialize predictor
predictor = DispatchPredictor()

# Make prediction
result = predictor.predict_single(distance=25.5, skill_match=1)

print(f"Success Probability: {result['success_probability']:.2%}")
print(f"Prediction: {result['success_prediction']}")
```

#### Batch Predictions
```python
import pandas as pd
from predict import DispatchPredictor

# Create dispatch data
dispatches = pd.DataFrame({
    'distance': [15.0, 45.0, 8.0, 75.0, 25.0],
    'skill_match': [1, 1, 0, 0, 1]
})

# Make predictions
predictor = DispatchPredictor()
results = predictor.predict_batch(dispatches)

print(results[['distance', 'skill_match', 'success_probability']])
```

#### Get Recommendations
```python
from predict import DispatchPredictor

predictor = DispatchPredictor()
recommendation = predictor.get_recommendation(distance=25.5, skill_match=1)
print(recommendation)
```

### Example Scripts
```bash
# Run all usage examples
python example_usage.py
```

## API Commands

### Start API Server
```bash
# Start with default settings
python api.py

# Or use uvicorn directly
uvicorn api:app --reload

# Custom host and port
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Test API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Single Prediction
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"distance": 25.5, "skill_match": 1}'
```

#### Batch Predictions
```bash
curl -X POST "http://localhost:8000/predict/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "dispatches": [
      {"distance": 15.0, "skill_match": 1},
      {"distance": 50.0, "skill_match": 0},
      {"distance": 10.0, "skill_match": 1}
    ]
  }'
```

#### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### API with Python Requests
```python
import requests

# Single prediction
response = requests.post(
    "http://localhost:8000/predict",
    json={"distance": 25.5, "skill_match": 1}
)
result = response.json()
print(result)

# Batch predictions
response = requests.post(
    "http://localhost:8000/predict/batch",
    json={
        "dispatches": [
            {"distance": 15.0, "skill_match": 1},
            {"distance": 50.0, "skill_match": 0}
        ]
    }
)
results = response.json()
print(results)
```

## Data Exploration Commands

### Start Jupyter Notebook
```bash
jupyter notebook
# Then open explore_data.ipynb
```

### Direct Data Loading
```python
from data_loader import load_data

# Load all data
df = load_data()
print(f"Loaded {len(df)} records")
print(df.head())
```

### Data Preprocessing
```python
from data_loader import load_data
from preprocessor import DataPreprocessor

# Load and preprocess
df = load_data()
preprocessor = DataPreprocessor()

# Explore
preprocessor.explore_data(df)

# Prepare features
X, y = preprocessor.prepare_features(df)

# Split data
X_train, X_test, y_train, y_test = preprocessor.split_data(X, y)
```

## Database Commands

### Using Python
```python
from data_loader import DataLoader

loader = DataLoader()
loader.connect()

# Get table info
info = loader.get_table_info('dispatch_history_10k')
print(info)

# Get sample data
sample = loader.get_sample_data('dispatch_history_10k', limit=5)
print(sample)

# Fetch dispatch data
data = loader.fetch_dispatch_data()
print(f"Fetched {len(data)} records")

loader.disconnect()
```

### Direct SQL (psql)
```bash
# Connect to database
psql -h localhost -U postgres -d team_faiber_force

# List tables
\dt

# View table structure
\d dispatch_history_10k
\d technicians_10k

# Sample queries
SELECT COUNT(*) FROM dispatch_history_10k;
SELECT COUNT(*) FROM technicians_10k;
SELECT success, COUNT(*) FROM dispatch_history_10k GROUP BY success;
```

## Model Management

### Save Model
```python
from model import DispatchSuccessPredictor

# After training
predictor = DispatchSuccessPredictor()
predictor.train(X_train, y_train)
predictor.save('models/my_model.pkl')
```

### Load Model
```python
from model import DispatchSuccessPredictor

# Load existing model
predictor = DispatchSuccessPredictor()
predictor.load('models/dispatch_success_model.pkl')

# Make predictions
predictions = predictor.predict(X_test)
```

### Compare Models
```python
from data_loader import load_data
from preprocessor import DataPreprocessor
from model import compare_models

# Load and prepare data
df = load_data()
preprocessor = DataPreprocessor()
X, y = preprocessor.prepare_features(df)
X_train, X_test, y_train, y_test = preprocessor.split_data(X, y)

# Compare all models
comparison = compare_models(X_train, y_train, X_test, y_test)
print(comparison)
```

## Maintenance Commands

### Backup Models
```bash
# Windows
xcopy /E /I models models_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%

# Mac/Linux
cp -r models/ models_backup_$(date +%Y%m%d)/
```

### Update Dependencies
```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade scikit-learn
```

### Clean Up
```bash
# Remove Python cache
# Windows
del /S /Q __pycache__
del /S /Q *.pyc

# Mac/Linux
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Git Commands

### Initial Setup
```bash
# Initialize (if not already done)
git init

# Add files
git add .

# Commit
git commit -m "Initial commit: Dispatch Success Predictor"

# Add remote
git remote add origin <your-repo-url>

# Push
git push -u origin main
```

### Regular Updates
```bash
# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Updated model training"

# Push
git push
```

## Environment Management

### Create Virtual Environment
```bash
# Create
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Deactivate Environment
```bash
deactivate
```

## Troubleshooting Commands

### Check Python Version
```bash
python --version
```

### Check Installed Packages
```bash
pip list
pip show pandas
pip show scikit-learn
```

### Test Imports
```python
python -c "import pandas; print(pandas.__version__)"
python -c "import sklearn; print(sklearn.__version__)"
python -c "import psycopg2; print(psycopg2.__version__)"
```

### Check Database Connection
```python
python -c "from data_loader import DataLoader; loader = DataLoader(); loader.connect(); print('Connected!'); loader.disconnect()"
```

### Verify Model Exists
```bash
# Windows
dir models\

# Mac/Linux
ls -l models/
```

## Quick Reference Card

| Task | Command |
|------|---------|
| Test DB | `python test_connection.py` |
| Train Model | `python train_model.py` |
| Predict | `python predict.py --distance 25 --skill-match 1` |
| Start API | `python api.py` |
| Run Examples | `python example_usage.py` |
| Run Tests | `python run_all_tests.py` |
| Start Jupyter | `jupyter notebook` |
| API Docs | http://localhost:8000/docs |

## Common Workflows

### Workflow 1: First Time Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure database
cp env.example .env
# Edit .env with credentials

# 3. Test connection
python test_connection.py

# 4. Train model
python train_model.py

# 5. Test predictions
python predict.py --distance 25 --skill-match 1
```

### Workflow 2: Daily Usage
```bash
# Make predictions
python predict.py --distance 30 --skill-match 1

# Or use API
python api.py
# Then use HTTP requests
```

### Workflow 3: Model Retraining
```bash
# 1. Backup existing model
cp -r models/ models_backup/

# 2. Train new model
python train_model.py --compare

# 3. Test new model
python predict.py --distance 25 --skill-match 1

# 4. If satisfied, keep new model. If not, restore backup.
```

### Workflow 4: Integration
```python
# In your application
from predict import DispatchPredictor

# Initialize once (at startup)
predictor = DispatchPredictor()

# Use for each dispatch decision
def should_accept_dispatch(distance, has_skill_match):
    result = predictor.predict_single(distance, int(has_skill_match))
    return result['success_probability'] >= 0.6  # Your threshold
```

## Help and Documentation

- Full documentation: `README.md`
- Quick start: `QUICKSTART.md`
- Setup guide: `SETUP_INSTRUCTIONS.md`
- Technical details: `PROJECT_SUMMARY.md`
- This reference: `COMMANDS.md`

