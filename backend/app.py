import asyncio
import json
import random
import pickle
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the model (ensure model_trainer.py is run first)
MODEL_PATH = "model_output/rf_model.pkl"
model = None

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
else:
    print("Warning: Model not found. Please run model_trainer.py first. Using a fallback heuristic.")

# Global state for simulation
class SimulationState:
    def __init__(self):
        self.is_fixing = False
        self.is_spiking = False
        self.tick = 0

sim_state = SimulationState()

@app.post("/api/fix")
async def apply_fix():
    """Endpoint triggered by the frontend Resolve button."""
    sim_state.is_fixing = True
    sim_state.is_spiking = False
    return {"status": "success", "message": "Smart Fix Applied. Frame pacing normalized."}

@app.post("/api/trigger_spike")
async def trigger_spike():
    """Endpoint to artificially trigger a stutter for demo purposes."""
    sim_state.is_spiking = True
    sim_state.is_fixing = False
    return {"status": "success", "message": "Spike triggered."}

def generate_telemetry():
    """Simulates realistic telemetry data, reacting to state."""
    sim_state.tick += 1
    
    if sim_state.is_fixing:
        # Ideal smooth performance
        cpu = random.uniform(30, 45)
        gpu = random.uniform(85, 95)
        vram = random.uniform(40, 60)
        frametime = random.uniform(16.0, 16.8)
        
        # Turn off fixing after a while to allow natural behavior again
        if sim_state.tick % 100 == 0:
             sim_state.is_fixing = False
    elif sim_state.is_spiking:
        # Severe stutter / Instability
        cpu = random.uniform(80, 100)
        gpu = random.uniform(40, 60) # GPU is starved
        vram = random.uniform(90, 99) # Thrashing
        frametime = random.uniform(30.0, 120.0) # Massive spikes
    else:
        # Normal fluctuation, occasional minor spike
        cpu = random.uniform(40, 60)
        gpu = random.uniform(90, 99)
        vram = random.uniform(60, 80)
        frametime = random.uniform(16.2, 17.5)
        
        # Randomly trigger a spike sometimes
        if random.random() < 0.005:
            sim_state.is_spiking = True

    # Predict stutter probability
    prob = 0.0
    if model:
        features = np.array([[cpu, gpu, vram, frametime]])
        prob = model.predict_proba(features)[0][1] # Probability of class 1
    else:
        # Fallback heuristic
        prob = (vram / 100) * 0.6 + (cpu / 100) * 0.4

    # Determine XAI Explanation if probability is high
    explanation = ""
    cause = "Unknown"
    if prob > 0.7:
        if vram > 85 and cpu > 80:
            cause = "VRAM_THRASHING"
            explanation = "Heavy background process thrashing VRAM and CPU cache. Game is being starved of resources."
        elif frametime > 50:
            cause = "THERMAL_THROTTLE"
            explanation = "GPU thermal limit reached. Frame pacing engine requires clock stabilization."
        else:
            cause = "SCHEDULING_DELAY"
            explanation = "OS thread scheduler is delaying game render thread. Prioritization recommended."

    return {
        "cpu": round(cpu, 1),
        "gpu": round(gpu, 1),
        "vram": round(vram, 1),
        "frametime": round(frametime, 2),
        "stutter_probability": round(prob, 3),
        "alert": prob > 0.7,
        "xai_cause": cause,
        "xai_explanation": explanation
    }

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = generate_telemetry()
            await websocket.send_json(data)
            await asyncio.sleep(0.05)  # 50ms polling interval
    except WebSocketDisconnect:
        print("Client disconnected")
