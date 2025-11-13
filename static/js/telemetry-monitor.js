/**
 * Telemetry Monitoring Dashboard
 * Handles start/stop controls and status updates
 */

// Auto-refresh status every 2 seconds
let statusRefreshInterval = null;
let activityLog = [];
const MAX_LOG_ENTRIES = 50;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    addActivityLog('Telemetry dashboard loaded', 'info');
    refreshStatus();
    
    // Auto-refresh status every 2 seconds
    statusRefreshInterval = setInterval(refreshStatus, 2000);
});

/**
 * Start telemetry collection
 */
async function startTelemetry() {
    addActivityLog('Starting telemetry collection...', 'info');
    
    try {
        const response = await fetch('/api/telemetry/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (response.ok) {
            addActivityLog('✓ Telemetry started successfully', 'success');
            updateUI(data.details);
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-stop').disabled = false;
        } else {
            const errorMsg = data.detail || 'Unknown error';
            addActivityLog(`✗ Failed to start: ${errorMsg}`, 'error');
        }
    } catch (error) {
        const errorMsg = `Error: ${error.message}`;
        addActivityLog(`✗ ${errorMsg}`, 'error');
        console.error('Start error:', error);
    }
}

/**
 * Stop telemetry collection
 */
async function stopTelemetry() {
    addActivityLog('Stopping telemetry collection...', 'info');
    
    try {
        const response = await fetch('/api/telemetry/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (response.ok) {
            addActivityLog('✓ Telemetry stopped successfully', 'success');
            updateUI(data);
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-stop').disabled = true;
        } else {
            const errorMsg = data.detail || 'Unknown error';
            addActivityLog(`✗ Failed to stop: ${errorMsg}`, 'error');
        }
    } catch (error) {
        const errorMsg = `Error: ${error.message}`;
        addActivityLog(`✗ ${errorMsg}`, 'error');
        console.error('Stop error:', error);
    }
}

/**
 * Refresh telemetry status
 */
async function refreshStatus() {
    try {
        const response = await fetch('/api/telemetry/status');
        const data = await response.json();

        if (response.ok) {
            updateUI(data);
        } else {
            console.error('Failed to get status:', data);
        }
    } catch (error) {
        console.error('Status refresh error:', error);
    }
}

/**
 * Get and display monitored VMs
 */
async function getMonitoredVMs() {
    try {
        const response = await fetch('/api/telemetry/vms');
        const data = await response.json();

        if (response.ok) {
            displayVMs(data.vms || []);
        }
    } catch (error) {
        console.error('Error fetching VMs:', error);
    }
}

/**
 * Get and display configuration
 */
async function getConfiguration() {
    try {
        const response = await fetch('/api/telemetry/config');
        const data = await response.json();

        if (response.ok) {
            displayConfig(data.config || {});
        }
    } catch (error) {
        console.error('Error fetching config:', error);
    }
}

/**
 * Update UI with status information
 */
function updateUI(status) {
    // Update status indicator
    const statusIndicator = document.getElementById('status-indicator');
    const isRunning = status.running === true;
    
    statusIndicator.textContent = isRunning ? 'Running' : 'Stopped';
    statusIndicator.className = 'status-indicator ' + 
        (isRunning ? 'status-running' : 'status-stopped');

    // Update status values
    document.getElementById('status-value').textContent = isRunning ? 'Running' : 'Stopped';
    document.getElementById('running-value').textContent = isRunning ? 'Yes' : 'No';
    
    // Build message
    let message = isRunning ? '✓ Telemetry collection active' : 'Telemetry not running';
    document.getElementById('message-value').textContent = message;
    
    // Update statistics from API response
    // The API returns these fields directly (not in a statistics object)
    document.getElementById('collections-value').textContent = 
        status.total_collections || 0;
    
    // Use actual total metrics written from API
    document.getElementById('metrics-value').textContent = 
        status.total_metrics_written || 0;
    
    document.getElementById('vms-count-value').textContent = 
        status.vms_monitored || 0;
    
    document.getElementById('errors-value').textContent = 
        status.total_errors || 0;
    
    // Format last collection time
    if (status.last_collection_time) {
        try {
            const date = new Date(status.last_collection_time);
            const now = new Date();
            const diffMs = now - date;
            const diffSec = Math.floor(diffMs / 1000);
            
            if (diffSec < 60) {
                document.getElementById('last-collection-value').textContent = 
                    `${diffSec}s ago`;
            } else if (diffSec < 3600) {
                const minutes = Math.floor(diffSec / 60);
                document.getElementById('last-collection-value').textContent = 
                    `${minutes}m ago`;
            } else {
                document.getElementById('last-collection-value').textContent = 
                    date.toLocaleTimeString();
            }
        } catch (e) {
            document.getElementById('last-collection-value').textContent = 
                status.last_collection_time;
        }
    } else {
        document.getElementById('last-collection-value').textContent = 'Never';
    }

    // Update button states
    document.getElementById('btn-start').disabled = isRunning;
    document.getElementById('btn-stop').disabled = !isRunning;

    // Fetch VMs and config
    getMonitoredVMs();
    getConfiguration();
}

/**
 * Display monitored VMs
 */
function displayVMs(vms) {
    const vmsList = document.getElementById('vms-list');
    
    if (!vms || vms.length === 0) {
        vmsList.innerHTML = '<div class="empty-state">No VMs discovered yet. Start telemetry to discover VMs.</div>';
        return;
    }

    vmsList.innerHTML = vms.map(vm => `
        <div class="vm-item">
            <div class="vm-item-name">${escapeHtml(vm.name || vm.id || 'Unknown')}</div>
            <div class="vm-item-info">ID: ${escapeHtml(vm.id || '-')}</div>
            <div class="vm-item-info">Arch: ${escapeHtml(vm.arch || '-')}</div>
            <div class="vm-item-info">Memory: ${vm.max_mem ? formatBytes(vm.max_mem) : '-'}</div>
            <div class="vm-item-info">vCPUs: ${vm.vcpu_count || '-'}</div>
            <span class="vm-item-status ${vm.state === 'running' ? 'running' : 'stopped'}">
                ${escapeHtml((vm.state || 'unknown').toUpperCase())}
            </span>
        </div>
    `).join('');
}

/**
 * Display configuration
 */
function displayConfig(config) {
    document.getElementById('config-libvirt').textContent = 
        config.libvirt_uri || 'Not configured';
    document.getElementById('config-influx').textContent = 
        config.influx_url || 'Not configured';
    document.getElementById('config-db').textContent = 
        config.influx_db || 'Not configured';
    document.getElementById('config-poll').textContent = 
        config.poll_interval ? `${config.poll_interval}s` : 'Not configured';
}

/**
 * Add entry to activity log
 */
function addActivityLog(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const entry = {
        timestamp,
        message,
        type
    };
    
    activityLog.unshift(entry);
    if (activityLog.length > MAX_LOG_ENTRIES) {
        activityLog.pop();
    }

    renderActivityLog();
}

/**
 * Render activity log
 */
function renderActivityLog() {
    const activityElement = document.getElementById('activity-log');
    
    activityElement.innerHTML = activityLog.map(entry => `
        <div class="activity-item activity-${entry.type}">
            <span class="log-timestamp">[${entry.timestamp}]</span>
            ${escapeHtml(entry.message)}
        </div>
    `).join('');

    // Auto-scroll to bottom
    activityElement.scrollTop = activityElement.scrollHeight;
}

/**
 * Clear activity log
 */
function clearActivityLog() {
    activityLog = [];
    renderActivityLog();
    addActivityLog('Activity log cleared', 'info');
}

/**
 * Utility: Escape HTML special characters
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Utility: Format bytes to human-readable format
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', function() {
    if (statusRefreshInterval) {
        clearInterval(statusRefreshInterval);
    }
});
