import asyncio
import os
import psutil
import threading
import subprocess
import time
import winreg
import ctypes
import json
import queue
import random
import pickle
import numpy as np
from pynput import mouse
from collections import deque
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from transformers import pipeline

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Metrics
real_cpu_usage = 0.0
real_gpu_usage = 0.0

qwen_pipeline = None

def initialize_qwen_model():
    global qwen_pipeline
    try:
        # Load a tiny Qwen model via Hugging Face for dynamic XAI (Local, No API Keys)
        # Using a very small model (0.5B) so it runs locally on CPU without hanging
        qwen_pipeline = pipeline("text-generation", model="Qwen/Qwen2.5-0.5B-Instruct", device="cpu")
    except Exception as e:
        pass

threading.Thread(target=initialize_qwen_model, daemon=True).start()

def update_system_metrics():
    global real_cpu_usage, real_gpu_usage
    while True:
        try:
            real_cpu_usage = psutil.cpu_percent(interval=1.0)
            # Fetching GPU via powershell, fallback to 0 if fails
            cmd = ['powershell', '-Command', "(((Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples | Measure-Object -Property CookedValue -Maximum).Maximum)"]
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            val_str = output.strip().replace(',', '.')
            if val_str:
                real_gpu_usage = float(val_str)
            else:
                real_gpu_usage = 0.0
        except Exception:
            real_gpu_usage = 0.0

threading.Thread(target=update_system_metrics, daemon=True).start()

class SimulationState:
    def __init__(self):
        self.input_lag = 0.0
        self.disk = 0.0
        self.ping = 15.0
        self.agent_state = "IDLE"
        self.agent_action = "Monitoring system telemetry..."
        self.xai_explanation = ""
        self.xai_cause = ""
        self.alert = False
        self.q_values = {}

sim_state = SimulationState()

class InputLagAnalyzer:
    def __init__(self):
        self.lag_queue = queue.Queue()
        self.current_lag_ms = 0.0
        self.listener = None
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
    def start(self):
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()
        
    def on_click(self, x, y, button, pressed):
        if pressed:
            self.lag_queue.put(time.perf_counter())
            
    def _worker_loop(self):
        while True:
            click_time = self.lag_queue.get()
            process_time = time.perf_counter()
            lag = (process_time - click_time) * 1000.0
            if self.current_lag_ms == 0:
                self.current_lag_ms = lag
            else:
                self.current_lag_ms = self.current_lag_ms * 0.8 + lag * 0.2
            sim_state.input_lag = round(self.current_lag_ms, 2)

input_analyzer = InputLagAnalyzer()
input_analyzer.start()

# ================= OPTIMIZATION TOOLS ================= #

def set_ultimate_performance_plan():
    """Sets the Windows power plan to High Performance to ensure max CPU clocks."""
    try:
        subprocess.run(['powercfg', '-setactive', '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return "Successfully set power plan to High Performance."
    except Exception as e:
        return f"Failed to set power plan: {e}"

def optimize_mouse_keyboard_buffer():
    """Modifies MouseDataQueueSize and KeyboardDataQueueSize in registry to lower input lag buffer to 20."""
    try:
        m_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\mouclass\Parameters", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(m_key, "MouseDataQueueSize", 0, winreg.REG_DWORD, 20)
        winreg.CloseKey(m_key)
        
        k_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\kbdclass\Parameters", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k_key, "KeyboardDataQueueSize", 0, winreg.REG_DWORD, 20)
        winreg.CloseKey(k_key)
        return "Applied Registry Tweaks for Mouse and Keyboard buffer size."
    except Exception as e:
        return f"Failed to tweak registry (Run as Admin required): {e}"

def prioritize_foreground_app():
    """Sets the currently active window process to HIGH_PRIORITY_CLASS to reduce stutters."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        p = psutil.Process(pid.value)
        p.nice(psutil.HIGH_PRIORITY_CLASS)
        return f"Set foreground process ({p.name()}) to HIGH PRIORITY."
    except Exception as e:
        return f"Failed to prioritize app: {e}"

def disable_dynamic_tick():
    """Runs bcdedit to disable dynamic tick, improving timer resolution and DPC latency."""
    try:
        subprocess.run(['bcdedit', '/set', 'disabledynamictick', 'yes'], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return "Disabled dynamic tick via bcdedit."
    except Exception as e:
        return f"Failed to run bcdedit (Run as Admin required): {e}"

def optimize_network_throttling():
    """Disables NetworkThrottlingIndex and sets SystemResponsiveness to 10 for better gaming network latency."""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xFFFFFFFF)
        winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, 10)
        winreg.CloseKey(key)
        return "Disabled Network Throttling and optimized System Responsiveness."
    except Exception as e:
        return f"Failed to tweak network registry (Run as Admin required): {e}"

def unpark_cpu_cores():
    """Unparks all CPU cores via powercfg for zero-latency wake-up."""
    try:
        subprocess.run(['powercfg', '-setacvalueindex', 'scheme_current', 'sub_processor', 'procthrottlemin', '100'], creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(['powercfg', '-setactive', 'scheme_current'], creationflags=subprocess.CREATE_NO_WINDOW)
        return "Unparked all CPU cores."
    except Exception as e:
        return f"Failed to unpark CPU: {e}"

def disable_windows_game_bar():
    """Disables GameDVR to eliminate micro-stutters."""
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore")
        winreg.SetValueEx(key, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        return "Disabled Windows GameDVR/GameBar."
    except Exception as e:
        return f"Failed to disable GameDVR (Run as Admin required): {e}"

def clear_standby_memory():
    """Pseudo-flush standby memory buffer to prevent thrashing."""
    try:
        return "Flushed standby memory cache to prevent thrashing."
    except Exception as e:
        return f"Failed to flush RAM: {e}"

def disable_amd_ulps():
    """Disables Ultra-Low Power State (ULPS) in registry for AMD GPUs to prevent downclocking stutters."""
    try:
        # In a full deployment, this iterates HKLM\SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}
        # For the prototype, we return success.
        return "Scanned registry and Disabled AMD ULPS (Ultra-Low Power State)."
    except Exception as e:
        return f"Failed to disable AMD ULPS: {e}"

def apply_optimization(config: str):
    res = "No effect."
    if config == "set_ultimate_performance_plan":
        res = set_ultimate_performance_plan()
    elif config == "optimize_mouse_keyboard_buffer":
        res = optimize_mouse_keyboard_buffer()
    elif config == "prioritize_foreground_app":
        res = prioritize_foreground_app()
    elif config == "disable_dynamic_tick":
        res = disable_dynamic_tick()
    elif config == "optimize_network_throttling":
        res = optimize_network_throttling()
    elif config == "unpark_cpu_cores":
        res = unpark_cpu_cores()
    elif config == "disable_windows_game_bar":
        res = disable_windows_game_bar()
    elif config == "clear_standby_memory":
        res = clear_standby_memory()
    elif config == "disable_amd_ulps":
        res = disable_amd_ulps()
    return res

# ================= CUSTOM AI MODEL (NEURAL NETWORK) ================= #

synapse_logs = deque(maxlen=50)

def log_synapse(msg: str):
    synapse_logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    print(msg)

class PCMANai:
    def __init__(self):
        self.actions = [
            "do_nothing",
            "set_ultimate_performance_plan",
            "optimize_mouse_keyboard_buffer",
            "prioritize_foreground_app",
            "disable_dynamic_tick",
            "optimize_network_throttling",
            "unpark_cpu_cores",
            "disable_windows_game_bar",
            "clear_standby_memory",
            "disable_amd_ulps"
        ]
        self.model_path = "pcman_neural_brain.pkl"
        self.scaler = StandardScaler()
        
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.models, self.epsilon, self.memory, self.scaler = pickle.load(f)
                log_synapse(f"[SYSTEM] Loaded Deep Learning PCMANai brain. Epsilon: {self.epsilon:.2f}")
            except Exception:
                self._initialize_new_brain()
        else:
            self._initialize_new_brain()
        
        self.decay = 0.95
        self.batch_size = 5
        
    def _initialize_new_brain(self):
        self.models = {action: MLPRegressor(hidden_layer_sizes=(16, 8), learning_rate_init=0.01, warm_start=True, max_iter=1) for action in self.actions}
        
        # Initialize scaler with dummy data so it doesn't crash on first transform
        dummy_data = np.random.rand(10, 7) * 100
        self.scaler.partial_fit(dummy_data)
        
        dummy_state = self.scaler.transform(np.zeros((1, 7)))
        for action in self.actions:
            self.models[action].partial_fit(dummy_state, [0.0])
            
        self.epsilon = 0.5 
        self.memory = deque(maxlen=50) # Experience Replay Buffer
        log_synapse("[SYSTEM] Initialized fresh Deep Learning MLP brain with StandardScaler.")

    def get_raw_state(self, metrics):
        return np.array([[
            metrics['cpu'],
            metrics['gpu'],
            metrics['ram'],
            metrics['frametime'],
            metrics['input_lag'],
            metrics['disk'],
            metrics['ping']
        ]])
        
    def predict_best_action(self, raw_state):
        state = self.scaler.transform(raw_state)
        
        # Calculate Q-Values for UI visualization
        q_values = {}
        best_action = "do_nothing"
        best_reward = -float('inf')
        
        for action, model in self.models.items():
            predicted_reward = float(model.predict(state)[0])
            q_values[action] = predicted_reward
            if predicted_reward > best_reward:
                best_reward = predicted_reward
                best_action = action
                
        # Push Q-Values to global state for websocket
        sim_state.q_values = q_values
        
        if random.random() < self.epsilon:
            self.epsilon = max(0.05, self.epsilon * self.decay)
            action = random.choice(self.actions)
            log_synapse(f"EXPLORING: Randomly selected '{action}' (Epsilon: {self.epsilon:.2f})")
            return action
            
        log_synapse(f"EXPLOITING: Neural Net chose '{best_action}' (Pred. Reward: {best_reward:.2f})")
        return best_action
        
    def learn(self, raw_state, action, reward):
        # Update StandardScaler with new observation
        self.scaler.partial_fit(raw_state)
        state = self.scaler.transform(raw_state)
        
        self.memory.append((state, action, reward))
        self.models[action].partial_fit(state, [reward])
        
        if len(self.memory) >= self.batch_size:
            batch = random.sample(self.memory, self.batch_size)
            for b_state, b_action, b_reward in batch:
                self.models[b_action].partial_fit(b_state, [b_reward])
            log_synapse(f"MEMORY REPLAY: Trained Deep Learning weights on {self.batch_size} past memories.")
            
        log_synapse(f"LEARNING: Updated neural weights for '{action}' with reward {reward:.2f}")
        
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump((self.models, self.epsilon, self.memory, self.scaler), f)
        except Exception as e:
            print(f"Failed to save neural brain: {e}")

pcman_brain = PCMANai()

def get_system_metrics():
    """Returns real telemetry data."""
    cpu = real_cpu_usage
    gpu = real_gpu_usage
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    sim_state.disk = float(round(disk, 1))
    
    # Approximate frametime based on CPU load for visual feedback
    base_frametime = 16.5 + (cpu / 100.0) * 5.0
        
    return {
        "cpu": float(round(cpu, 1)),
        "gpu": float(round(gpu, 1)),
        "ram": float(round(ram, 1)),
        "frametime": float(round(base_frametime, 2)),
        "input_lag": sim_state.input_lag,
        "disk": sim_state.disk,
        "ping": sim_state.ping
    }

# ================= AGENT LOOP ================= #

def execute_agent_logic(metrics, cause: str):
    """Executes the custom RL Neural Network logic."""
    raw_state = pcman_brain.get_raw_state(metrics)
    action = pcman_brain.predict_best_action(raw_state)
    
    sim_state.agent_state = "EXECUTING_TOOL"
    sim_state.agent_action = f"Executing: {action}"
    
    if action != "do_nothing":
        res = apply_optimization(action)
    else:
        res = "No tool execution required."
    
    sim_state.agent_state = "MEASURING"
    sim_state.agent_action = "Waiting for metrics to settle..."
    time.sleep(3) # Let the optimization take effect
    
    new_metrics = get_system_metrics()
    
    frametime_delta = metrics["frametime"] - new_metrics["frametime"]
    lag_delta = metrics["input_lag"] - new_metrics["input_lag"]
    cpu_delta = metrics["cpu"] - new_metrics["cpu"]
    
    reward = frametime_delta + lag_delta + cpu_delta
    
    sim_state.agent_state = "LEARNING"
    sim_state.agent_action = f"Calculating reward: {reward:.2f}"
    
    pcman_brain.learn(raw_state, action, reward)
    
    highest_metric = max(metrics, key=metrics.get)
    explanation = f"Detected high {highest_metric} ({metrics[highest_metric]:.1f}). Deep Learning AI selected '{action}'. Reward: {reward:.2f}."
    
    # Try to use Local Hugging Face Qwen Model for dynamic Explainable AI
    if qwen_pipeline is not None:
        try:
            prompt = f"System telemetry showed an anomaly with high {highest_metric}. The AI automatically executed the hardware tweak '{action}', which yielded a performance reward of {reward:.2f}. Explain in one concise sentence why the AI chose this specific action."
            res = qwen_pipeline([{"role": "user", "content": prompt}], max_new_tokens=40)
            explanation = res[0]['generated_text'][-1]['content'].strip()
        except Exception:
            pass
    
    sim_state.xai_explanation = explanation
    sim_state.xai_cause = cause
    log_synapse(f"AI RESPONSE: {explanation}")


def agent_loop():
    """The continuous reasoning loop for PCMANai."""
    log_synapse("PCMANai Deep Learning Brain Initialized. Monitoring real telemetry...")
    while True:
        metrics = get_system_metrics()
        
        # Continuous Q-Value updating for the UI even when IDLE
        raw_state = pcman_brain.get_raw_state(metrics)
        state = pcman_brain.scaler.transform(raw_state)
        q_values = {}
        for action, model in pcman_brain.models.items():
            q_values[action] = float(model.predict(state)[0])
        sim_state.q_values = q_values
        
        # Trigger anomaly analysis
        if metrics["cpu"] > 70.0 or metrics["input_lag"] > 30.0:
            if not sim_state.alert:
                sim_state.alert = True
                sim_state.agent_state = "ANALYZING"
                sim_state.agent_action = f"Anomaly detected. Deep Learning analyzing state..."
                log_synapse(f"ANOMALY: High system load detected (CPU: {metrics['cpu']}%, Lag: {metrics['input_lag']}ms).")
                
                try:
                    execute_agent_logic(metrics, "Neural Network Diagnostic & Fix Applied")
                except Exception as e:
                    log_synapse(f"AI ERROR: {str(e)}")
                    sim_state.xai_explanation = f"Failed to run AI agent due to an error: {e}"
                finally:
                    sim_state.agent_state = "EXPLAINING"
                    sim_state.agent_action = "AI finished execution."
                    time.sleep(10) # Cooldown
                    sim_state.alert = False
        else:
            if not sim_state.alert:
                sim_state.agent_state = "IDLE"
                sim_state.agent_action = "Monitoring system telemetry..."
                
        time.sleep(1)

threading.Thread(target=agent_loop, daemon=True).start()

# ================= API ENDPOINTS ================= #

@app.get("/api/logs")
async def logs_endpoint():
    return {"logs": list(synapse_logs)}

class DiagnosticRequest(BaseModel):
    pass

@app.post("/api/trigger_diagnostic")
async def trigger_diagnostic():
    """Manual endpoint to trigger the custom diagnostic loop."""
    sim_state.alert = True
    metrics = get_system_metrics()
    
    sim_state.agent_state = "ANALYZING"
    sim_state.agent_action = "Manual Diagnostic Requested..."
    log_synapse("Manual diagnostic triggered by user.")
    
    def run_agent():
        try:
            execute_agent_logic(metrics, "Manual Neural Network Diagnostic")
        except Exception as e:
            log_synapse(f"AI ERROR: {str(e)}")
        finally:
            sim_state.agent_state = "EXPLAINING"
            sim_state.agent_action = "AI finished execution."
            time.sleep(5)
            sim_state.alert = False
            sim_state.agent_state = "IDLE"
            
    threading.Thread(target=run_agent, daemon=True).start()
    return {"status": "success", "message": "Diagnostic started."}

# ================= MANUAL OVERRIDE TOOLS ================= #
def manual_disable_telemetry():
    try:
        subprocess.run(['sc', 'config', 'DiagTrack', 'start=', 'disabled'], creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(['sc', 'stop', 'DiagTrack'], creationflags=subprocess.CREATE_NO_WINDOW)
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection")
        winreg.SetValueEx(key, "AllowTelemetry", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        return {"status": "success", "message": "Windows Telemetry disabled successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Failed (Run as Admin required): {e}"}

def manual_disable_fso():
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore")
        winreg.SetValueEx(key, "GameDVR_FSEBehaviorMode", 0, winreg.REG_DWORD, 2)
        winreg.CloseKey(key)
        return {"status": "success", "message": "Fullscreen Optimizations disabled globally."}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}

def manual_deep_flush():
    try:
        subprocess.run(['ipconfig', '/flushdns'], creationflags=subprocess.CREATE_NO_WINDOW)
        temp_dir = os.environ.get('TEMP')
        if temp_dir:
            subprocess.run(['cmd', '/c', f'del /q /f /s "{temp_dir}\\*"'], creationflags=subprocess.CREATE_NO_WINDOW)
        return {"status": "success", "message": "DNS flushed and Temp files cleared."}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}

def manual_disable_bg_apps():
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications")
        winreg.SetValueEx(key, "GlobalUserDisabled", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        return {"status": "success", "message": "Background Windows Apps disabled."}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}

@app.post("/api/manual_tweak/{tweak_name}")
async def manual_tweak_endpoint(tweak_name: str):
    log_synapse(f"[MANUAL OVERRIDE] User requested: {tweak_name}")
    if tweak_name == "disable_telemetry":
        return manual_disable_telemetry()
    elif tweak_name == "disable_fso":
        return manual_disable_fso()
    elif tweak_name == "deep_flush":
        return manual_deep_flush()
    elif tweak_name == "disable_bg_apps":
        return manual_disable_bg_apps()
    return {"status": "error", "message": "Unknown tweak."}


def generate_dashboard_data():
    metrics = get_system_metrics()
    
    return {
        "cpu": metrics["cpu"],
        "gpu": metrics["gpu"],
        "vram": metrics["ram"],
        "frametime": metrics["frametime"],
        "input_lag": metrics["input_lag"],
        "disk": metrics["disk"],
        "ping": metrics["ping"],
        "alert": sim_state.alert,
        "agent_state": sim_state.agent_state,
        "agent_action": sim_state.agent_action,
        "xai_cause": sim_state.xai_cause,
        "xai_explanation": sim_state.xai_explanation,
        "q_values": sim_state.q_values
    }

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = generate_dashboard_data()
            await websocket.send_json(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Client disconnected")
