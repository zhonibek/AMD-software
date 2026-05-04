import asyncio
import json
import random
import pickle
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import psutil
import threading
import subprocess
import time

app = FastAPI()

# Initialize psutil
psutil.cpu_percent()

# Background thread for REAL system metrics
real_cpu_usage = 0.0
real_gpu_usage = 0.0

def update_system_metrics():
    global real_cpu_usage, real_gpu_usage
    while True:
        try:
            # CPU polling (blocks for 1 second, giving highly accurate average like Task Manager)
            real_cpu_usage = psutil.cpu_percent(interval=1.0)
            
            # GPU polling (matches Task Manager by taking the max utilization across all GPU engines)
            cmd = ['powershell', '-Command', "(((Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples | Measure-Object -Property CookedValue -Maximum).Maximum)"]
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            val_str = output.strip().replace(',', '.')
            if val_str:
                real_gpu_usage = float(val_str)
        except Exception:
            pass

threading.Thread(target=update_system_metrics, daemon=True).start()


# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
    
    real_ram = psutil.virtual_memory().percent

    if sim_state.is_fixing:
        # Simulate fix working by dropping CPU load artificially for demo
        cpu = real_cpu_usage * 0.5
        gpu = random.uniform(85, 95)
        vram = real_ram * 0.8
        frametime = random.uniform(16.0, 16.8)
        
        # Turn off fixing after a while to allow natural behavior again
        if sim_state.tick % 100 == 0:
             sim_state.is_fixing = False
    elif sim_state.is_spiking:
        # Severe stutter / Instability override for demo
        cpu = 95.0 + random.uniform(0, 5)
        gpu = random.uniform(40, 60) # GPU is starved
        vram = 90 + random.uniform(0, 9) # Thrashing
        frametime = random.uniform(30.0, 120.0) # Massive spikes
    else:
        # Use REAL SYSTEM METRICS
        cpu = real_cpu_usage
        # Use actual GPU usage polled by the background thread (fallback if 0)
        gpu = real_gpu_usage if real_gpu_usage > 0 else (real_cpu_usage * 1.5 + random.uniform(2, 8))
        gpu = min(max(gpu, 1.0), 99.0)
        vram = real_ram # Use actual System RAM percentage
        frametime = random.uniform(16.2, 17.5)

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
        "cpu": float(round(cpu, 1)),
        "gpu": float(round(gpu, 1)),
        "vram": float(round(vram, 1)),
        "frametime": float(round(frametime, 2)),
        "stutter_probability": float(round(prob, 3)),
        "alert": bool(prob > 0.7),
        "xai_cause": str(cause),
        "xai_explanation": str(explanation)
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
