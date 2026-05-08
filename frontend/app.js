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

const scenarioSelect = document.getElementById('anomaly-select');
const scenarioBtn = document.getElementById('trigger-scenario-btn');

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

    if (data.alert) {
        agentStateVal.classList.add('high');
        statusIndicator.innerHTML = '<span class="dot red"></span> Unstable';
        
        // Show Agent loop active
        agentPanel.classList.add('glow');
        xaiResultContainer.classList.add('hidden');
    } else {
        agentStateVal.classList.remove('high');
        statusIndicator.innerHTML = '<span class="dot green"></span> Stable';
        
        agentPanel.classList.remove('glow');
        
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
scenarioBtn.addEventListener('click', () => {
    const scenario = scenarioSelect.value;
    fetch('http://127.0.0.1:8000/api/trigger_scenario', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenario })
    })
    .then(res => res.json())
    .then(data => console.log(data))
    .catch(err => console.error(err));
});

// Synapse Logs Polling
const synapseLogsContainer = document.getElementById('synapse-logs');

async function fetchSynapseLogs() {
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

