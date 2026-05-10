// Chart.js Configuration
const ctx = document.getElementById('frametimeChart').getContext('2d');
Chart.defaults.color = '#9a9aab';
Chart.defaults.font.family = "'Inter', sans-serif";

const MAX_DATA_POINTS = 100;
const frametimeData = {
    labels: Array(MAX_DATA_POINTS).fill(''),
    datasets: [{
        label: 'Frametime (ms)',
        data: Array(MAX_DATA_POINTS).fill(16.6),
        borderColor: '#00e676',
        backgroundColor: 'rgba(0, 230, 118, 0.1)',
        borderWidth: 2,
        tension: 0.3,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4
    }]
};

const config = {
    type: 'line',
    data: frametimeData,
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false, // Turn off for realtime performance
        scales: {
            x: {
                display: false,
                grid: { display: false }
            },
            y: {
                min: 0,
                max: 80,
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                }
            }
        },
        plugins: {
            legend: { display: false }
        }
    }
};

const chart = new Chart(ctx, config);

// WebSocket Connection
const ws = new WebSocket('ws://127.0.0.1:8000/ws/telemetry');

// DOM Elements
const cpuFill = document.getElementById('cpu-fill');
const cpuVal = document.getElementById('cpu-val');
const gpuFill = document.getElementById('gpu-fill');
const gpuVal = document.getElementById('gpu-val');
const vramFill = document.getElementById('vram-fill');
const vramVal = document.getElementById('vram-val');
const inputLagFill = document.getElementById('input-lag-fill');
const inputLagVal = document.getElementById('input-lag-val');
const diskFill = document.getElementById('disk-fill');
const diskVal = document.getElementById('disk-val');
const pingFill = document.getElementById('ping-fill');
const pingVal = document.getElementById('ping-val');
const agentStateVal = document.getElementById('agent-state-val');

const statusIndicator = document.getElementById('status-indicator');
const agentPanel = document.getElementById('agent-panel');
const agentActionText = document.getElementById('agent-action-text');
const xaiResultContainer = document.getElementById('xai-result-container');
const xaiExplanationText = document.getElementById('xai-explanation-text');
const qValuesContainer = document.getElementById('q-values-container');

const diagnosticBtn = document.getElementById('trigger-diagnostic-btn');
const hitlContainer = document.getElementById('hitl-container');
const btnApprove = document.getElementById('btn-approve');
const btnReject = document.getElementById('btn-reject');
const simulateSpikeBtn = document.getElementById('simulate-spike-btn');
const activeTargetName = document.getElementById('active-target-name');
const btnBoostActive = document.getElementById('btn-boost-active');
const btnRestoreDefaults = document.getElementById('btn-restore-defaults');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};

function updateDashboard(data) {
    // Update Chart
    const dataset = chart.data.datasets[0];
    dataset.data.shift();
    dataset.data.push(data.frametime);
    
    // Dynamic chart color based on state
    if (data.alert) {
        dataset.borderColor = '#ff1744'; // Danger
        dataset.backgroundColor = 'rgba(255, 23, 68, 0.1)';
        chart.options.scales.y.max = 130; // Scale up to show massive spikes
    } else {
        dataset.borderColor = '#00e676'; // Safe
        dataset.backgroundColor = 'rgba(0, 230, 118, 0.1)';
        chart.options.scales.y.max = 80;
    }
    chart.update();

    // Update Progress Bars
    updateBar(cpuFill, cpuVal, data.cpu);
    updateBar(gpuFill, gpuVal, data.gpu);
    updateBar(vramFill, vramVal, data.vram);
    updateBar(inputLagFill, inputLagVal, data.input_lag, true);
    updateBar(diskFill, diskVal, data.disk);
    updateBar(pingFill, pingVal, data.ping, true);

    // Update Agent State
    agentStateVal.innerText = data.agent_state;
    agentActionText.innerText = data.agent_action;

    // Render Q-Values
    if (data.q_values && Object.keys(data.q_values).length > 0) {
        qValuesContainer.innerHTML = '';
        const sortedTools = Object.entries(data.q_values).sort((a, b) => b[1] - a[1]);
        const maxQ = Math.max(0.1, ...Object.values(data.q_values).map(Math.abs));
        
        sortedTools.forEach(([tool, qval]) => {
            const row = document.createElement('div');
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';
            row.style.fontSize = '0.75rem';
            row.style.marginBottom = '2px';
            
            const name = document.createElement('span');
            name.textContent = tool.replace(/_/g, ' ');
            name.style.color = '#ccc';
            name.style.flex = '1';
            name.style.overflow = 'hidden';
            name.style.textOverflow = 'ellipsis';
            name.style.whiteSpace = 'nowrap';
            
            const val = document.createElement('span');
            val.textContent = qval.toFixed(2);
            val.style.color = qval > 0 ? '#00e676' : (qval < 0 ? '#ff1744' : '#888');
            val.style.fontWeight = '600';
            val.style.marginLeft = '10px';
            val.style.minWidth = '35px';
            val.style.textAlign = 'right';
            
            row.appendChild(name);
            row.appendChild(val);
            
            const barContainer = document.createElement('div');
            barContainer.style.width = '100%';
            barContainer.style.height = '3px';
            barContainer.style.background = 'rgba(255,255,255,0.05)';
            barContainer.style.borderRadius = '2px';
            barContainer.style.marginBottom = '6px';
            
            const barFill = document.createElement('div');
            barFill.style.width = `${Math.min(100, (Math.abs(qval) / maxQ) * 100)}%`;
            barFill.style.height = '100%';
            barFill.style.background = qval > 0 ? 'linear-gradient(90deg, rgba(0,230,118,0.5), #00e676)' : 'linear-gradient(90deg, rgba(255,23,68,0.5), #ff1744)';
            barFill.style.borderRadius = '2px';
            barContainer.appendChild(barFill);
            
            const wrap = document.createElement('div');
            wrap.appendChild(row);
            wrap.appendChild(barContainer);
            
            qValuesContainer.appendChild(wrap);
        });
    }

    if (data.alert) {
        agentStateVal.classList.add('high');
        statusIndicator.innerHTML = '<span class="dot red"></span> Unstable';
        
        // Show Agent loop active
        agentPanel.classList.add('glow');
        xaiResultContainer.classList.add('hidden');
        
        // Handle HITL State
        if (data.awaiting_approval) {
            xaiResultContainer.classList.remove('hidden');
            xaiExplanationText.innerText = data.xai_explanation;
            hitlContainer.style.display = 'flex';
            hitlContainer.classList.remove('hidden');
        } else {
            hitlContainer.style.display = 'none';
            hitlContainer.classList.add('hidden');
        }
    } else {
        agentStateVal.classList.remove('high');
        statusIndicator.innerHTML = '<span class="dot green"></span> Stable';
        
        agentPanel.classList.remove('glow');
        hitlContainer.style.display = 'none';
        hitlContainer.classList.add('hidden');
        
        if (data.xai_explanation) {
            xaiResultContainer.classList.remove('hidden');
            xaiExplanationText.innerText = data.xai_explanation;
        } else {
            xaiResultContainer.classList.add('hidden');
        }
    }
}

function updateBar(fillEl, textEl, value, isMs = false) {
    fillEl.style.width = isMs ? `${Math.min(value, 100)}%` : `${value}%`;
    textEl.innerText = isMs ? `${value.toFixed(1)}ms` : `${value.toFixed(1)}%`;
    
    // Color gradient based on usage
    if(value > 85) {
        fillEl.style.background = 'linear-gradient(90deg, #f5576c 0%, #f093fb 100%)';
    } else {
        fillEl.style.background = 'linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)';
    }
}

// API Calls
diagnosticBtn.addEventListener('click', () => {
    fetch('http://127.0.0.1:8000/api/trigger_diagnostic', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(res => res.json())
    .then(data => console.log(data))
    .catch(err => console.error(err));
});

const stopSpikeBtn = document.getElementById('stop-spike-btn');

simulateSpikeBtn.addEventListener('click', () => {
    fetch('http://127.0.0.1:8000/api/simulate_spike', { method: 'POST' });
    simulateSpikeBtn.style.display = 'none';
    stopSpikeBtn.style.display = 'inline-block';
    // Auto-hide stop button after 5 seconds (spike duration)
    setTimeout(() => {
        stopSpikeBtn.style.display = 'none';
        simulateSpikeBtn.style.display = 'inline-block';
    }, 5000);
});

stopSpikeBtn.addEventListener('click', () => {
    fetch('http://127.0.0.1:8000/api/stop_spike', { method: 'POST' });
    stopSpikeBtn.style.display = 'none';
    simulateSpikeBtn.style.display = 'inline-block';
});

btnApprove.addEventListener('click', () => {
    fetch('http://127.0.0.1:8000/api/agent/approve', { method: 'POST' });
});

btnReject.addEventListener('click', () => {
    fetch('http://127.0.0.1:8000/api/agent/reject', { method: 'POST' });
});

btnBoostActive.addEventListener('click', async (e) => {
    const originalText = e.target.innerText;
    e.target.innerText = '🚀 BOOSTING...';
    try {
        const res = await fetch('http://127.0.0.1:8000/api/boost_active_game', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            e.target.innerText = '⚡ BOOSTED!';
            e.target.style.background = 'linear-gradient(135deg, #00e676, #4facfe)';
        } else {
            e.target.innerText = '❌ FAILED';
        }
    } catch (err) {
        e.target.innerText = '❌ ERROR';
    }
    
    setTimeout(() => {
        e.target.innerText = originalText;
        e.target.style.background = 'linear-gradient(135deg, #a020f0, #f093fb)';
    }, 3000);
});

btnRestoreDefaults.addEventListener('click', async (e) => {
    const originalText = e.target.innerText;
    e.target.innerText = 'RESTORING...';
    try {
        const res = await fetch('http://127.0.0.1:8000/api/restore_defaults', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            e.target.innerText = 'DEFAULTS RESTORED!';
            e.target.style.background = 'linear-gradient(135deg, #00e676, #4facfe)';
            e.target.style.color = '#fff';
        } else {
            e.target.innerText = 'FAILED';
        }
    } catch (err) {
        e.target.innerText = 'ERROR';
    }
    
    setTimeout(() => {
        e.target.innerText = originalText;
        e.target.style.background = 'linear-gradient(135deg, #ff3366, #ff6b6b)';
    }, 4000);
});

// Manual Overrides Logic
document.querySelectorAll('.override-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        const tweakName = e.target.getAttribute('data-tweak');
        const originalText = e.target.innerText;
        e.target.innerText = 'Executing...';
        e.target.style.color = '#f093fb';
        e.target.style.borderColor = '#f093fb';
        
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/manual_tweak/${tweakName}`, { method: 'POST' });
            const data = await res.json();
            
            if (data.status === 'success') {
                e.target.innerText = 'Success!';
                e.target.style.color = '#00e676';
                e.target.style.borderColor = '#00e676';
            } else {
                e.target.innerText = 'Failed (Admin Required)';
                e.target.style.color = '#ff1744';
                e.target.style.borderColor = '#ff1744';
            }
        } catch (err) {
            e.target.innerText = 'Network Error';
            e.target.style.color = '#ff1744';
            e.target.style.borderColor = '#ff1744';
        }
        
        // Reset after 3 seconds
        setTimeout(() => {
            e.target.innerText = originalText;
            e.target.style.color = '';
            e.target.style.borderColor = '';
        }, 3000);
    });
});

// Synapse Logs Polling
const synapseLogsContainer = document.getElementById('synapse-terminal');

async function fetchSynapseLogs() {
    if (!synapseLogsContainer) return;
    try {
        const res = await fetch('http://127.0.0.1:8000/api/logs');
        const data = await res.json();
        
        synapseLogsContainer.innerHTML = '';
        data.logs.forEach(log => {
            const logDiv = document.createElement('div');
            logDiv.style.color = '#9a9aab';
            if (log.includes('EXPLORING')) logDiv.style.color = '#f093fb';
            else if (log.includes('EXPLOITING')) logDiv.style.color = '#4facfe';
            else if (log.includes('LEARNING')) logDiv.style.color = '#00e676';
            else if (log.includes('ANOMALY')) logDiv.style.color = '#ff1744';
            else if (log.includes('SAFETY')) logDiv.style.color = '#ff3366';
            
            logDiv.innerText = log;
            synapseLogsContainer.appendChild(logDiv);
        });
        synapseLogsContainer.scrollTop = synapseLogsContainer.scrollHeight;
    } catch (err) {
        console.error(err);
    }
}

setInterval(fetchSynapseLogs, 2000);
fetchSynapseLogs();

// Target Lock Polling
const IGNORE_LIST = ['chrome.exe', 'opera.exe', 'msedge.exe', 'firefox.exe', 'explorer.exe', 'ApplicationFrameHost.exe', 'SearchApp.exe', 'ShellExperienceHost.exe'];

async function fetchActiveWindow() {
    try {
        const res = await fetch('http://127.0.0.1:8000/api/active_window');
        const data = await res.json();
        if (data.active_window && activeTargetName) {
            // Ignore browsers and system apps so Alt-Tabbing to dashboard doesn't lose the game target
            const processName = data.active_window.toLowerCase();
            const isIgnored = IGNORE_LIST.some(ignored => processName === ignored.toLowerCase());
            
            if (!isIgnored && data.active_window !== 'Unknown' && data.active_window !== 'None') {
                activeTargetName.innerText = data.active_window;
            }
        }
    } catch (err) {
        console.error(err);
    }
}
setInterval(fetchActiveWindow, 2000);
fetchActiveWindow();

