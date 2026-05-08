# 🧠 PCMANai (AMD Stability Brain)

An autonomous, closed-loop **AI Hardware Assistant** built for the AMD AI Developer Competition. PCMANai observes real-time system telemetry, reasons using a custom local Deep Learning Neural Network, and acts using expert-level Windows/AMD optimizations to eliminate input lag and frametime stutters.

## 🏆 Hackathon Categories Targeted

This project was specifically engineered to dominate multiple competition tracks by combining local Reinforcement Learning with Hugging Face LLMs:

- ✅ **Agent Builder Track - The INTERNET OF AGENTS:** PCMANai is a true autonomous agent. It observes state, selects from an action space of hardware tools, executes them, measures the reward, and updates its Neural weights in a continuous loop.
- ✅ **AI Agents & Agentic Workflows:** The system requires zero human input after initialization. It uses an Epsilon-Greedy RL loop to explore and exploit performance tweaks.
- ✅ **Hugging Face & Qwen:** PCMANai utilizes a local **Qwen 2.5** language model via the **Hugging Face `transformers` API** to dynamically generate Explainable AI (XAI) justifications for its actions in real-time.
- ✅ **Assistant:** PCMANai acts as an invisible background assistant that autonomously tunes your PC for maximum gaming and productivity performance.

## 🛠️ Technology Stack & AI Architecture

1. **Deep Learning Brain (`scikit-learn`):** A custom Multi-Layer Perceptron (MLP) Neural Network acting as a Contextual Bandit. It uses a `StandardScaler` to normalize real-time CPU, GPU, RAM, Disk, Ping, Frametime, and Input Lag telemetry.
2. **Experience Replay Memory:** The Agent maintains a memory buffer of past states and rewards to train on mini-batches, rapidly accelerating its learning curve.
3. **Local Hugging Face LLM (Qwen):** A local implementation of `Qwen2.5-0.5B-Instruct` is used for the Agent's reasoning loop. Instead of black-box fixes, the Agent explains exactly why it applied a tweak in plain English.
4. **AMD-Specific Optimizations:** The Agent can autonomously scan the registry to disable Ultra-Low Power State (ULPS) on AMD Radeon GPUs to stabilize competitive frametimes.

## 🚀 How to Run

1. Clone the repository.
2. Run `pip install -r backend/requirements.txt`.
3. Double click `launch.bat` to boot the backend Uvicorn server and open the Dashboard.
4. Click **"Run Diagnostic"** to watch the Neural Network calculate Q-Values and train itself in real-time!

## 🧩 The Action Space (Tools)

The AI Agent has access to the following real-world system tools:
- `disable_amd_ulps`: Fixes AMD GPU sleep-state stutters.
- `unpark_cpu_cores`: Eliminates CPU wake-up latency.
- `disable_windows_game_bar`: Stops GameDVR micro-stutters.
- `optimize_mouse_keyboard_buffer`: Decreases input lag buffer sizes in the registry.
- `prioritize_foreground_app`: Automatically sets the active game to HIGH priority.
- `clear_standby_memory`: Flushes RAM caches to prevent disk thrashing.

---
*Built autonomously using DeepMind Antigravity for the Lablab.ai AMD Developer Competition.*
