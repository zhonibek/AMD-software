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
const riskVal = document.getElementById('risk-val');

const statusIndicator = document.getElementById('status-indicator');
const xaiPanel = document.getElementById('xai-panel');
const xaiCauseText = document.getElementById('xai-cause-text');
const xaiExplanationText = document.getElementById('xai-explanation-text');

const fixBtn = document.getElementById('fix-btn');
const spikeBtn = document.getElementById('trigger-spike-btn');

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

    // Update Risk
    const riskPercent = (data.stutter_probability * 100).toFixed(1);
    riskVal.innerText = `${riskPercent}%`;
    if (data.alert) {
        riskVal.classList.add('high');
        statusIndicator.innerHTML = '<span class="dot red"></span> Unstable';
        
        // Show Alert
        xaiPanel.classList.remove('hidden');
        xaiCauseText.innerText = data.xai_cause.replace(/_/g, ' ');
        xaiExplanationText.innerText = data.xai_explanation;
    } else {
        riskVal.classList.remove('high');
        statusIndicator.innerHTML = '<span class="dot green"></span> Stable';
        
        // Hide Alert
        xaiPanel.classList.add('hidden');
    }
}

function updateBar(fillEl, textEl, value) {
    fillEl.style.width = `${value}%`;
    textEl.innerText = `${value.toFixed(1)}%`;
    
    // Color gradient based on usage
    if(value > 85) {
        fillEl.style.background = 'linear-gradient(90deg, #f5576c 0%, #f093fb 100%)';
    } else {
        fillEl.style.background = 'linear-gradient(90deg, #4facfe 0%, #00f2fe 100%)';
    }
}

// API Calls
fixBtn.addEventListener('click', () => {
    fetch('http://127.0.0.1:8000/api/fix', { method: 'POST' })
        .then(res => res.json())
        .then(data => console.log(data))
        .catch(err => console.error(err));
});

spikeBtn.addEventListener('click', () => {
    fetch('http://127.0.0.1:8000/api/trigger_spike', { method: 'POST' })
        .then(res => res.json())
        .then(data => console.log(data))
        .catch(err => console.error(err));
});
