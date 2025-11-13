// Store VM gauge chart instances
const vmGaugeCharts = {};
let liveVMs = [];

// Create a small gauge chart for VM cards
function createSmallVMGauge(gaugeId, vmId, metricType, initialValue = 0) {
    const canvasId = `vm-gauge-${vmId}-${metricType}`;
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    
    const ctx = canvas.getContext('2d');
    const key = `${vmId}-${metricType}`;
    
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [
                {
                    data: [initialValue, 90 - initialValue],
                    backgroundColor: [
                        '#4caf50', // Green
                        'rgba(255, 255, 255, 0.2)'
                    ],
                    borderColor: '#fff',
                    borderWidth: 1,
                    borderRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            },
            rotation: -90,
            circumference: 180,
            cutout: '80%'
        },
        plugins: [
            {
                id: 'textCenterSmall',
                beforeDraw(chart) {
                    const { width, height } = chart.ctx.canvas;
                    chart.ctx.restore();
                    
                    const vmMetrics = vmGaugeCharts[key] || {};
                    const value = vmMetrics.value || 0;
                    
                    const fontSize = '12';
                    chart.ctx.font = `bold ${fontSize}px Arial`;
                    chart.ctx.textBaseline = 'middle';
                    chart.ctx.fillStyle = '#fff';
                    
                    const text = `${value.toFixed(1)}%`;
                    const textX = Math.round((width - chart.ctx.measureText(text).width) / 2);
                    const textY = height / 1.9;
                    
                    chart.ctx.fillText(text, textX, textY);
                    chart.ctx.save();
                }
            }
        ]
    });
    
    vmGaugeCharts[key] = { chart, value: initialValue };
    return chart;
}

// Update VM gauge
function updateVMGaugeChart(vmId, metricType, newValue) {
    const key = `${vmId}-${metricType}`;
    if (vmGaugeCharts[key]) {
        vmGaugeCharts[key].value = newValue;
        vmGaugeCharts[key].chart.data.datasets[0].data = [newValue, 90 - newValue];
        vmGaugeCharts[key].chart.update();
    }
    
    const valueElement = document.getElementById(`vm-value-${vmId}-${metricType}`);
    if (valueElement) {
        valueElement.innerText = `${newValue.toFixed(1)}%`;
    }
}

// Fetch live VMs from API
async function fetchLiveVMs() {
    try {
        const response = await fetch('/api/telemetry/live-vms');
        const data = await response.json();
        
        if (response.ok) {
            liveVMs = data.vms || [];
            console.log(`✓ Fetched ${liveVMs.length} live VMs from KVM`);
            return liveVMs;
        } else {
            console.error('Error fetching live VMs:', data);
            return [];
        }
    } catch (error) {
        console.error('Error fetching live VMs:', error);
        return [];
    }
}

// Create VM cards with gauges
async function createVMCards() {
    const container = document.querySelector('.vm-cards-scroll');
    container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">Loading VMs...</p>';
    
    // Fetch live VMs from API
    const vms = await fetchLiveVMs();
    
    if (vms.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">No VMs found. Start telemetry monitoring to see VMs.</p>';
        return;
    }
    
    container.innerHTML = ''; // Clear loading message
    
    vms.forEach(vm => {
        const card = document.createElement('div');
        card.className = 'vm-card';
        
        const vmDisplayId = vm.id || vm.uuid || 'unknown';
        const vmName = vm.name || `VM-${vmDisplayId}`;
        const cpuCount = vm.cpu_count || 0;
        const memoryGb = Math.round((vm.memory_max || 0) / 1024 / 1024);
        
        card.innerHTML = `
            <div class="vm-card-header">
                <div class="vm-card-title">${vmName}</div>
                <div class="vm-card-status">
                    <span class="vm-status-indicator"></span>
                    <span>Online</span>
                </div>
            </div>
            <div class="vm-card-info">
                <p><strong>ID:</strong> ${vmDisplayId}</p>
                <p><strong>CPU:</strong> ${cpuCount} vCPU</p>
                <p><strong>Memory:</strong> ${memoryGb} GB</p>
            </div>
            <div class="vm-card-gauges">
                <div class="vm-small-gauge">
                    <div class="vm-gauge-label">CPU</div>
                    <div class="vm-gauge-canvas-container">
                        <canvas id="vm-gauge-${vmDisplayId}-cpu" width="100" height="80"></canvas>
                    </div>
                    <div class="vm-gauge-value" id="vm-value-${vmDisplayId}-cpu">0.0%</div>
                </div>
                <div class="vm-small-gauge">
                    <div class="vm-gauge-label">Memory</div>
                    <div class="vm-gauge-canvas-container">
                        <canvas id="vm-gauge-${vmDisplayId}-memory" width="100" height="80"></canvas>
                    </div>
                    <div class="vm-gauge-value" id="vm-value-${vmDisplayId}-memory">0.0%</div>
                </div>
                <div class="vm-small-gauge">
                    <div class="vm-gauge-label">Disk</div>
                    <div class="vm-gauge-canvas-container">
                        <canvas id="vm-gauge-${vmDisplayId}-disk" width="100" height="80"></canvas>
                    </div>
                    <div class="vm-gauge-value" id="vm-value-${vmDisplayId}-disk">0.0%</div>
                </div>
            </div>
        `;
        
        container.appendChild(card);
    });
    
    // Create gauges for each VM after cards are added to DOM
    vms.forEach(vm => {
        const vmDisplayId = vm.id || vm.uuid || 'unknown';
        createSmallVMGauge(1, vmDisplayId, 'cpu', 0);
        createSmallVMGauge(2, vmDisplayId, 'memory', 0);
        createSmallVMGauge(3, vmDisplayId, 'disk', 0);
    });
    
    // Generate random data for VM gauges (demo)
    updateVMGaugesWithRandomData();
}

// Generate random data for VM gauges (demo)
function updateVMGaugesWithRandomData() {
    liveVMs.forEach(vm => {
        const vmDisplayId = vm.id || vm.uuid || 'unknown';
        updateVMGaugeChart(vmDisplayId, 'cpu', Math.random() * 90);
        updateVMGaugeChart(vmDisplayId, 'memory', Math.random() * 90);
        updateVMGaugeChart(vmDisplayId, 'disk', Math.random() * 90);
    });
}

// Auto-update gauges periodically
function startVMGaugeUpdates() {
    setInterval(() => {
        updateVMGaugesWithRandomData();
    }, 2000); // Update every 2 seconds
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    createVMCards();
    startVMGaugeUpdates();
});
