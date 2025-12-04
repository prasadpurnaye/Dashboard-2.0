/**
 * Resource Monitoring Page
 * Real-time VM resource metrics with time-series graphs
 */

// Global state
const state = {
    selectedVmId: null,
    selectedVmName: null,
    vms: [],
    charts: {},
    metricsHistory: {},
    pollingInterval: null,
    maxHistoryPoints: 60, // Keep last 60 data points
};

// Metric definitions for each tab
const metricDefinitions = {
    'cpu-memory': [
        { key: 'timeusr', name: 'User CPU Time', unit: 'ns', type: 'number' },
        { key: 'timesys', name: 'System CPU Time', unit: 'ns', type: 'number' },
        { key: 'memactual', name: 'Actual Memory', unit: 'KB', type: 'bytes' },
        { key: 'memrss', name: 'Memory RSS', unit: 'KB', type: 'bytes' },
        { key: 'memavailable', name: 'Available Memory', unit: 'KB', type: 'bytes' },
        { key: 'memusable', name: 'Usable Memory', unit: 'KB', type: 'bytes' },
        { key: 'memswap_in', name: 'Swap In', unit: '', type: 'number' },
        { key: 'memswap_out', name: 'Swap Out', unit: '', type: 'number' },
        { key: 'memmajor_fault', name: 'Major Faults', unit: '', type: 'number' },
        { key: 'memminor_fault', name: 'Minor Faults', unit: '', type: 'number' },
        { key: 'memdisk_cache', name: 'Disk Cache', unit: 'KB', type: 'bytes' },
    ],
    'network': [
        { key: 'net_rxbytes', name: 'RX Bytes', unit: 'B', type: 'bytes' },
        { key: 'net_rxpackets', name: 'RX Packets', unit: '', type: 'number' },
        { key: 'net_rxerrors', name: 'RX Errors', unit: '', type: 'number' },
        { key: 'net_rxdrops', name: 'RX Drops', unit: '', type: 'number' },
        { key: 'net_txbytes', name: 'TX Bytes', unit: 'B', type: 'bytes' },
        { key: 'net_txpackets', name: 'TX Packets', unit: '', type: 'number' },
        { key: 'net_txerrors', name: 'TX Errors', unit: '', type: 'number' },
        { key: 'net_txdrops', name: 'TX Drops', unit: '', type: 'number' },
    ],
    'disk': [
        { key: 'disk_rd_req', name: 'Read Requests', unit: '', type: 'number' },
        { key: 'disk_rd_bytes', name: 'Read Bytes', unit: 'B', type: 'bytes' },
        { key: 'disk_wr_reqs', name: 'Write Requests', unit: '', type: 'number' },
        { key: 'disk_wr_bytes', name: 'Write Bytes', unit: 'B', type: 'bytes' },
        { key: 'disk_errors', name: 'Errors', unit: '', type: 'number' },
    ],
};

/**
 * Format value with appropriate unit
 */
function formatValue(value, type = 'number', unit = '') {
    if (value === null || value === undefined || isNaN(value)) {
        return '-- ' + unit;
    }

    switch (type) {
        case 'bytes':
            return formatBytes(value) + (unit ? ' ' + unit : '');
        case 'number':
            return Math.round(value * 100) / 100 + (unit ? ' ' + unit : '');
        default:
            return value + (unit ? ' ' + unit : '');
    }
}

/**
 * Format bytes to human-readable format
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Initialize the page
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Resource Monitoring initializing...');

    // Load VMs
    await loadVMs();

    // Setup event listeners
    setupEventListeners();

    console.log('✓ Resource Monitoring initialized');
});

/**
 * Load live VMs and populate dropdown
 */
async function loadVMs() {
    try {
        showLoadingState(true);
        const response = await fetch('/api/telemetry/live-vms');
        const data = await response.json();

        if (!response.ok || !data.vms) {
            throw new Error('Failed to load VMs');
        }

        state.vms = data.vms;
        console.log(`✓ Loaded ${state.vms.length} VMs`);

        // Populate dropdown
        const dropdown = document.getElementById('vm-dropdown');
        dropdown.innerHTML = '<option value="">-- Select a VM --</option>';

        state.vms.forEach(vm => {
            const option = document.createElement('option');
            option.value = vm.id;
            option.textContent = `${vm.name} (${vm.cpu_count} vCPU, ${Math.round((vm.memory_max || 0) / 1024 / 1024)}GB)`;
            dropdown.appendChild(option);
        });

        showLoadingState(false);
    } catch (error) {
        console.error('❌ Error loading VMs:', error);
        showErrorState(`Failed to load VMs: ${error.message}`);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    const dropdown = document.getElementById('vm-dropdown');
    const refreshBtn = document.getElementById('refresh-btn');
    const tabBtns = document.querySelectorAll('.tab-btn');

    dropdown.addEventListener('change', async (e) => {
        const vmId = e.target.value;
        if (vmId) {
            const vm = state.vms.find(v => v.id == vmId);
            if (vm) {
                await selectVM(vm);
            }
        } else {
            deselectVM();
        }
    });

    refreshBtn.addEventListener('click', async () => {
        if (state.selectedVmId) {
            await fetchVMTelemetry();
        }
    });

    tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Remove active class from all tabs
            tabBtns.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));

            // Add active class to clicked tab
            e.target.classList.add('active');
            const tabId = e.target.getAttribute('data-tab');
            document.getElementById(tabId + '-tab').classList.add('active');
        });
    });
}

/**
 * Select a VM
 */
async function selectVM(vm) {
    state.selectedVmId = vm.id;
    state.selectedVmName = vm.name;
    state.metricsHistory = {};
    state.charts = {};

    console.log(`📊 Selected VM: ${vm.name} (ID: ${vm.id})`);

    // Update info text
    const infoText = document.getElementById('vm-info-text');
    infoText.textContent = `${vm.name} • ${vm.cpu_count} vCPU • ${Math.round((vm.memory_max || 0) / 1024 / 1024)}GB RAM • State: ${vm.state}`;

    // Show content area and hide loading
    document.getElementById('content-area').style.display = 'block';
    showLoadingState(false);
    showErrorState('');

    // Fetch initial telemetry
    await fetchVMTelemetry();

    // Start polling if not already running
    if (!state.pollingInterval) {
        state.pollingInterval = setInterval(async () => {
            if (state.selectedVmId) {
                await fetchVMTelemetry();
            }
        }, 5000); // Poll every 5 seconds
    }
}

/**
 * Deselect VM
 */
function deselectVM() {
    state.selectedVmId = null;
    state.selectedVmName = null;
    state.metricsHistory = {};

    // Hide content area
    document.getElementById('content-area').style.display = 'none';

    // Stop polling
    if (state.pollingInterval) {
        clearInterval(state.pollingInterval);
        state.pollingInterval = null;
    }

    // Update info text
    document.getElementById('vm-info-text').textContent = '';
}

/**
 * Fetch telemetry for selected VM
 */
async function fetchVMTelemetry() {
    if (!state.selectedVmId) return;

    try {
        const response = await fetch(`/api/telemetry/vm-stats/${state.selectedVmId}`);
        const data = await response.json();

        if (!response.ok) {
            console.error('❌ Error fetching telemetry:', data);
            return;
        }

        const metrics = data.metrics || {};
        console.log(`✓ Fetched telemetry for VM ${state.selectedVmId}`);

        // Update metrics
        updateMetrics(metrics);

        // Update summary
        updateSummary(metrics);

        // Update graphs
        updateGraphs(metrics);

    } catch (error) {
        console.error('❌ Error fetching telemetry:', error);
    }
}

/**
 * Update metric values in the UI
 */
function updateMetrics(metrics) {
    // Update all metric elements
    for (const [key, value] of Object.entries(metrics)) {
        const element = document.getElementById(`value-${key}`);
        if (element) {
            // Find metric definition
            let metricDef = null;
            for (const tab of Object.values(metricDefinitions)) {
                const found = tab.find(m => m.key === key);
                if (found) {
                    metricDef = found;
                    break;
                }
            }

            if (metricDef) {
                element.textContent = formatValue(value, metricDef.type, metricDef.unit);
            } else {
                element.textContent = formatValue(value, 'number');
            }
        }
    }
}

/**
 * Update summary panel
 */
function updateSummary(metrics) {
    const lastUpdate = new Date().toLocaleTimeString();

    document.getElementById('metric-state').textContent = metrics.state || '--';
    document.getElementById('metric-cpus').textContent = metrics.cpus || '--';
    document.getElementById('metric-cputime').textContent = formatValue(metrics.cputime, 'number', 'ns');
    document.getElementById('metric-last-update').textContent = lastUpdate;
}

/**
 * Update graphs with new data
 */
function updateGraphs(metrics) {
    // Initialize or update history
    const timestamp = new Date().toLocaleTimeString();

    for (const [key, value] of Object.entries(metrics)) {
        if (!state.metricsHistory[key]) {
            state.metricsHistory[key] = {
                labels: [],
                data: [],
            };
        }

        // Add new data point
        state.metricsHistory[key].labels.push(timestamp);
        state.metricsHistory[key].data.push(value || 0);

        // Keep only last N points
        if (state.metricsHistory[key].data.length > state.maxHistoryPoints) {
            state.metricsHistory[key].labels.shift();
            state.metricsHistory[key].data.shift();
        }

        // Create or update graph
        const canvasId = `graph-${key}`;
        const canvas = document.getElementById(canvasId);
        if (canvas) {
            createOrUpdateGraph(canvasId, state.metricsHistory[key], key);
        }
    }
}

/**
 * Create or update a metric graph
 */
function createOrUpdateGraph(canvasId, history, metricKey) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const chartKey = canvasId;

    // Determine chart color based on metric type
    let borderColor = '#4caf50';
    let backgroundColor = 'rgba(76, 175, 80, 0.1)';

    if (metricKey.includes('error') || metricKey.includes('drop') || metricKey.includes('fault')) {
        borderColor = '#ff9800';
        backgroundColor = 'rgba(255, 152, 0, 0.1)';
    }

    const chartConfig = {
        type: 'line',
        data: {
            labels: history.labels,
            datasets: [
                {
                    label: metricKey,
                    data: history.data,
                    borderColor: borderColor,
                    backgroundColor: backgroundColor,
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.1,
                    spanGaps: true,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: borderColor,
                    borderWidth: 1,
                }
            },
            scales: {
                x: {
                    display: false,
                },
                y: {
                    display: true,
                    ticks: {
                        color: '#888',
                        font: {
                            size: 10,
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                    }
                }
            }
        }
    };

    if (state.charts[chartKey]) {
        // Update existing chart
        state.charts[chartKey].data.labels = history.labels;
        state.charts[chartKey].data.datasets[0].data = history.data;
        state.charts[chartKey].update('none'); // No animation for smooth updates
    } else {
        // Create new chart
        state.charts[chartKey] = new Chart(ctx, chartConfig);
    }
}

/**
 * Show loading state
 */
function showLoadingState(show) {
    const loadingState = document.getElementById('loading-state');
    if (show) {
        loadingState.style.display = 'block';
    } else {
        loadingState.style.display = 'none';
    }
}

/**
 * Show error state
 */
function showErrorState(message) {
    const errorState = document.getElementById('error-state');
    const errorMessage = document.getElementById('error-message');

    if (message) {
        errorMessage.textContent = message;
        errorState.style.display = 'block';
    } else {
        errorState.style.display = 'none';
    }
}

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', () => {
    if (state.pollingInterval) {
        clearInterval(state.pollingInterval);
    }
});
