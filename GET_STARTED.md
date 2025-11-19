# 🚀 Get Started in 3 Minutes

The fastest way to start predicting dispatch success!

## ⚡ Super Quick Start

```bash
# 1. Install (30 seconds)
pip install -r requirements.txt

# 2. Configure (30 seconds)
cp env.example .env
# Edit .env with your database credentials

# 3. Test (30 seconds)
python test_connection.py

# 4. Train (90 seconds)
python train_model.py

# 5. Predict! (10 seconds)
python predict.py --distance 25 --skill-match 1
```

Done! 🎉

## 📊 What You Just Built

A machine learning system that predicts dispatch success based on:
- **Distance**: How far the technician needs to travel
- **Skill Match**: Whether the technician has the required skills

## 🎯 Quick Examples

### Command Line
```bash
# High probability scenario
python predict.py --distance 10 --skill-match 1

# Low probability scenario
python predict.py --distance 80 --skill-match 0
```

### Python Code
```python
from predict import DispatchPredictor

predictor = DispatchPredictor()
result = predictor.predict_single(distance=25, skill_match=1)
print(f"Success rate: {result['success_probability']:.1%}")
```

### REST API
```bash
# Start server
python api.py

# Make prediction
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"distance": 25, "skill_match": 1}'
```

## 📈 Understanding Results

The system returns predictions like:

```
Success Probability: 85.3%
Prediction: SUCCESS
Recommendation: PROCEED - High probability of success
```

**Decision Rules**:
- ≥80% = PROCEED (High confidence)
- 60-80% = PROCEED WITH CAUTION
- 40-60% = REVIEW
- <40% = DO NOT PROCEED

## 🔧 Troubleshooting

**Can't connect to database?**
```bash
python test_connection.py
```
This will tell you exactly what's wrong.

**Model not found?**
```bash
python train_model.py
```
Train the model first!

**Something else?**
Check `SETUP_INSTRUCTIONS.md` for detailed help.

## 📚 Next Steps

1. **Learn More**: Read `README.md`
2. **See Examples**: Run `python example_usage.py`
3. **Explore Data**: Open `explore_data.ipynb`
4. **All Commands**: Check `COMMANDS.md`

## 🎓 Key Files

| File | What It Does |
|------|--------------|
| `train_model.py` | Trains the ML model |
| `predict.py` | Makes predictions |
| `api.py` | Starts REST API |
| `test_connection.py` | Tests database |
| `example_usage.py` | Shows how to use |

## 💡 Pro Tips

1. **Retrain regularly** with fresh data:
   ```bash
   python train_model.py
   ```

2. **Compare models** to find the best:
   ```bash
   python train_model.py --compare
   ```

3. **Use batch predictions** for efficiency:
   ```python
   predictor.predict_batch(dispatches_df)
   ```

4. **Monitor API** health:
   ```bash
   curl http://localhost:8000/health
   ```

## 🎯 Real-World Usage

**Before Assignment**: Check success probability
```python
if predictor.predict_single(distance, skill_match)['success_probability'] > 0.7:
    assign_dispatch()
else:
    find_better_technician()
```

**Batch Processing**: Score all options
```python
results = predictor.predict_batch(all_available_technicians)
best = results.loc[results['success_probability'].idxmax()]
assign_to(best['technician_id'])
```

## 📞 Getting Help

1. Run diagnostics: `python run_all_tests.py`
2. Check docs: `README.md`, `QUICKSTART.md`
3. See examples: `example_usage.py`

## ✅ Success!

You now have a production-ready dispatch success predictor! 

Start making smarter dispatch decisions based on data! 📊✨

---

**Made with ❤️ for the F-AI-ber Force Hackathon**

