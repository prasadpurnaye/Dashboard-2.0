/**
 * Main Gauges Dashboard - Rate-of-Change Based Monitoring
 * 
 * This dashboard displays 8 gauges that show the rate of change for various VM metrics.
 * Each gauge angle is calculated using: atan((newValue - oldValue) / timeDelta) * 180 / π
 * 
 * Features:
 * - VM dropdown for live VM selection
 * - Real telemetry data from backend API
 * - Rate-of-change angle calculations
 * - Previous value tracking for accurate rate computation
 */

// ============================================================================
// GAUGE CONFIGURATION - Maps gauge ID to telemetry field and calculation type
// ============================================================================

const GAUGE_CONFIG = {
    1: {
        title: 'Network RX Rate',
        field: 'net_rxbytes',
        type: 'rate-of-change',
        unit: 'bytes/s'
    },
    2: {
        title: 'Network TX Rate',
        field: 'net_txbytes',
        type: 'rate-of-change',
        unit: 'bytes/s'
    },
    3: {
        title: 'Disk Read Rate',
        field: 'disk_rd_bytes',
        type: 'rate-of-change',
        unit: 'bytes/s'
    },
    4: {
        title: 'Disk Write Rate',
        field: 'disk_wr_bytes',
        type: 'rate-of-change',
        unit: 'bytes/s'
    },
    5: {
        title: 'CPU User Time Rate',
        field: 'timeusr',
        type: 'rate-of-change',
        unit: 'ns/s'
    },
    6: {
        title: 'CPU System Time Rate',
        field: 'timesys',
        type: 'rate-of-change',
        unit: 'ns/s'
    },
    7: {
        title: 'Memory RSS Rate',
        field: 'memrss',
        type: 'rate-of-change',
        unit: 'bytes/s'
    },
    8: {
        title: 'Disk Read Requests Rate',
        field: 'disk_rd_req',
        type: 'rate-of-change',
        unit: 'reqs/s'
    }
};

// ============================================================================
// STATE MANAGEMENT - Stores gauge instances, previous values, and current VM
// ============================================================================

const STATE = {
    gaugeCharts: {},                    // Chart.js instances for each gauge
    currentVmId: null,                  // Selected VM ID
    previousValues: {},                 // Previous metric values per VM
    lastUpdateTime: {},                 // Last update timestamp per VM
    updateInterval: null,               // Update interval ID
    vms: []                             // Available VMs list
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Calculate rate of change using arctangent formula with adaptive scaling
 * 
 * The formula accounts for very large metric values (millions) by:
 * 1. Computing the delta (change) between values
 * 2. Normalizing by time to get rate per second
 * 3. Using log-scaled arctangent for better visual distribution
 * 4. Mapping result to 0-90 degree gauge range
 * 
 * @param {number} newValue - Current metric value
 * @param {number} oldValue - Previous metric value
 * @param {number} timeDeltaMs - Time difference in milliseconds
 * @returns {number} Rate in degrees (0-90 range)
 */
function calculateRateOfChange(newValue, oldValue, timeDeltaMs) {
    // If no previous value or no time delta, return neutral angle
    if (oldValue === undefined || timeDeltaMs === 0) {
        return 0;
    }
    
    // Convert time delta to seconds (typically 2 seconds for our periodic updates)
    const timeDeltaSeconds = timeDeltaMs / 1000;
    
    // Calculate absolute change in value
    const valueDelta = Math.abs(newValue - oldValue);
    
    // Calculate rate: change per second
    const ratePerSecond = valueDelta / timeDeltaSeconds;
    
    // Use logarithmic scaling for better distribution across 0-90° range
    // This prevents huge values from maxing out the gauge
    // log10 compression: log10(1) = 0, log10(10) = 1, log10(100) = 2, etc.
    // Then map to 0-90 range using arctangent
    const logRate = Math.log10(Math.max(1, ratePerSecond)); // Avoid log(0)
    
    // Apply arctangent to the log-scaled rate for smooth 0-90 mapping
    const normalizedLog = logRate / 5;
    const rateInRadians = Math.atan(normalizedLog); // Normalize log scale
    const rateInDegrees = rateInRadians * 180 / Math.PI;
    
    // Clamp to 0-90 range and ensure we get meaningful values
    const clampedDegrees = Math.max(0, Math.min(90, rateInDegrees));
    
    // Detailed arctangent calculation logging
    console.debug(`
    ┌─ ARCTANGENT CALCULATION DETAILS ─────────────────────────┐
    │ Raw Delta:           ${valueDelta.toLocaleString()} units
    │ Time Delta:          ${timeDeltaSeconds.toFixed(2)} seconds
    │ Rate/Second:         ${ratePerSecond.toLocaleString()} units/sec
    │ Log10(Rate):         ${logRate.toFixed(4)}
    │ Normalized:          ${logRate.toFixed(4)} / 5 = ${normalizedLog.toFixed(4)}
    │ atan(${normalizedLog.toFixed(4)}):       ${rateInRadians.toFixed(4)} radians
    │ × 180/π:             ${rateInDegrees.toFixed(4)}°
    │ Clamped 0-90:        ${clampedDegrees.toFixed(2)}°
    └──────────────────────────────────────────────────────────┘
    `);
    console.log("clampedDegrees", clampedDegrees);
    return clampedDegrees;
}

/**
 * Initialize or load VM previous values storage
 * @param {string} vmId - VM identifier
 */
function initializePreviousValues(vmId) {
    if (!STATE.previousValues[vmId]) {
        STATE.previousValues[vmId] = {};
        STATE.lastUpdateTime[vmId] = Date.now();
    }
}

/**
 * Store current values as previous for next update
 * @param {string} vmId - VM identifier
 * @param {object} metrics - Current metrics object
 */
function storePreviousValues(vmId, metrics) {
    const gaugeIds = Object.keys(GAUGE_CONFIG);
    
    gaugeIds.forEach(gaugeId => {
        const field = GAUGE_CONFIG[gaugeId].field;
        if (metrics[field] !== undefined) {
            STATE.previousValues[vmId][field] = metrics[field];
        }
    });
    
    STATE.lastUpdateTime[vmId] = Date.now();
}

// ============================================================================
// GAUGE CREATION & RENDERING
// ============================================================================

/**
 * Create a gauge chart using Chart.js (180-degree half circle)
 * @param {number} gaugeId - Gauge identifier (1-8)
 * @param {number} initialValue - Initial angle value (0-90)
 */
function createGaugeChart(gaugeId, initialValue = 0) {
    const ctx = document.getElementById(`gauge-${gaugeId}`).getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [
                {
                    data: [initialValue, 90 - initialValue],
                    backgroundColor: [
                        '#4caf50', // Green for active portion
                        '#f0f0f0'  // Light gray for inactive portion
                    ],
                    borderColor: '#333',
                    borderWidth: 2,
                    borderRadius: 5
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
            rotation: -90,           // Start at top
            circumference: 180,      // 180-degree gauge
            cutout: '75%'            // Donut hole size
        },
        plugins: [
            {
                id: 'textCenter',
                beforeDraw(chart) {
                    const { width } = chart;
                    const { height } = chart.ctx.canvas;
                    chart.ctx.restore();
                    const fontSize = (height / 140).toFixed(2);
                    chart.ctx.font = `${fontSize}em sans-serif`;
                    chart.ctx.textBaseline = 'middle';
                    
                    // Display the angle value in the center
                    const gaugeId = parseInt(chart.canvas.id.split('-')[1]);
                    const value = chart.data.datasets[0].data[0];
                    const text = `${value.toFixed(2)}°`;
                    
                    const textX = Math.round((width - chart.ctx.measureText(text).width) / 2);
                    const textY = height / 1.8;
                    
                    chart.ctx.fillStyle = '#333';
                    chart.ctx.fillText(text, textX, textY);
                    chart.ctx.save();
                }
            }
        ]
    });
    
    STATE.gaugeCharts[gaugeId] = chart;
    return chart;
}

/**
 * Update gauge chart with new rate-based angle
 * @param {number} gaugeId - Gauge identifier (1-8)
 * @param {number} newAngle - New angle value (0-90)
 */
function updateGaugeChart(gaugeId, newAngle) {
    if (!STATE.gaugeCharts[gaugeId]) {
        console.warn(`Gauge ${gaugeId} chart not found`);
        return;
    }
    
    // Clamp angle to 0-90 range
    const clampedAngle = Math.max(0, Math.min(90, newAngle));
    
    // Update chart data
    STATE.gaugeCharts[gaugeId].data.datasets[0].data = [clampedAngle, 90 - clampedAngle];
    STATE.gaugeCharts[gaugeId].update();
    
    // Update text display
    const displayElement = document.getElementById(`gauge-value-${gaugeId}`);
    if (displayElement) {
        const config = GAUGE_CONFIG[gaugeId];
        displayElement.innerText = `${clampedAngle.toFixed(2)}° (rate)`;
    }
}

// ============================================================================
// VM SELECTION & DROPDOWN MANAGEMENT
// ============================================================================

/**
 * Fetch list of available VMs from backend
 */
async function fetchAvailableVms() {
    try {
        console.log('🔍 Fetching available VMs from /api/telemetry/live-vms...');
        const response = await fetch('/api/telemetry/live-vms');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        STATE.vms = data.vms || [];
        
        console.log(`✓ API Response: ${STATE.vms.length} VMs received`, STATE.vms);
        
        updateVmDropdown();
        console.log(`✓ Loaded ${STATE.vms.length} VMs into dropdown`);
    } catch (error) {
        console.error('❌ Error fetching VMs:', error);
        updateVmDropdown([]);
    }
}

/**
 * Update the VM dropdown options
 */
function updateVmDropdown() {
    const dropdown = document.getElementById('vm-dropdown');
    
    if (!dropdown) {
        console.error('❌ Dropdown element not found with ID "vm-dropdown"');
        return;
    }
    
    console.log(`📋 Updating dropdown with ${STATE.vms.length} VMs`);
    
    // Clear existing options
    dropdown.innerHTML = '<option value="">-- Select a VM --</option>';
    
    // Add VM options
    STATE.vms.forEach(vm => {
        console.log(`  Adding VM: ${vm.name} (ID: ${vm.id})`);
        const option = document.createElement('option');
        option.value = vm.id;
        option.textContent = `${vm.name} (ID: ${vm.id})`;
        dropdown.appendChild(option);
    });
    
    // If we have VMs, select the first one
    if (STATE.vms.length > 0) {
        console.log(`✓ Auto-selecting first VM: ${STATE.vms[0].name}`);
        dropdown.value = STATE.vms[0].id;
        selectVm(STATE.vms[0].id);
    } else {
        console.warn('⚠ No VMs available to select');
    }
}

/**
 * Handle VM selection change
 * @param {string} vmId - Selected VM ID
 */
function selectVm(vmId) {
    if (!vmId) {
        console.log('No VM selected');
        return;
    }
    
    console.log(`✓ Selected VM: ${vmId}`);
    STATE.currentVmId = vmId;
    
    // Initialize previous values for this VM
    initializePreviousValues(vmId);
    
    // Fetch initial telemetry for selected VM
    fetchAndUpdateGauges();
}

// ============================================================================
// TELEMETRY FETCHING & GAUGE UPDATES
// ============================================================================

/**
 * Fetch telemetry for the selected VM and update gauges with rate-of-change angles
 */
async function fetchAndUpdateGauges() {
    if (!STATE.currentVmId) {
        console.debug('No VM selected, skipping gauge update');
        return;
    }
    
    try {
        // Show loading indicator
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'inline';
        }
        
        // Fetch telemetry for the selected VM
        const url = `/api/telemetry/vm-stats/${STATE.currentVmId}`;
        console.log(`📊 Fetching telemetry from: ${url}`);
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        const metrics = data.metrics;
        
        console.log(`✓ Received metrics for VM ${STATE.currentVmId}`);
        console.log(`  Real data verification - Sample values:`);
        console.log(`    net_rxbytes: ${metrics.net_rxbytes} (expected: large number)`);
        console.log(`    disk_rd_bytes: ${metrics.disk_rd_bytes} (expected: large number)`);
        console.log(`    timeusr: ${metrics.timeusr} (expected: large number)`);
        
        // Check if this is the first update for this VM (no previous values stored yet)
        const isFirstUpdate = Object.keys(STATE.previousValues[STATE.currentVmId] || {}).length === 0;
        
        if (isFirstUpdate) {
            console.log(`📌 First update for VM ${STATE.currentVmId} - storing initial values, gauges will show 0° until next update`);
            
            // Show the baseline metrics being stored
            console.group(`%c📦 Baseline Metrics Stored (will be used for rate calculation)`, 'color: #ff9800; font-weight: bold;');
            
            const baselineData = [];
            Object.keys(GAUGE_CONFIG).forEach(gaugeId => {
                const config = GAUGE_CONFIG[gaugeId];
                const field = config.field;
                const value = metrics[field];
                
                if (value !== undefined) {
                    baselineData.push({
                        'Gauge #': gaugeId,
                        'Metric': config.title,
                        'Field': field,
                        'Baseline Value': value.toLocaleString(),
                        'Unit': config.unit
                    });
                }
            });
            
            console.table(baselineData);
            console.log('%cℹ️  These baseline values will be used to calculate rates in the next update cycle', 'color: #666; font-style: italic;');
            console.groupEnd();
            
            // On first update, just store the values without calculating rates
            storePreviousValues(STATE.currentVmId, metrics);
            // Set all gauges to 0° since we have no previous data to compare
            for (let i = 1; i <= 8; i++) {
                updateGaugeChart(i, 0);
            }
        } else {
            // On subsequent updates, calculate and display rate-of-change angles
            console.log(`✓ Update #2+ for VM ${STATE.currentVmId} - calculating rates`);
            
            // Build table data for console output
            const tableData = [];
            
            Object.keys(GAUGE_CONFIG).forEach(gaugeId => {
                const config = GAUGE_CONFIG[gaugeId];
                const field = config.field;
                const currentValue = metrics[field];
                
                if (currentValue === undefined) {
                    console.warn(`⚠ Field ${field} not found in metrics for gauge ${gaugeId}`);
                    return;
                }
                
                // Get previous value and time
                const previousValue = STATE.previousValues[STATE.currentVmId][field];
                const previousTime = STATE.lastUpdateTime[STATE.currentVmId];
                const currentTime = Date.now();
                const timeDelta = currentTime - previousTime;
                
                // Calculate rate-of-change angle
                const angleInDegrees = calculateRateOfChange(currentValue, previousValue, timeDelta);
                
                // Update the gauge with the rate-based angle
                updateGaugeChart(gaugeId, angleInDegrees);
                
                // Prepare data for table
                const delta = currentValue - previousValue;
                const ratePerSecond = (delta / (timeDelta / 1000)).toFixed(2);
                
                tableData.push({
                    'Gauge #': gaugeId,
                    'Metric': config.title,
                    'Field': field,
                    'Previous Value': previousValue.toLocaleString(),
                    'Current Value': currentValue.toLocaleString(),
                    'Delta': delta.toLocaleString(),
                    'Rate/sec': ratePerSecond,
                    'Time (ms)': timeDelta,
                    'Angle (°)': angleInDegrees.toFixed(2)
                });
            });
            
            // Print table to console
            console.log('%c═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════', 'color: #4caf50; font-weight: bold;');
            console.log('%c📊 GAUGE VALUES & CALCULATED ANGLES (Main Gauge Monitoring)', 'color: #4caf50; font-weight: bold; font-size: 14px;');
            console.log('%c═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════', 'color: #4caf50; font-weight: bold;');
            console.table(tableData);
            console.log('%c═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════', 'color: #4caf50; font-weight: bold;');
            
            // Special focus on Network RX (Gauge 1)
            const networkRxRow = tableData.find(row => row['Gauge #'] === '1');
            if (networkRxRow) {
                console.log('%c🌐 NETWORK RX DETAILED BREAKDOWN 🌐', 'color: #2196F3; font-weight: bold; font-size: 13px; background: #e3f2fd; padding: 5px;');
                console.log(`%c┌─ Network Receive (RX) Bytes ─────────────────┐`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│ Metric Field:     net_rxbytes                 │`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│ Previous Value:   ${networkRxRow['Previous Value'].padEnd(32)}│`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│ Current Value:    ${networkRxRow['Current Value'].padEnd(32)}│`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│ Change (Delta):   ${networkRxRow['Delta'].padEnd(32)}│`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│ Time Interval:    ${String(networkRxRow['Time (ms)']).padEnd(32)}ms│`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│ Rate per Second:  ${String(networkRxRow['Rate/sec']).padEnd(32)}│`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│                                               │`, 'color: #2196F3; font-family: monospace;');
                console.log(`%c│ ✓ CALCULATED ANGLE: ${String(networkRxRow['Angle (°)']).padEnd(26)}°│`, 'color: #FF6F00; font-family: monospace; font-weight: bold;');
                console.log(`%c└───────────────────────────────────────────────┘`, 'color: #2196F3; font-family: monospace;');
            }
            
            // Also log individual gauge details for reference
            console.group('📋 Individual Gauge Details');
            tableData.forEach(row => {
                const emoji = row['Gauge #'] === '1' ? '🌐' : '📊';
                console.log(
                    `%c${emoji} [Gauge ${row['Gauge #']}] ${row['Metric']}`,
                    'color: #667eea; font-weight: bold;'
                );
                console.log(`  Previous: ${row['Previous Value']}`);
                console.log(`  Current:  ${row['Current Value']}`);
                console.log(`  Delta:    ${row['Delta']}`);
                console.log(`  Rate:     ${row['Rate/sec']} per second`);
                console.log(`  ▼ Angle:  ${row['Angle (°)']}° ▼`);
            });
            console.groupEnd();
            
            // Store current values as previous for next update
            storePreviousValues(STATE.currentVmId, metrics);
        }
        
        // Hide loading indicator
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        
    } catch (error) {
        console.error('❌ Error fetching/updating gauges:', error);
        console.error('Stack trace:', error.stack);
        
        // Hide loading indicator
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize all gauge charts and set up event listeners
 */
function initializeGauges() {
    console.log('🚀 Initializing Main Gauges Dashboard...');
    
    // Create gauge charts
    console.log('📊 Creating 8 gauge charts...');
    for (let i = 1; i <= 8; i++) {
        createGaugeChart(i, 0);
        console.log(`  ✓ Gauge ${i} created`);
    }
    
    // Set up VM dropdown listener
    const dropdown = document.getElementById('vm-dropdown');
    if (dropdown) {
        console.log('✓ VM dropdown found, attaching change listener');
        dropdown.addEventListener('change', (e) => {
            console.log(`📌 Dropdown changed to: ${e.target.value}`);
            selectVm(e.target.value);
        });
    } else {
        console.error('❌ VM dropdown not found! ID: "vm-dropdown"');
    }
    
    // Fetch available VMs and populate dropdown
    console.log('🔄 Fetching available VMs...');
    fetchAvailableVms();
    
    // Set up periodic updates (every 5 seconds)
    console.log('⏱️ Starting periodic updates every 5 seconds...');
    STATE.updateInterval = setInterval(() => {
        console.log('🔄 Periodic update tick...');
        fetchAndUpdateGauges();
    }, 6000);
    
    console.log('✓ Main Gauges Dashboard initialized');
}

// Start initialization when DOM is ready
document.addEventListener('DOMContentLoaded', initializeGauges);