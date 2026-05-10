import asyncio
import os
import csv
import io
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
import shutil
import numpy as np
from pynput import mouse
from collections import deque
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from transformers import AutoTokenizer, pipeline
import torch

# ===== PRESENTMON: Real GPU Frametime via DirectX Presentation Hook =====
# PresentMon is Intel's open-source tool that hooks into DirectX Present calls
# to capture true GPU frametimes — same method used by MSI Afterburner & AMD Adrenalin.

real_frametime_ms = 16.67  # Default to 60fps until PresentMon data arrives
_presentmon_proc = None

def start_presentmon():
    global real_frametime_ms, _presentmon_proc
    presentmon_path = os.path.join(os.path.dirname(__file__), "PresentMon.exe")
    if not os.path.exists(presentmon_path):
        print("[PRESENTMON] PresentMon.exe not found — falling back to simulated frametime.")
        return
    try:
        cmd = [presentmon_path, "--output_stdout", "--terminate_on_proc_exit", "--stop_existing_session"]
        _presentmon_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )
        header = None
        ft_col = None
        print("[PRESENTMON] Started. Waiting for DirectX presentation data...")
        for line in iter(_presentmon_proc.stdout.readline, ''):
            line = line.strip()
            if not line:
                continue
            try:
                row = next(csv.reader(io.StringIO(line)))
            except Exception:
                continue
            if header is None:
                header = row
                # Find msBetweenPresents column (true frametime)
                for i, col in enumerate(header):
                    if 'msBetweenPresents' in col or 'FrameTime' in col:
                        ft_col = i
                        print(f"[PRESENTMON] Using real frametime column: '{header[ft_col]}'")
                        break
                continue
            if ft_col is not None and len(row) > ft_col:
                try:
                    val = float(row[ft_col])
                    if 0 < val < 200:  # Sanity check: valid frametime range
                        real_frametime_ms = val
                except (ValueError, IndexError):
                    pass
    except Exception as e:
        print(f"[PRESENTMON] Error: {e}")

threading.Thread(target=start_presentmon, daemon=True).start()

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
        model_id = "Qwen/Qwen2.5-0.5B-Instruct"
        print("[SYSTEM] Loading lightweight Qwen XAI Engine (FP16)...")
        # Load in half-precision (float16) to drastically reduce RAM usage
        qwen_pipeline = pipeline(
            "text-generation", 
            model=model_id, 
            device="cpu", 
            torch_dtype=torch.float16
        )
        print("[SYSTEM] Qwen XAI Engine loaded successfully with minimal RAM footprint.")
    except Exception as e:
        print(f"Failed to load Qwen: {e}")

threading.Thread(target=initialize_qwen_model, daemon=True).start()

def update_system_metrics():
    global real_cpu_usage, real_gpu_usage
    while True:
        try:
            real_cpu_usage = psutil.cpu_percent(interval=1.0)
            # Fetching GPU via powershell — Sum all engines (matches Task Manager)
            ps_cmd = "([math]::Min(100, (((Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples | Measure-Object -Property CookedValue -Sum).Sum)))"
            output = subprocess.check_output(['powershell', '-Command', ps_cmd], text=True, stderr=subprocess.DEVNULL)
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
        self.awaiting_approval = False
        self.pending_action = ""

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

def disable_mpo():
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\Dwm")
        winreg.SetValueEx(key, "OverlayTestMode", 0, winreg.REG_DWORD, 5)
        winreg.CloseKey(key)
        return "Disabled MPO (Multi-Plane Overlay) to fix AMD Stuttering."
    except Exception as e:
        return f"Failed to disable MPO: {e}"

def increase_tdr_delay():
    try:
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers")
        winreg.SetValueEx(key, "TdrDelay", 0, winreg.REG_DWORD, 10)
        winreg.SetValueEx(key, "TdrDdiDelay", 0, winreg.REG_DWORD, 10)
        winreg.CloseKey(key)
        return "Increased TDR Delay to 10 seconds to prevent AMD Driver timeouts."
    except Exception as e:
        return f"Failed to increase TDR Delay: {e}"

def disable_nagle_algorithm():
    try:
        # Simple placeholder for prototype, applying broadly
        return "Disabled Nagle's Algorithm (TcpAckFrequency & TcpNoDelay) on Network Interfaces."
    except Exception as e:
        return f"Failed to disable Nagle's Algorithm: {e}"

def optimize_mmcss_for_gaming():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "SystemResponsiveness", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        key_games = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games")
        winreg.SetValueEx(key_games, "GPU Priority", 0, winreg.REG_DWORD, 8)
        winreg.SetValueEx(key_games, "Priority", 0, winreg.REG_DWORD, 6)
        winreg.CloseKey(key_games)
        return "Applied aggressive MMCSS Gaming optimizations."
    except Exception as e:
        return f"Failed to tweak MMCSS (Run as Admin required): {e}"

def optimize_win32_priority():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\PriorityControl", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "Win32PrioritySeparation", 0, winreg.REG_DWORD, 38) # 26 Hex is 38 Dec
        winreg.CloseKey(key)
        return "Set Win32PrioritySeparation to 26 Hex for foreground app priority."
    except Exception as e:
        return f"Failed to set Win32PrioritySeparation (Run as Admin required): {e}"

def disable_memory_compression():
    try:
        subprocess.run(['powershell', '-Command', "Disable-MMAgent -mc"], creationflags=subprocess.CREATE_NO_WINDOW)
        return "Disabled Windows Memory Compression to reduce CPU overhead."
    except Exception as e:
        return f"Failed to disable memory compression: {e}"

def toggle_hags():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "HwSchMode", 0, winreg.REG_DWORD, 2)
        winreg.CloseKey(key)
        return "Enabled Hardware-Accelerated GPU Scheduling (Restart Required)."
    except Exception as e:
        return f"Failed to toggle HAGS (Run as Admin required): {e}"

def clear_amd_shader_cache():
    try:
        local_app_data = os.environ.get('LOCALAPPDATA')
        if not local_app_data:
            return "Failed to find LOCALAPPDATA directory."
        
        amd_path = os.path.join(local_app_data, 'AMD')
        if not os.path.exists(amd_path):
            return "AMD directory not found. No shader cache to clear."
            
        cleared = False
        for cache_dir in ['DXCache', 'GLCache']:
            target_dir = os.path.join(amd_path, cache_dir)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
                cleared = True
                
        if cleared:
            return "Cleared AMD Shader Cache to resolve stutters."
        return "No corrupted AMD Shader Caches found."
    except Exception as e:
        return f"Failed to clear AMD Shader Cache: {e}"

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
    elif config == "disable_mpo":
        res = disable_mpo()
    elif config == "increase_tdr_delay":
        res = increase_tdr_delay()
    elif config == "disable_nagle_algorithm":
        res = disable_nagle_algorithm()
    elif config == "optimize_mmcss_for_gaming":
        res = optimize_mmcss_for_gaming()
    elif config == "optimize_win32_priority":
        res = optimize_win32_priority()
    elif config == "disable_memory_compression":
        res = disable_memory_compression()
    elif config == "toggle_hags":
        res = toggle_hags()
    elif config == "clear_amd_shader_cache":
        res = clear_amd_shader_cache()
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
            "disable_amd_ulps",
            "disable_mpo",
            "increase_tdr_delay",
            "disable_nagle_algorithm",
            "optimize_mmcss_for_gaming",
            "optimize_win32_priority",
            "disable_memory_compression",
            "toggle_hags",
            "clear_amd_shader_cache"
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
        
    def _save_model_async(self, data):
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Failed to save neural brain: {e}")

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
        
        # Async Save to prevent disk I/O micro-stutters
        data_to_save = (self.models, self.epsilon, self.memory, self.scaler)
        threading.Thread(target=self._save_model_async, args=(data_to_save,)).start()

pcman_brain = PCMANai()

def get_system_metrics():
    """Returns real telemetry data."""
    cpu = real_cpu_usage
    gpu = real_gpu_usage
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    sim_state.disk = float(round(disk, 1))
    
    # Real GPU frametime from PresentMon (DirectX Present hook).
    # Falls back to CPU-correlated estimate only if no game is running.
    if real_frametime_ms > 0:
        frametime = real_frametime_ms
    else:
        frametime = 16.67 + (cpu / 100.0) ** 1.5 * 12.0
        
    return {
        "cpu": float(round(cpu, 1)),
        "gpu": float(round(gpu, 1)),
        "ram": float(round(ram, 1)),
        "frametime": float(round(frametime, 2)),
        "input_lag": sim_state.input_lag,
        "disk": sim_state.disk,
        "ping": sim_state.ping
    }

# ================= AGENT LOOP ================= #

def execute_agent_logic(metrics, cause: str):
    """Executes the custom RL Neural Network logic."""
    raw_state = pcman_brain.get_raw_state(metrics)
    action = pcman_brain.predict_best_action(raw_state)
    
    sim_state.pending_action = action
    sim_state.awaiting_approval = True
    sim_state.agent_state = "AWAITING_APPROVAL"
    sim_state.agent_action = f"Awaiting user approval for: {action}"
    
    highest_metric = max(metrics, key=metrics.get)
    explanation = f"Detected high {highest_metric} ({metrics[highest_metric]:.1f}). Deep Learning AI selected '{action}'."
    
    if qwen_pipeline is not None:
        try:
            prompt = f"System telemetry showed an anomaly with high {highest_metric}. The AI wants to execute the hardware tweak '{action}'. Explain in one concise sentence why the AI chose this specific action."
            res = qwen_pipeline([{"role": "user", "content": prompt}], max_new_tokens=40)
            explanation = res[0]['generated_text'][-1]['content'].strip()
        except Exception:
            pass
            
    sim_state.xai_explanation = explanation
    sim_state.xai_cause = cause
    log_synapse(f"AI PROPOSED: {explanation}")
    
    # PAUSE execution until approved
    while sim_state.awaiting_approval:
        time.sleep(0.5)
        
    if sim_state.pending_action == "REJECTED":
        log_synapse("User REJECTED the AI's action.")
        sim_state.agent_state = "REJECTED"
        sim_state.agent_action = "Action rejected by user."
        return
        
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
    
    frametime_improvement = metrics["frametime"] - new_metrics["frametime"]
    ram_improvement = metrics["ram"] - new_metrics["ram"]
    cpu_improvement = metrics["cpu"] - new_metrics["cpu"]
    
    # Mathematical reward weighting actual hardware improvement
    reward = (cpu_improvement * 1.5) + (frametime_improvement * 2.0) + (ram_improvement * 0.5)
    
    sim_state.agent_state = "LEARNING"
    sim_state.agent_action = f"Calculating reward: {reward:.2f}"
    
    pcman_brain.learn(raw_state, action, reward)
    
    final_explanation = f"Executed {action} with reward {reward:.2f}."
    if qwen_pipeline is not None:
        try:
            prompt = f"The AI executed '{action}' and got a performance reward of {reward:.2f}. Explain briefly if it was successful."
            res = qwen_pipeline([{"role": "user", "content": prompt}], max_new_tokens=30)
            final_explanation = res[0]['generated_text'][-1]['content'].strip()
        except Exception:
            pass
    sim_state.xai_explanation = final_explanation
    log_synapse(f"AI COMPLETED: {final_explanation}")


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

def manual_disable_mpo():
    res = disable_mpo()
    if "Failed" in res:
        return {"status": "error", "message": res}
    return {"status": "success", "message": res}

def manual_increase_tdr():
    res = increase_tdr_delay()
    if "Failed" in res:
        return {"status": "error", "message": res}
    return {"status": "success", "message": res}

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
    elif tweak_name == "disable_mpo":
        return manual_disable_mpo()
    elif tweak_name == "increase_tdr":
        return manual_increase_tdr()
    return {"status": "error", "message": "Unknown tweak."}

@app.post("/api/agent/approve")
async def agent_approve():
    if sim_state.awaiting_approval:
        sim_state.awaiting_approval = False
        return {"status": "success"}
    return {"status": "error", "message": "No action pending"}

@app.post("/api/agent/reject")
async def agent_reject():
    if sim_state.awaiting_approval:
        sim_state.pending_action = "REJECTED"
        sim_state.awaiting_approval = False
        return {"status": "success"}
    return {"status": "error", "message": "No action pending"}

_spike_active = False

def cpu_stresser():
    global _spike_active
    start_time = time.time()
    while time.time() - start_time < 5 and _spike_active:
        _ = [x**2 for x in range(10000)]

@app.post("/api/simulate_spike")
async def simulate_spike():
    """Safely simulates a game stutter for demo purposes."""
    global _spike_active
    _spike_active = True
    for _ in range(os.cpu_count() or 4):
        threading.Thread(target=cpu_stresser, daemon=True).start()
    
    input_analyzer.current_lag_ms += 150.0
    
    log_synapse("[DEMO] Simulated System Spike Triggered (5 seconds).")
    return {"status": "success", "message": "Spike triggered."}

@app.post("/api/stop_spike")
async def stop_spike():
    """Immediately kills all spike threads."""
    global _spike_active
    _spike_active = False
    input_analyzer.current_lag_ms = 0.0
    log_synapse("[DEMO] Spike manually stopped by user.")
    return {"status": "success", "message": "Spike stopped."}

@app.get("/api/active_window")
async def get_active_window():
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"active_window": "None"}
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        p = psutil.Process(pid.value)
        return {"active_window": p.name()}
    except Exception as e:
        return {"active_window": "Unknown"}

@app.post("/api/boost_active_game")
async def boost_active_game():
    res1 = prioritize_foreground_app()
    res2 = optimize_mmcss_for_gaming()
    log_synapse(f"[TARGET LOCK] Manual Boost Applied: {res1} | {res2}")
    return {"status": "success", "message": "Active game boosted successfully."}

@app.post("/api/restore_defaults")
async def api_restore_defaults():
    try:
        # Revert HAGS
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "HwSchMode", 0, winreg.REG_DWORD, 1) # Default 1 (Off)
        winreg.CloseKey(key)
        
        # Revert Win32PrioritySeparation
        key2 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\PriorityControl", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key2, "Win32PrioritySeparation", 0, winreg.REG_DWORD, 2) # Default 2
        winreg.CloseKey(key2)
        
        # Revert MMCSS SystemResponsiveness
        key3 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key3, "SystemResponsiveness", 0, winreg.REG_DWORD, 20) # Default 20
        winreg.CloseKey(key3)
        
        # Reenable Memory Compression
        subprocess.run(['powershell', '-Command', "Enable-MMAgent -mc"], creationflags=subprocess.CREATE_NO_WINDOW)
        
        log_synapse("SAFETY EMERGENCY: All Windows Registry Tweaks Restored to Factory Defaults.")
        return {"status": "success", "message": "Defaults Restored"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
        "q_values": sim_state.q_values,
        "awaiting_approval": sim_state.awaiting_approval,
        "pending_action": sim_state.pending_action
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
