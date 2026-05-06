/* monitoring-core/app/dashboard/static/js/dashboard.js */
class DashboardManager {
    constructor() {
        this.refreshInterval = 30000; // 30 seconds
        this.charts = {};
        this.isAutoRefreshEnabled = true;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAutoRefresh();
        this.setupWebSocket();
    }

    setupEventListeners() {
        // Toggle auto-refresh
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.refreshData();
            }
        });

        // Page visibility change handler
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopAutoRefresh();
            } else {
                this.startAutoRefresh();
            }
        });
    }

    setupWebSocket() {
        // WebSocket for real-time updates (if implemented)
        if (window.WebSocket) {
            try {
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${wsProtocol}//${window.location.host}/ws/dashboard`;
                this.ws = new WebSocket(wsUrl);

                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleRealtimeUpdate(data);
                };

                this.ws.onerror = () => {
                    console.log('WebSocket connection failed, falling back to polling');
                };
            } catch (error) {
                console.log('WebSocket not available, using polling only');
            }
        }
    }

    handleRealtimeUpdate(data) {
        switch (data.type) {
            case 'log_update':
                this.updateLogCount(data.count);
                break;
            case 'anomaly_detected':
                this.showAnomalyAlert(data.anomaly);
                break;
            case 'service_status_change':
                this.updateServiceStatus(data.service, data.status);
                break;
        }
    }

    startAutoRefresh() {
        this.isAutoRefreshEnabled = true;
        this.autoRefreshTimer = setInterval(() => {
            if (this.isAutoRefreshEnabled) {
                this.refreshData();
            }
        }, this.refreshInterval);
    }

    stopAutoRefresh() {
        this.isAutoRefreshEnabled = false;
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
        }
    }

    async refreshData() {
        try {
            const response = await fetch('/dashboard/api/dashboard-data');
            const data = await response.json();

            if (data.error) {
                this.showError('Failed to refresh data: ' + data.error);
                return;
            }

            this.updateDashboard(data);
            this.updateLastRefreshTime();

        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    updateDashboard(data) {
        // Override in specific dashboard pages
        console.log('Dashboard data updated:', data);
    }

    updateLastRefreshTime() {
        const elements = document.querySelectorAll('#last-updated, .last-updated');
        elements.forEach(el => {
            el.textContent = new Date().toLocaleTimeString();
        });
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
        toast.style.cssText = `
            top: 20px; 
            right: 20px; 
            z-index: 9999; 
            min-width: 300px;
            animation: slideIn 0.3s ease;
        `;

        toast.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span><i class="fas fa-${this.getIconForType(type)} me-2"></i>${message}</span>
                <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }

    getIconForType(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'error': return 'exclamation-triangle';
            case 'warning': return 'exclamation-circle';
            default: return 'info-circle';
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDuration(ms) {
        if (ms < 1000) return ms + 'ms';
        if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
        if (ms < 3600000) return (ms / 60000).toFixed(1) + 'm';
        return (ms / 3600000).toFixed(1) + 'h';
    }

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }
}

// Chart utilities
class ChartManager {
    constructor() {
        this.charts = {};
        this.defaultColors = [
            '#667eea', '#764ba2', '#f093fb', '#f5576c',
            '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'
        ];
    }

    createLineChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId).getContext('2d');

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: { ...defaultOptions, ...options }
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    updateChart(canvasId, newData) {
        const chart = this.charts[canvasId];
        if (chart) {
            chart.data = newData;
            chart.update('none'); // No animation for real-time updates
        }
    }

    destroyChart(canvasId) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
            delete this.charts[canvasId];
        }
    }

    getColorPalette(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(this.defaultColors[i % this.defaultColors.length]);
        }
        return colors;
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}






// CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    .animate-fade-in {
        animation: fadeIn 0.3s ease;
    }
`;
document.head.appendChild(style);

// Initialize dashboard manager
const dashboardManager = new DashboardManager();
const chartManager = new ChartManager();

// Make available globally
window.dashboardManager = dashboardManager;
window.chartManager = chartManager;