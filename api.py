"""
FastAPI REST API for dispatch success and duration prediction
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import pandas as pd
from predict import DispatchPredictor

# Initialize FastAPI app
app = FastAPI(
    title="Dispatch Success & Duration Predictor API",
    description="API for predicting dispatch success probability and estimated duration",
    version="2.0.0"
)

# Initialize predictor
predictor = None


@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    global predictor
    try:
        predictor = DispatchPredictor()
        print("✓ Models loaded successfully")
    except Exception as e:
        print(f"✗ Error loading models: {e}")
        raise


# Request/Response models
class DispatchRequest(BaseModel):
    ticket_type: str = Field(..., description="Type of ticket (e.g., Installation, Repair)")
    order_type: str = Field(..., description="Type of order")
    priority: str = Field(..., description="Priority level (e.g., High, Medium, Low)")
    required_skill: str = Field(..., description="Skill required for the dispatch")
    technician_skill: str = Field(..., description="Technician's skill")
    distance: float = Field(..., description="Distance in km", ge=0)
    expected_duration: float = Field(..., description="Expected duration in minutes", ge=0)


class DispatchResponse(BaseModel):
    success_prediction: bool
    success_probability: float
    failure_probability: float
    estimated_duration: float
    expected_duration: float
    duration_difference: float
    recommendation: str
    inputs: Dict


class BatchDispatchRequest(BaseModel):
    dispatches: List[DispatchRequest]


class BatchDispatchResponse(BaseModel):
    predictions: List[DispatchResponse]


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dispatch Success & Duration Predictor API",
        "version": "2.0.0",
        "endpoints": {
            "/predict": "POST - Predict success and duration for a single dispatch",
            "/predict/batch": "POST - Predict for multiple dispatches",
            "/health": "GET - Health check"
        },
        "features": [
            "Success probability prediction",
            "Duration estimation",
            "Considers: ticket_type, order_type, priority, skills, distance"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if predictor is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    return {
        "status": "healthy",
        "models_loaded": True,
        "version": "2.0.0"
    }


@app.post("/predict", response_model=DispatchResponse)
async def predict_dispatch(request: DispatchRequest):
    """
    Predict success and duration for a single dispatch
    
    Args:
        request: Dispatch request with all required fields
    
    Returns:
        Prediction with success probability, estimated duration, and recommendation
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        result = predictor.predict_single(
            ticket_type=request.ticket_type,
            order_type=request.order_type,
            priority=request.priority,
            required_skill=request.required_skill,
            technician_skill=request.technician_skill,
            distance=request.distance,
            expected_duration=request.expected_duration
        )
        
        # Add recommendation
        prob = result['success_probability']
        duration_diff = result['duration_difference']
        
        if prob >= 0.8:
            recommendation = "PROCEED - High probability of success"
        elif prob >= 0.6:
            recommendation = "PROCEED WITH CAUTION - Moderate probability of success"
        elif prob >= 0.4:
            recommendation = "REVIEW - Low probability of success"
        else:
            recommendation = "DO NOT PROCEED - Very low probability of success"
        
        # Add duration warning to recommendation
        if duration_diff > request.expected_duration * 0.3:
            recommendation += f" (Warning: {duration_diff:.0f} min longer than expected)"
        
        result['recommendation'] = recommendation
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/predict/batch", response_model=BatchDispatchResponse)
async def predict_dispatches_batch(request: BatchDispatchRequest):
    """
    Predict success and duration for multiple dispatches
    
    Args:
        request: Batch request with multiple dispatches
    
    Returns:
        List of predictions with success probabilities, durations, and recommendations
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame([d.dict() for d in request.dispatches])
        
        # Make predictions
        results = predictor.predict_batch(df)
        
        # Add recommendations
        def get_recommendation(row):
            prob = row['success_probability']
            duration_diff = row['duration_difference']
            
            if prob >= 0.8:
                rec = "PROCEED - High probability of success"
            elif prob >= 0.6:
                rec = "PROCEED WITH CAUTION - Moderate probability of success"
            elif prob >= 0.4:
                rec = "REVIEW - Low probability of success"
            else:
                rec = "DO NOT PROCEED - Very low probability of success"
            
            if duration_diff > row['expected_duration'] * 0.3:
                rec += f" (Warning: {duration_diff:.0f} min longer)"
            
            return rec
        
        results['recommendation'] = results.apply(get_recommendation, axis=1)
        
        # Convert to response format
        predictions = []
        for idx, row in results.iterrows():
            predictions.append({
                'success_prediction': bool(row['success_prediction']),
                'success_probability': float(row['success_probability']),
                'failure_probability': float(row['failure_probability']),
                'estimated_duration': float(row['estimated_duration']),
                'expected_duration': float(row['expected_duration']),
                'duration_difference': float(row['duration_difference']),
                'recommendation': row['recommendation'],
                'inputs': {
                    'ticket_type': row['ticket_type'],
                    'order_type': row['order_type'],
                    'priority': row['priority'],
                    'required_skill': row['required_skill'],
                    'technician_skill': row['technician_skill'],
                    'distance': float(row['distance']),
                    'skill_match': bool(row['skill_match'])
                }
            })
        
        return {"predictions": predictions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
