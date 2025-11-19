# Dispatch Success Predictor

A machine learning system for predicting dispatch success based on distance and technician skill matching using historical data from PostgreSQL.

## 🎯 Overview

This project predicts whether a dispatch will be successful based on:
- **Distance**: The travel distance for the dispatch
- **Skill Match**: Whether the technician's skills match the required skills for the job

## 📊 Features

- **Data Pipeline**: Automated data extraction from PostgreSQL database
- **Feature Engineering**: Creates relevant features including skill matching indicators
- **Multiple ML Models**: Supports Random Forest, Gradient Boosting, and Logistic Regression
- **Model Evaluation**: Comprehensive metrics including accuracy, precision, recall, F1, and ROC AUC
- **REST API**: FastAPI-based API for real-time predictions
- **Batch Predictions**: Support for predicting multiple dispatches at once

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
cd F-AI-ber-Force-1

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your PostgreSQL credentials:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=team_faiber_force
DB_USER=your_username
DB_PASSWORD=your_password
```

### 3. Train the Model

```bash
# Basic training
python train_model.py

# Compare multiple models
python train_model.py --compare

# Train specific model type
python train_model.py --model-type gradient_boosting
```

### 4. Make Predictions

#### Command Line

```bash
# Predict a single dispatch
python predict.py --distance 25.5 --skill-match 1
```

#### Python API

```python
from predict import DispatchPredictor

# Load predictor
predictor = DispatchPredictor()

# Single prediction
result = predictor.predict_single(distance=25.5, skill_match=1)
print(f"Success Probability: {result['success_probability']:.2%}")

# Get recommendation
recommendation = predictor.get_recommendation(distance=25.5, skill_match=1)
print(recommendation)
```

### 5. Run REST API

```bash
# Start the API server
python api.py

# Or use uvicorn directly
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

API will be available at `http://localhost:8000`

## 📡 API Usage

### Single Prediction

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"distance": 25.5, "skill_match": 1}'
```

### Batch Predictions

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

### API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📁 Project Structure

```
F-AI-ber-Force-1/
├── config.py              # Configuration settings
├── data_loader.py         # Database connection and data extraction
├── preprocessor.py        # Data preprocessing and feature engineering
├── model.py               # ML model training and evaluation
├── train_model.py         # Main training script
├── predict.py             # Prediction script
├── api.py                 # FastAPI REST API
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── models/               # Saved models and metrics (created during training)
│   ├── dispatch_success_model.pkl
│   ├── scaler.pkl
│   └── model_metrics.json
└── README.md             # This file
```

## 🔍 Database Schema

### Tables Used

#### dispatch_history_10k
- `id`: Dispatch ID
- `distance`: Travel distance
- `required_skill`: Skill required for the job
- `assigned_technician_id`: ID of assigned technician
- `success`: Whether dispatch was successful (target variable)
- `dispatch_time`: When dispatch was created
- `completion_time`: When dispatch was completed

#### technicians_10k
- `technician_id`: Technician ID
- `technician_skill`: Technician's skill
- `skill_level`: Skill level

## 🤖 Model Performance

The model is evaluated on multiple metrics:

- **Accuracy**: Overall correctness of predictions
- **Precision**: Proportion of positive predictions that were correct
- **Recall**: Proportion of actual positives that were identified
- **F1 Score**: Harmonic mean of precision and recall
- **ROC AUC**: Area under the ROC curve

Example performance (Random Forest):
```
Accuracy:  ~85-90%
Precision: ~80-85%
Recall:    ~85-90%
F1 Score:  ~82-87%
ROC AUC:   ~88-92%
```

## 🎨 Feature Engineering

The system creates the following features:

1. **distance**: Raw distance value (scaled)
2. **skill_match**: Binary indicator (1 if skills match, 0 otherwise)
3. **distance_category**: Categorical distance bins (very_short to very_long)
4. **distance_skill_interaction**: Interaction term between distance and skill mismatch

## 🛠️ Advanced Usage

### Custom Model Training

```python
from data_loader import load_data
from preprocessor import DataPreprocessor
from model import DispatchSuccessPredictor

# Load and prepare data
df = load_data()
preprocessor = DataPreprocessor()
X, y = preprocessor.prepare_features(df)
X_train, X_test, y_train, y_test = preprocessor.split_data(X, y)

# Train custom model
predictor = DispatchSuccessPredictor(model_type='gradient_boosting')
predictor.train(X_train, y_train)
metrics = predictor.evaluate(X_test, y_test)
predictor.save('my_custom_model.pkl')
```

### Batch Predictions from CSV

```python
import pandas as pd
from predict import DispatchPredictor

# Load your dispatch data
dispatches = pd.read_csv('dispatches_to_predict.csv')

# Make predictions
predictor = DispatchPredictor()
results = predictor.predict_batch(dispatches)

# Save results
results.to_csv('predictions.csv', index=False)
```

## 📈 Model Comparison

To compare different models:

```bash
python train_model.py --compare
```

This will train and evaluate:
- Random Forest Classifier
- Gradient Boosting Classifier
- Logistic Regression

Results are saved to `models/model_comparison.csv`

## 🐛 Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running
- Verify credentials in `.env` file
- Check if tables exist: `dispatch_history_10k`, `technicians_10k`

### Model Not Found Error

- Run `python train_model.py` first to train and save the model
- Check that `models/` directory contains the model files

### Import Errors

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Use a virtual environment to avoid conflicts

## 📝 License

Git Repo for the F-AI-ber Force Hackathon team

## 🤝 Contributing

This project was created for the F-AI-ber Force Hackathon.

## 📞 Support

For questions or issues, please open an issue in the repository.

---

**Built with ❤️ for the F-AI-ber Force Hackathon**
