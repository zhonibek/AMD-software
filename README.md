# 🧠 PCMANai: The Local Evolving Hardware Brain

**PCMANai** (Personal Computing Management Artificial Intelligence) is a state-of-the-art, autonomous PC optimization agent. Unlike traditional "game boosters" that rely on static rules, PCMANai utilizes a local **Contextual Bandit Neural Network** to learn, evolve, and optimize your specific hardware environment in real-time.

![PCMANai Dashboard Prototype](https://img.shields.io/badge/Status-Prototype-red?style=for-the-badge)
![AI-Powered](https://img.shields.io/badge/AI-Reinforcement_Learning-blue?style=for-the-badge)
![Local-Execution](https://img.shields.io/badge/Environment-Local_Only-green?style=for-the-badge)

---

## 🚀 Key Features

### 1. Self-Evolving Local AI
PCMANai has completely moved away from external LLMs like ChatGPT. It runs a local **SGDRegressor** (Scikit-Learn) that observes your hardware metrics and "discovers" the best optimizations through Reinforcement Learning. It saves its experience permanently to a `pcman_brain.pkl` file, getting smarter every time you use your PC.

### 2. High-Fidelity Telemetry
Monitor your system with surgical precision:
- **Input Lag Analyzer:** Uses a global OS-level hook to measure the micro-latency between mouse clicks and processing frames.
- **Frametime Tracking:** Real-time Chart.js visualization of frame delivery consistency.
- **Full Hardware Stack:** Live tracking of CPU, GPU, VRAM, RAM, Disk Active Time, and Network Ping.

### 3. Anomaly Simulation Suite
Test the AI's "intelligence" by unleashing intentional hardware stressors from the dashboard:
- **CPU Spikes:** Mathematical stress loops.
- **Input Lag Spikes:** High-priority scheduler starvation.
- **Memory Leaks:** Forced RAM thrashing and pagefile swapping.
- **Disk Thrashing:** Simulated background service saturation.
- **Bad Core Affinity:** Forcing heavy tasks onto Core 0 (the OS critical core).
- **Ping Spikes:** Simulated network congestion.

### 4. Advanced Optimization Toolkit
PCMANai can deploy a variety of system-level "synapses" to fix lag:
- **Ultimate Performance Toggling:** Switches Windows power plans dynamically.
- **Process Affinity Masking:** Moves background noise away from critical CPU cores.
- **Standby List Flushing:** Instantly purges cached RAM to stop micro-stutters.
- **Priority Escalation:** Boosts foreground application priority to `High`.
- **Registry Tweaking:** Real-time modification of `TcpNoDelay` and `Win32PrioritySeparation`.

---

## 🛠️ Technical Stack

- **Backend:** Python 3.10+, FastAPI (Asynchronous API), WebSockets (Real-time data streaming).
- **AI/ML:** Scikit-Learn (Incremental Learning), NumPy.
- **System Control:** Psutil, Pynput, Winreg, Ctypes.
- **Frontend:** Vanilla HTML5, CSS3 (Glassmorphism design), Javascript (ES6), Chart.js.

---

## ⚡ Quick Start

### 1. Requirements
Ensure you have Python installed and an elevated (Administrator) terminal:
```bash
pip install -r backend/requirements.txt
```

### 2. Launch
Simply run the included batch file to start the backend and frontend:
```bash
./launch.bat
```
*Note: Administrator privileges are required for Registry and Process Priority optimizations to work.*

### 3. Training the Brain
Open the dashboard at `http://localhost:8000`. Choose an anomaly from the dropdown and click **"Simulate Anomaly"**. Watch the **Synapse Log** in the bottom right as PCMANai tries different tools, measures the reward, and learns how to fix your PC.

---

## 🛡️ Safety & Privacy
PCMANai is **100% Local**. No telemetry or hardware data is ever sent to the cloud. The AI's "thoughts" stay on your machine.

---
*Developed for the AMD Challenge. Empowering hardware with autonomous intelligence.*
