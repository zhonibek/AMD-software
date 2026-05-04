# AMD Stability Brain 🧠

An AI-powered diagnostic and optimization layer designed for AMD hardware. It monitors real-time telemetry (CPU, GPU, RAM, Frametimes), detects anomalies using an Explainable AI (XAI) Random Forest model, and provides root-cause diagnosis for micro-stuttering.

## How to Run the Project

This project consists of two parts: a Python backend and a web frontend.

### 1. Start the Python Backend
Open a terminal (PowerShell or Command Prompt) and run:
```powershell
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

### 2. Start the Web Frontend
Open a **second** terminal and run:
```powershell
cd frontend
python -m http.server 8080
```

### 3. Open the Dashboard
Open your web browser and go to:
[http://127.0.0.1:8080/](http://127.0.0.1:8080/)

---

## Features
- **Real-Time Telemetry:** Hooks directly into Windows Performance Counters and `psutil` to stream real CPU, GPU, and RAM data.
- **Hardware Stress Testing:** The "Simulate Spike" feature dynamically allocates memory and pegs CPU cores using background PowerShell processes to test the system naturally.
- **Explainable AI (XAI):** A Random Forest model actively scores stutter probabilities and translates raw data into human-readable warnings (e.g. "VRAM_THRASHING").
