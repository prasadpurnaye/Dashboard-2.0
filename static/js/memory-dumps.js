// Memory Dumps Dashboard - JavaScript
// Handles dump triggers, VM management, and InfluxDB data display

class MemoryDumpManager {
    constructor() {
        this.vms = [];
        this.allDumps = [];
        this.filteredDumps = [];
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.autoRefreshInterval = null;
        this.selectedDumpForModal = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadInitialData();
    }

    initializeElements() {
        // Buttons
        this.dumpSelectedBtn = document.getElementById('dump-selected-btn');
        this.dumpAllBtn = document.getElementById('dump-all-btn');
        this.refreshTableBtn = document.getElementById('refresh-table-btn');
        this.exportCsvBtn = document.getElementById('export-csv-btn');
        this.resetFiltersBtn = document.getElementById('reset-filters-btn');
        this.prevPageBtn = document.getElementById('prev-page-btn');
        this.nextPageBtn = document.getElementById('next-page-btn');
        this.copyHashBtn = document.getElementById('copy-hash-btn');

        // Inputs
        this.vmSelect = document.getElementById('vm-select');
        this.searchFilter = document.getElementById('search-filter');
        this.dateFilter = document.getElementById('date-filter');
        this.autoRefreshCheck = document.getElementById('auto-refresh-check');
        this.showCompressedCheck = document.getElementById('show-compressed-check');

        // Display elements
        this.totalVmsDisplay = document.getElementById('total-vms');
        this.totalDumpsDisplay = document.getElementById('total-dumps');
        this.lastDumpTimeDisplay = document.getElementById('last-dump-time');
        this.dumpsTableBody = document.getElementById('dumps-tbody');
        this.recordCountValue = document.getElementById('record-count-value');
        this.pageInfo = document.getElementById('page-info');
        this.activityLog = document.getElementById('activity-log');
        this.activityCount = document.getElementById('activity-count');
        this.toastContainer = document.getElementById('toast-container');

        // Modal
        this.modal = document.getElementById('dump-details-modal');
        this.modalBody = document.getElementById('dump-details-body');
        this.modalCloseButtons = document.querySelectorAll('.modal-close, .modal-close-btn');
    }

    setupEventListeners() {
        // Dump actions
        this.dumpSelectedBtn.addEventListener('click', () => this.dumpSelectedVM());
        this.dumpAllBtn.addEventListener('click', () => this.dumpAllVMs());

        // Table actions
        this.refreshTableBtn.addEventListener('click', () => this.loadDumpsFromInfluxDB());
        this.exportCsvBtn.addEventListener('click', () => this.exportToCSV());

        // Filters
        this.resetFiltersBtn.addEventListener('click', () => this.resetFilters());
        this.searchFilter.addEventListener('input', () => this.applyFilters());
        this.dateFilter.addEventListener('input', () => this.applyFilters());
        this.autoRefreshCheck.addEventListener('change', (e) => this.handleAutoRefresh(e));

        // Pagination
        this.prevPageBtn.addEventListener('click', () => this.previousPage());
        this.nextPageBtn.addEventListener('click', () => this.nextPage());

        // VM Select
        this.vmSelect.addEventListener('change', (e) => this.toggleDumpSelectedBtn());

        // Modal
        this.modalCloseButtons.forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.closeModal();
        });
        this.copyHashBtn.addEventListener('click', () => this.copyHashToClipboard());

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModal();
        });
    }

    async loadInitialData() {
        console.log('📊 Loading initial data...');
        await this.loadVMs();
        await this.loadDumpsFromInfluxDB();
        this.updateStatusInfo();
        
        if (this.autoRefreshCheck.checked) {
            this.startAutoRefresh();
        }
    }

    async loadVMs() {
        try {
            const response = await fetch('/api/telemetry/live-vms');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.vms = data.vms || [];
            
            // Populate VM select dropdown
            const currentValue = this.vmSelect.value;
            const options = this.vmSelect.querySelectorAll('option:not(:first-child):not([value="all"])');
            options.forEach(opt => opt.remove());
            
            this.vms.forEach(vm => {
                const option = document.createElement('option');
                option.value = vm.id;
                option.textContent = `${vm.name} (${vm.id})`;
                this.vmSelect.appendChild(option);
            });
            
            this.vmSelect.value = currentValue;
            
            console.log(`✓ Loaded ${this.vms.length} VMs`);
            this.addActivityLog('Loaded VMs from libvirt', 'success', `Found ${this.vms.length} virtual machines`);
        } catch (error) {
            console.error('❌ Failed to load VMs:', error);
            this.addActivityLog('Failed to load VMs', 'error', error.message);
            this.showToast('Failed to load VMs', 'error');
        }
    }

    async loadDumpsFromInfluxDB() {
        console.log('📂 Loading dumps from InfluxDB3...');
        
        // Show loading state
        this.dumpsTableBody.innerHTML = `
            <tr class="loading-row">
                <td colspan="8" class="loading-cell">
                    <div class="spinner"></div>
                    Loading data from InfluxDB3...
                </td>
            </tr>
        `;
        
        try {
            const response = await fetch('/api/memory-dumps/records');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.allDumps = data.records || [];
            
            console.log(`✓ Loaded ${this.allDumps.length} dump records`);
            this.addActivityLog('Loaded dump records', 'success', `Retrieved ${this.allDumps.length} records from InfluxDB3`);
            
            this.applyFilters();
            this.updatePagination();
        } catch (error) {
            console.error('❌ Failed to load dumps:', error);
            this.addActivityLog('Failed to load dumps', 'error', error.message);
            this.showToast('Failed to load dumps from InfluxDB3', 'error');
            
            this.dumpsTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px; color: #f5576c;">
                        ❌ Error loading data: ${error.message}
                    </td>
                </tr>
            `;
        }
    }

    applyFilters() {
        const searchTerm = this.searchFilter.value.toLowerCase();
        const dateTerm = this.dateFilter.value;
        
        this.filteredDumps = this.allDumps.filter(dump => {
            const matchesSearch = !searchTerm || 
                dump.dom.toLowerCase().includes(searchTerm) ||
                dump.sha256.toLowerCase().includes(searchTerm) ||
                dump.vmid.toString().includes(searchTerm);
            
            const matchesDate = !dateTerm || 
                dump.timestamp.startsWith(dateTerm);
            
            return matchesSearch && matchesDate;
        });
        
        this.currentPage = 1;
        this.updatePagination();
        this.renderTable();
    }

    renderTable() {
        if (this.filteredDumps.length === 0) {
            this.dumpsTableBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px; color: #999;">
                        No dump records found.
                    </td>
                </tr>
            `;
            return;
        }

        const start = (this.currentPage - 1) * this.itemsPerPage;
        const end = start + this.itemsPerPage;
        const pageData = this.filteredDumps.slice(start, end);

        this.dumpsTableBody.innerHTML = pageData.map(dump => `
            <tr>
                <td>${this.escapeHtml(dump.vmid)}</td>
                <td>${this.escapeHtml(dump.dom)}</td>
                <td>${this.formatTimestamp(dump.timestamp)}</td>
                <td>${(dump.duration_sec || 0).toFixed(2)}</td>
                <td class="hash-cell" title="${dump.sha256}">
                    ${dump.sha256.substring(0, 16)}...
                </td>
                <td class="hash-cell" title="${dump.dump_path}">
                    ${this.getFilename(dump.dump_path)}
                </td>
                <td class="size-cell">${this.formatBytes(dump.gzip_size_bytes)}</td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn view-btn" onclick="dumpManager.viewDetails('${this.escapeAttr(JSON.stringify(dump))}')">
                            👁️ View
                        </button>
                        <button class="action-btn copy-btn" onclick="dumpManager.copyToClipboard('${this.escapeAttr(dump.sha256)}')">
                            📋 Copy
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        this.recordCountValue.textContent = this.filteredDumps.length;
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredDumps.length / this.itemsPerPage);
        this.pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
        
        this.prevPageBtn.disabled = this.currentPage <= 1;
        this.nextPageBtn.disabled = this.currentPage >= totalPages;
    }

    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.renderTable();
            window.scrollTo(0, document.querySelector('.table-section').offsetTop);
        }
    }

    nextPage() {
        const totalPages = Math.ceil(this.filteredDumps.length / this.itemsPerPage);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.renderTable();
            window.scrollTo(0, document.querySelector('.table-section').offsetTop);
        }
    }

    resetFilters() {
        this.searchFilter.value = '';
        this.dateFilter.value = '';
        this.applyFilters();
        console.log('🔄 Filters reset');
        this.showToast('Filters reset', 'info');
    }

    updateStatusInfo() {
        this.totalVmsDisplay.textContent = this.vms.length;
        this.totalDumpsDisplay.textContent = this.allDumps.length;
        
        if (this.allDumps.length > 0) {
            const sortedDumps = [...this.allDumps].sort((a, b) => 
                new Date(b.timestamp) - new Date(a.timestamp)
            );
            this.lastDumpTimeDisplay.textContent = this.formatTimestamp(sortedDumps[0].timestamp);
        } else {
            this.lastDumpTimeDisplay.textContent = 'Never';
        }
    }

    toggleDumpSelectedBtn() {
        const selected = this.vmSelect.value;
        this.dumpSelectedBtn.disabled = !selected || selected === 'all';
    }

    async dumpSelectedVM() {
        const vmId = this.vmSelect.value;
        if (!vmId || vmId === 'all') {
            this.showToast('Please select a VM', 'warning');
            return;
        }

        await this.triggerDump([vmId]);
    }

    async dumpAllVMs() {
        if (this.vms.length === 0) {
            this.showToast('No VMs available', 'warning');
            return;
        }

        const vmIds = this.vms.map(vm => vm.id);
        await this.triggerDump(vmIds);
    }

    async triggerDump(vmIds) {
        try {
            console.log(`💾 Triggering dump for VMs: ${vmIds.join(', ')}`);
            
            const response = await fetch('/api/memory-dumps/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ vm_ids: vmIds })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✓ Dump triggered:', data);
            
            this.addActivityLog('Dump triggered', 'success', 
                `Started dump for ${vmIds.length} VM(s)`);
            this.showToast(`Dump initiated for ${vmIds.length} VM(s)`, 'success');
            
            // Refresh table after a delay
            setTimeout(() => this.loadDumpsFromInfluxDB(), 2000);
        } catch (error) {
            console.error('❌ Failed to trigger dump:', error);
            this.addActivityLog('Dump failed', 'error', error.message);
            this.showToast(`Error: ${error.message}`, 'error');
        }
    }

    viewDetails(dumpJson) {
        try {
            const dump = JSON.parse(dumpJson);
            this.selectedDumpForModal = dump;

            this.modalBody.innerHTML = `
                <div class="detail-row">
                    <span class="detail-label">VM ID</span>
                    <span class="detail-value">${this.escapeHtml(dump.vmid)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">VM Name</span>
                    <span class="detail-value">${this.escapeHtml(dump.dom)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Timestamp</span>
                    <span class="detail-value">${this.formatTimestamp(dump.timestamp)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Duration</span>
                    <span class="detail-value">${(dump.duration_sec || 0).toFixed(2)} seconds</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">SHA256 Hash</span>
                    <span class="detail-value">${this.escapeHtml(dump.sha256)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Dump File Path</span>
                    <span class="detail-value">${this.escapeHtml(dump.dump_path)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Compressed Size</span>
                    <span class="detail-value">${this.formatBytes(dump.gzip_size_bytes)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">File Creation Time</span>
                    <span class="detail-value">${new Date(dump.ctime * 1000).toLocaleString()}</span>
                </div>
            `;

            this.modal.classList.add('active');
        } catch (error) {
            console.error('Error parsing dump details:', error);
            this.showToast('Error displaying details', 'error');
        }
    }

    closeModal() {
        this.modal.classList.remove('active');
        this.selectedDumpForModal = null;
    }

    copyHashToClipboard() {
        if (this.selectedDumpForModal) {
            this.copyToClipboard(this.selectedDumpForModal.sha256);
        }
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copied to clipboard', 'success');
        }).catch(err => {
            console.error('Copy failed:', err);
            this.showToast('Failed to copy', 'error');
        });
    }

    exportToCSV() {
        if (this.filteredDumps.length === 0) {
            this.showToast('No data to export', 'warning');
            return;
        }

        const headers = ['VM ID', 'VM Name', 'Timestamp', 'Duration (s)', 'SHA256 Hash', 'Dump Path', 'Size (Bytes)', 'File CTime', 'File MTime', 'File ATime'];
        const rows = this.filteredDumps.map(dump => [
            dump.vmid,
            dump.dom,
            dump.timestamp,
            dump.duration_sec,
            dump.sha256,
            dump.dump_path,
            dump.gzip_size_bytes,
            new Date(dump.ctime * 1000).toISOString(),
            new Date(dump.mtime * 1000).toISOString(),
            new Date(dump.atime * 1000).toISOString()
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        
        link.setAttribute('href', url);
        link.setAttribute('download', `memory-dumps-${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showToast('CSV exported successfully', 'success');
        this.addActivityLog('Export', 'success', `Exported ${this.filteredDumps.length} records to CSV`);
    }

    handleAutoRefresh(event) {
        if (event.target.checked) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    startAutoRefresh() {
        if (this.autoRefreshInterval) return;
        
        console.log('🔄 Starting auto-refresh (5s interval)');
        this.autoRefreshInterval = setInterval(() => {
            this.loadDumpsFromInfluxDB();
            this.updateStatusInfo();
        }, 5000);
        
        this.addActivityLog('Auto-refresh started', 'info', 'Updates every 5 seconds');
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            console.log('⏸️ Auto-refresh stopped');
            this.addActivityLog('Auto-refresh stopped', 'info', 'Manual refresh required');
        }
    }

    addActivityLog(title, type, message) {
        const time = new Date().toLocaleTimeString();
        const log = document.querySelector('.activity-log');
        
        if (log.querySelector('.activity-empty')) {
            log.innerHTML = '';
        }

        const activityItem = document.createElement('div');
        activityItem.className = `activity-item ${type}`;
        activityItem.innerHTML = `
            <span class="activity-time">${time}</span>
            <strong>${title}:</strong>
            <span class="activity-message">${message}</span>
        `;

        log.insertBefore(activityItem, log.firstChild);

        // Keep only last 20 items
        while (log.children.length > 20) {
            log.removeChild(log.lastChild);
        }

        // Update count
        const count = Math.min(log.children.length, 20);
        this.activityCount.textContent = count;
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        this.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    formatTimestamp(timestamp) {
        try {
            return new Date(timestamp).toLocaleString();
        } catch (e) {
            return timestamp;
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
    }

    getFilename(path) {
        return path.split('/').pop() || path;
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    escapeAttr(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/'/g, '&#39;')
            .replace(/"/g, '&quot;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }
}

// Initialize on page load
let dumpManager;
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Memory Dump Manager...');
    dumpManager = new MemoryDumpManager();
});
