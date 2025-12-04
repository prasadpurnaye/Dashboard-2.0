/**
 * VM Dashboard - Real Telemetry Integration
 * Displays VM cards with real-time CPU, memory, disk, and network metrics
 * Includes rate-of-change calculations from backend
 */

// Store VM gauge chart instances
const vmGaugeCharts = {};
let liveVMs = [];
let telemetryRefreshInterval = null;

/**
 * Create a small gauge chart for VM cards
 * @param {number} gaugeId - Gauge identifier
 * @param {string|number} vmId - VM identifier
 * @param {string} metricType - Type of metric (cpu, memory, disk, network_rx, network_tx)
 * @param {number} initialValue - Initial value for the gauge (0-100 for percentages)
 */
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

/**
 * Update VM gauge chart with new value
 * @param {string|number} vmId - VM identifier
 * @param {string} metricType - Type of metric
 * @param {number} newValue - New value (0-100 for percentages)
 */
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

/**
 * Update gauge element (generic helper)
 * @param {string} elementId - Element ID to update
 * @param {number} value - Value to display
 * @param {string} unit - Unit of measurement (optional)
 */
function updateGauge(elementId, value, unit = '%') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerText = `${value.toFixed(1)}${unit}`;
    }
}

/**
 * Format bytes to human readable format
 * @param {number} bytes - Number of bytes
 * @returns {string} Formatted bytes with unit
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format rate of change (degrees to readable format)
 * @param {number} rate - Rate in degrees from atan calculation
 * @returns {string} Formatted rate
 */
function formatRate(rate) {
    if (isNaN(rate) || !isFinite(rate)) {
        return '0.0°';
    }
    return Math.abs(rate).toFixed(1) + '°';
}

/**
 * Fetch live VMs from API
 * @returns {Promise<Array>} List of live VMs
 */
async function fetchLiveVMs() {
    try {
        const response = await fetch('/api/telemetry/live-vms');
        const data = await response.json();
        
        if (response.ok) {
            liveVMs = data.vms || [];
            console.log(`✓ Fetched ${liveVMs.length} live VMs from KVM`);
            return liveVMs;
        } else {
            console.error('❌ Error fetching live VMs:', data);
            return [];
        }
    } catch (error) {
        console.error('❌ Network error fetching live VMs:', error);
        return [];
    }
}

/**
 * Fetch real telemetry data from backend
 * @returns {Promise<Object>} Telemetry data with metrics and rates
 */
async function fetchVmTelemetry() {
    try {
        const response = await fetch('/api/telemetry/vm-telemetry');
        const data = await response.json();
        
        if (response.ok) {
            console.log(`✓ Fetched telemetry for ${data.count} VMs`);
            return data;
        } else {
            console.error('❌ Error fetching VM telemetry:', data);
            return { count: 0, vms: [], error: true };
        }
    } catch (error) {
        console.error('❌ Network error fetching VM telemetry:', error);
        return { count: 0, vms: [], error: true };
    }
}

/**
 * Update a single VM card with telemetry data
 * @param {string|number} vmId - VM identifier
 * @param {Object} vmData - VM telemetry data
 */
function updateVMCardFromTelemetry(vmId, vmData) {
    try {
        // Update CPU gauge and rate
        const cpuUsage = Math.min(100, Math.max(0, vmData.cpu_usage_percent || 0));
        updateVMGaugeChart(vmId, 'cpu', cpuUsage);
        
        const cpuRateElement = document.getElementById(`vm-rate-${vmId}-cpu`);
        if (cpuRateElement) {
            cpuRateElement.innerText = `Rate: ${formatRate(vmData.cpu_rate || 0)}`;
        }
        
        // Update Memory gauge and rate
        const memoryUsage = Math.min(100, Math.max(0, vmData.memory_usage_percent || 0));
        updateVMGaugeChart(vmId, 'memory', memoryUsage);
        
        const memRateElement = document.getElementById(`vm-rate-${vmId}-memory`);
        if (memRateElement) {
            memRateElement.innerText = `Rate: ${formatRate(vmData.memory_rate || 0)}`;
        }
        
        // Update Disk gauge and rate
        // Use disk_write_bytes for now (or could average read + write)
        const diskUsage = Math.min(100, Math.max(0, (vmData.disk_write_bytes || 0) / 1e9 * 100));
        updateVMGaugeChart(vmId, 'disk', diskUsage);
        
        const diskRateElement = document.getElementById(`vm-rate-${vmId}-disk`);
        if (diskRateElement) {
            diskRateElement.innerText = `Rate: ${formatRate(vmData.disk_write_rate || 0)}`;
        }
        
        // Update Network metrics (if elements exist)
        const networkRxElement = document.getElementById(`vm-network-${vmId}-rx`);
        if (networkRxElement) {
            networkRxElement.innerText = `RX: ${formatBytes(vmData.network_rx_bytes || 0)} (Rate: ${formatRate(vmData.network_rx_rate || 0)})`;
        }
        
        const networkTxElement = document.getElementById(`vm-network-${vmId}-tx`);
        if (networkTxElement) {
            networkTxElement.innerText = `TX: ${formatBytes(vmData.network_tx_bytes || 0)} (Rate: ${formatRate(vmData.network_tx_rate || 0)})`;
        }
        
    } catch (error) {
        console.error(`❌ Error updating VM card ${vmId}:`, error);
    }
}

/**
 * Update all VM gauges from fetched telemetry
 * @param {Object} telemetryData - Telemetry data from backend
 */
function updateAllVMGaugesFromTelemetry(telemetryData) {
    try {
        if (!telemetryData.vms || telemetryData.vms.length === 0) {
            console.warn('⚠ No VM telemetry data received');
            return;
        }
        
        // Update each VM with its telemetry
        telemetryData.vms.forEach(vm => {
            const vmId = vm.id || vm.uuid;
            if (vmId) {
                updateVMCardFromTelemetry(vmId, vm);
            }
        });
        
        console.log(`✓ Updated ${telemetryData.vms.length} VM cards with telemetry`);
    } catch (error) {
        console.error('❌ Error updating VM gauges from telemetry:', error);
    }
}

/**
 * Refresh VM telemetry with error handling
 */
async function refreshVmTelemetry() {
    try {
        const telemetryData = await fetchVmTelemetry();
        
        if (!telemetryData.error) {
            updateAllVMGaugesFromTelemetry(telemetryData);
        } else {
            console.warn('⚠ Telemetry fetch returned error, retrying next cycle');
        }
    } catch (error) {
        console.error('❌ Error in telemetry refresh cycle:', error);
    }
}

/**
 * Create VM cards with gauges (initial setup)
 */
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
    
    // Create card for each VM
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
                    <span>${vm.state || 'unknown'}</span>
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
                    <div class="vm-gauge-rate" id="vm-rate-${vmDisplayId}-cpu" style="font-size: 10px; color: #888;">Rate: 0.0°</div>
                </div>
                <div class="vm-small-gauge">
                    <div class="vm-gauge-label">Memory</div>
                    <div class="vm-gauge-canvas-container">
                        <canvas id="vm-gauge-${vmDisplayId}-memory" width="100" height="80"></canvas>
                    </div>
                    <div class="vm-gauge-value" id="vm-value-${vmDisplayId}-memory">0.0%</div>
                    <div class="vm-gauge-rate" id="vm-rate-${vmDisplayId}-memory" style="font-size: 10px; color: #888;">Rate: 0.0°</div>
                </div>
                <div class="vm-small-gauge">
                    <div class="vm-gauge-label">Disk</div>
                    <div class="vm-gauge-canvas-container">
                        <canvas id="vm-gauge-${vmDisplayId}-disk" width="100" height="80"></canvas>
                    </div>
                    <div class="vm-gauge-value" id="vm-value-${vmDisplayId}-disk">0.0%</div>
                    <div class="vm-gauge-rate" id="vm-rate-${vmDisplayId}-disk" style="font-size: 10px; color: #888;">Rate: 0.0°</div>
                </div>
            </div>
            <div class="vm-card-network" style="margin-top: 10px; font-size: 11px; color: #aaa;">
                <div id="vm-network-${vmDisplayId}-rx">RX: 0 B</div>
                <div id="vm-network-${vmDisplayId}-tx">TX: 0 B</div>
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
    
    // Fetch initial telemetry
    await refreshVmTelemetry();
}

/**
 * Start periodic telemetry refresh (default: every 1 second)
 * @param {number} intervalMs - Refresh interval in milliseconds
 */
function startVMTelemetryUpdates(intervalMs = 1000) {
    if (telemetryRefreshInterval) {
        clearInterval(telemetryRefreshInterval);
    }
    
    telemetryRefreshInterval = setInterval(() => {
        refreshVmTelemetry();
    }, intervalMs);
    
    console.log(`✓ VM telemetry auto-refresh started (interval: ${intervalMs}ms)`);
}

/**
 * Stop periodic telemetry refresh
 */
function stopVMTelemetryUpdates() {
    if (telemetryRefreshInterval) {
        clearInterval(telemetryRefreshInterval);
        telemetryRefreshInterval = null;
        console.log('⏹ VM telemetry auto-refresh stopped');
    }
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 VM Dashboard initializing...');
    createVMCards();
    startVMTelemetryUpdates(1000); // Refresh every 1 second
});

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', () => {
    stopVMTelemetryUpdates();
});
