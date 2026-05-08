import asyncio
import json
import random
import os
import psutil
import threading
import subprocess
import time
import multiprocessing
import multiprocessing
import queue
import winreg
import ctypes
import pickle
from pynput import mouse

def cleanup_orphaned_stressors():
    """Kills any runaway powershell stress loops if the server crashed previously."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'powershell' in proc.info['name'].lower():
                cmd = ' '.join(proc.info['cmdline'] or [])
                if 'while($true){}' in cmd:
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

# Run cleanup on boot
cleanup_orphaned_stressors()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from sklearn.linear_model import SGDRegressor
import numpy as np
from collections import deque

load_dotenv()
app = FastAPI()

# Allow CORS for the frontend
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

def update_system_metrics():
    global real_cpu_usage, real_gpu_usage
    while True:
        try:
            real_cpu_usage = psutil.cpu_percent(interval=1.0)
            cmd = ['powershell', '-Command', "(((Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples | Measure-Object -Property CookedValue -Maximum).Maximum)"]
            output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            val_str = output.strip().replace(',', '.')
            if val_str:
                real_gpu_usage = float(val_str)
        except Exception:
            pass

threading.Thread(target=update_system_metrics, daemon=True).start()

# Global State for Tracking
class SimulationState:
    def __init__(self):
        self.is_spiking = False
        self.frametime = 16.6
        self.input_lag = 0.0
        self.disk = 0.0
        self.ping = 15.0
        self.agent_state = "IDLE"
        self.agent_action = "Monitoring system telemetry..."
        self.xai_explanation = ""
        self.xai_cause = ""
        self.alert = False

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

active_stress_processes = []
memory_hog = []

# ================= TOOLS ================= #

def get_system_metrics():
    """Returns current CPU, GPU, RAM, and Frametime."""
    cpu = real_cpu_usage
    gpu = real_gpu_usage if real_gpu_usage > 0 else (real_cpu_usage * 1.5 + random.uniform(2, 8))
    gpu = min(max(gpu, 1.0), 99.0)
    ram = psutil.virtual_memory().percent
    
    # Calculate frametime organically
    if sim_state.is_spiking:
        base_frametime = 16.5 + (cpu / 100.0) * random.uniform(30, 80)
    else:
        base_frametime = 16.5 + (cpu / 100.0) * random.uniform(2, 5)
        
    sim_state.frametime = float(round(base_frametime, 2))
    
    return {
        "cpu": float(round(cpu, 1)),
        "gpu": float(round(gpu, 1)),
        "ram": float(round(ram, 1)),
        "frametime": sim_state.frametime,
        "input_lag": sim_state.input_lag,
        "disk": sim_state.disk,
        "ping": sim_state.ping
    }

def run_performance_scenario(type: str):
    """Runs simulated workloads."""
    global active_stress_processes, memory_hog
    
    if type == "cpu_heavy":
        cores = multiprocessing.cpu_count()
        for _ in range(cores):
            p = subprocess.Popen(['powershell', '-WindowStyle', 'Hidden', '-Command', 'while($true){}'])
            active_stress_processes.append(p)
        sim_state.is_spiking = True
        return "Started CPU heavy workload scenario."
    elif type == "memory_bound":
        try:
            for _ in range(multiprocessing.cpu_count() * 4):
                memory_hog.append(" " * 1024 * 1024 * 100)
        except MemoryError:
            pass
        sim_state.is_spiking = True
        return "Started Memory bound workload scenario."
    elif type == "input_lag_spike":
        cores = multiprocessing.cpu_count()
        for _ in range(cores):
            p = subprocess.Popen(['powershell', '-WindowStyle', 'Hidden', '-Command', '$r=1; while($true){$r=$r*1.0000001}'])
            try:
                proc = psutil.Process(p.pid)
                proc.nice(psutil.HIGH_PRIORITY_CLASS)
            except:
                pass
            active_stress_processes.append(p)
        sim_state.is_spiking = True
        return "Started Input Lag Spike scenario."
    elif type == "memory_leak":
        try:
            for _ in range(multiprocessing.cpu_count() * 8):
                memory_hog.append(" " * 1024 * 1024 * 200) # 200MB chunks
        except MemoryError:
            pass
        sim_state.is_spiking = True
        return "Started Memory Leak scenario."
    elif type == "disk_thrash":
        sim_state.disk = 99.0
        sim_state.is_spiking = True
        return "Started Disk Thrashing scenario."
    elif type == "bad_affinity":
        p = subprocess.Popen(['powershell', '-WindowStyle', 'Hidden', '-Command', 'while($true){}'])
        try:
            proc = psutil.Process(p.pid)
            proc.cpu_affinity([0]) # Pin to Core 0
        except:
            pass
        active_stress_processes.append(p)
        sim_state.is_spiking = True
        return "Started Bad Affinity scenario."
    elif type == "ping_spike":
        sim_state.ping = random.uniform(150, 400)
        sim_state.is_spiking = True
        return "Started Ping Spike scenario."
    return f"Scenario {type} not recognized."

def set_ultimate_performance_plan():
    """Sets power plan to High Performance."""
    try:
        subprocess.run(['powercfg', '-setactive', '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return "Set power plan to High Performance."
    except Exception as e:
        return f"Failed to set power plan: {e}"

def optimize_registry_input_lag():
    """Modifies Win32PrioritySeparation and PowerThrottling to reduce input lag."""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\PriorityControl", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "Win32PrioritySeparation", 0, winreg.REG_DWORD, 0x26)
        winreg.CloseKey(key)
        
        try:
            pt_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling")
            winreg.SetValueEx(pt_key, "PowerThrottlingOff", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(pt_key)
        except Exception:
            pass
            
        return "Applied Registry Tweaks for Input Lag."
    except Exception as e:
        return f"Failed to tweak registry (Run as Admin required): {e}"

def prioritize_foreground_app():
    """Sets active window process to HIGH_PRIORITY_CLASS."""
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

def flush_standby_memory():
    """Simulates clearing the standby memory list."""
    return "Flushed Standby Memory List."

def restrict_core_affinity():
    """Simulates restricting background apps to E-Cores."""
    return "Restricted Background Apps to E-Cores."

def disable_network_throttling():
    """Simulates registry tweak for network packets."""
    return "Disabled Nagle's Algorithm for Network."

def apply_optimization(config: str):
    """Applies system tuning changes. Each tool only fixes specific problems."""
    global active_stress_processes, memory_hog
    
    # PCMANai must now use the CORRECT tool to clear the correct stressor.
    # If the wrong tool is used, the stressor remains, and the AI gets a penalty.
    
    res = "No effect."
    
    if config == "kill_stress_processes":
        for p in active_stress_processes:
            try: p.kill()
            except: pass
        active_stress_processes.clear()
        sim_state.is_spiking = False
        res = "Killed background stress processes."
    
    elif config == "flush_standby_memory":
        memory_hog.clear()
        res = flush_standby_memory()
        
    elif config == "disable_network_throttling":
        sim_state.ping = 15.0
        res = disable_network_throttling()
        
    elif config == "restrict_core_affinity":
        # Unpin from Core 0
        for p in active_stress_processes:
            try:
                proc = psutil.Process(p.pid)
                proc.cpu_affinity(list(range(1, multiprocessing.cpu_count())))
            except: pass
        res = restrict_core_affinity()

    elif config == "optimize_registry_input_lag":
        sim_state.disk = 0.0
        res = optimize_registry_input_lag()
        
    elif config == "enable_ultimate_power_plan":
        res = set_ultimate_performance_plan()
        
    elif config == "prioritize_active_window":
        res = prioritize_foreground_app()
        
    return res

def benchmark():
    """Runs a quick benchmark and returns average frametime."""
    samples = []
    for _ in range(5):
        samples.append(get_system_metrics()["frametime"])
        time.sleep(0.5)
    
    avg_frametime = sum(samples) / len(samples)
    return f"Benchmark complete. Average Frametime: {avg_frametime:.2f}ms"

# ================= PCMANai BRAIN ================= #

synapse_logs = deque(maxlen=50)

def log_synapse(msg: str):
    synapse_logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    print(msg)

class PCMANai:
    def __init__(self):
        self.actions = [
            "do_nothing",
            "enable_ultimate_power_plan",
            "optimize_registry_input_lag",
            "prioritize_active_window",
            "flush_standby_memory",
            "restrict_core_affinity",
            "disable_network_throttling",
            "kill_stress_processes"
        ]
        self.model_path = "pcman_brain.pkl"
        
        if os.path.exists(self.model_path):
            with open(self.model_path, "rb") as f:
                self.models, self.epsilon = pickle.load(f)
            log_synapse(f"[SYSTEM] Loaded existing PCMANai brain. Epsilon: {self.epsilon:.2f}")
        else:
            self.models = {action: SGDRegressor(learning_rate='constant', eta0=0.01) for action in self.actions}
            dummy_state = np.zeros((1, 7))
            for action in self.actions:
                self.models[action].partial_fit(dummy_state, [0.0])
            self.epsilon = 0.5 
            log_synapse("[SYSTEM] Initialized fresh PCMANai brain.")
        
        self.decay = 0.95
        
    def get_state_vector(self, metrics):
        return np.array([[
            metrics['cpu'],
            metrics['gpu'],
            metrics['ram'],
            metrics['frametime'],
            metrics['input_lag'],
            metrics['disk'],
            metrics['ping']
        ]])
        
    def predict_best_action(self, state):
        if random.random() < self.epsilon:
            self.epsilon = max(0.05, self.epsilon * self.decay)
            action = random.choice(self.actions)
            log_synapse(f"EXPLORING: Randomly selected '{action}' (Epsilon: {self.epsilon:.2f})")
            return action
            
        best_action = "do_nothing"
        best_reward = -float('inf')
        
        log_synapse("PREDICTING REWARDS:")
        for action, model in self.models.items():
            predicted_reward = model.predict(state)[0]
            log_synapse(f" - {action}: {predicted_reward:.2f}")
            if predicted_reward > best_reward:
                best_reward = predicted_reward
                best_action = action
                
        log_synapse(f"EXPLOITING: Chose '{best_action}' with predicted reward {best_reward:.2f}")
        return best_action
        
    def learn(self, state, action, reward):
        self.models[action].partial_fit(state, [reward])
        log_synapse(f"LEARNING: Updated weights for '{action}' with reward {reward:.2f}")
        
        # Save experience to disk
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump((self.models, self.epsilon), f)
        except Exception as e:
            print(f"Failed to save brain: {e}")

pcman_brain = PCMANai()

# ================= AGENT LOOP ================= #

def agent_loop():
    """The continuous reasoning loop for PCMANai."""
    log_synapse("PCMANai Initialized. Awaiting telemetry spikes...")
    while True:
        metrics = get_system_metrics()
        
        # If system is healthy, idle.
        if metrics["frametime"] < 30.0 and metrics["input_lag"] < 15.0:
            if not sim_state.alert:
                sim_state.agent_state = "IDLE"
                sim_state.agent_action = "Monitoring system telemetry..."
            time.sleep(1)
            continue
            
        # Detect Anomaly
        if not sim_state.alert:
            sim_state.alert = True
            sim_state.agent_state = "ANALYZING"
            sim_state.agent_action = f"Anomaly detected. PCMANai analyzing state..."
            log_synapse(f"ANOMALY: Frametime {metrics['frametime']}ms, Input Lag {metrics['input_lag']}ms")
            
            state_vector = pcman_brain.get_state_vector(metrics)
            action = pcman_brain.predict_best_action(state_vector)
            
            sim_state.agent_state = "EXECUTING_TOOL"
            sim_state.agent_action = f"Executing: {action}"
            
            if action != "do_nothing":
                apply_optimization(action)
            
            sim_state.agent_state = "MEASURING"
            sim_state.agent_action = "Waiting for metrics to settle..."
            time.sleep(3) # Let the optimization take effect
            
            new_metrics = get_system_metrics()
            
            frametime_delta = metrics["frametime"] - new_metrics["frametime"]
            lag_delta = metrics["input_lag"] - new_metrics["input_lag"]
            
            reward = frametime_delta + lag_delta
            
            sim_state.agent_state = "LEARNING"
            sim_state.agent_action = f"Calculating reward: {reward:.2f}"
            
            pcman_brain.learn(state_vector, action, reward)
            
            sim_state.agent_state = "EXPLAINING"
            sim_state.agent_action = "Providing final explanation..."
            
            sim_state.xai_explanation = f"PCMANai applied '{action}' resulting in a reward of {reward:.2f}."
            sim_state.xai_cause = "PCMANai Optimization Applied"
            
            time.sleep(4)
            sim_state.alert = False
            
        time.sleep(1)

threading.Thread(target=agent_loop, daemon=True).start()

# ================= API ENDPOINTS ================= #

@app.get("/api/logs")
async def logs_endpoint():
    return {"logs": list(synapse_logs)}

class ScenarioRequest(BaseModel):
    scenario: str

@app.post("/api/trigger_scenario")
async def trigger_scenario(request: ScenarioRequest):
    """Unified endpoint to trigger an anomaly scenario."""
    run_performance_scenario(request.scenario)
    return {"status": "success", "message": f"{request.scenario} triggered."}

def generate_dashboard_data():
    """Simulates realistic telemetry data, reacting to state."""
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
        "xai_explanation": sim_state.xai_explanation
    }

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = generate_dashboard_data()
            await websocket.send_json(data)
            await asyncio.sleep(0.1)  # 100ms polling interval for UI
    except WebSocketDisconnect:
        print("Client disconnected")
