// monitoring-core/app/dashboard/static/js/charts.js



class MonitoringCharts {
    constructor() {
        this.charts = {};
        this.colors = {
            primary: '#667eea',
            secondary: '#764ba2',
            success: '#28a745',
            warning: '#ffc107',
            danger: '#dc3545',
            info: '#17a2b8',
            light: '#f8f9fa',
            dark: '#343a40'
        };
        
        this.gradients = {};
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            family: 'Inter, sans-serif',
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        title: function(context) {
                            return context[0].label || '';
                        }
                    }
                }
            },
            elements: {
                point: {
                    radius: 4,
                    hoverRadius: 6
                },
                line: {
                    borderWidth: 2,
                    tension: 0.4
                }
            }
        };
    }

    createGradient(ctx, color1, color2) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color1);
        gradient.addColorStop(1, color2);
        return gradient;
    }

    createRequestVolumeChart(canvasId, data = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Create gradients
        const requestGradient = this.createGradient(ctx, this.colors.primary + '80', this.colors.primary + '20');
        const errorGradient = this.createGradient(ctx, this.colors.danger + '80', this.colors.danger + '20');
        
        const defaultData = {
            labels: this.generateTimeLabels(24),
            datasets: [{
                label: 'Total Requests',
                data: data?.requests || this.generateRandomData(24, 50, 200),
                borderColor: this.colors.primary,
                backgroundColor: requestGradient,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: this.colors.primary,
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }, {
                label: 'Error Requests',
                data: data?.errors || this.generateRandomData(24, 0, 20),
                borderColor: this.colors.danger,
                backgroundColor: errorGradient,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: this.colors.danger,
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        };

        const options = {
            ...this.defaultOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            family: 'Inter, sans-serif'
                        },
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        font: {
                            family: 'Inter, sans-serif'
                        }
                    }
                }
            },
            plugins: {
                ...this.defaultOptions.plugins,
                tooltip: {
                    ...this.defaultOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            return `${label}: ${value.toLocaleString()}`;
                        }
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false,
            }
        };

        const chart = new Chart(ctx, {
            type: 'line',
            data: defaultData,
            options: options
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    createResponseTimeChart(canvasId, data = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        const avgGradient = this.createGradient(ctx, this.colors.info + '60', this.colors.info + '10');
        const p95Gradient = this.createGradient(ctx, this.colors.warning + '60', this.colors.warning + '10');
        
        const defaultData = {
            labels: this.generateTimeLabels(24),
            datasets: [{
                label: 'Average Response Time',
                data: data?.avg || this.generateRandomData(24, 50, 300),
                borderColor: this.colors.info,
                backgroundColor: avgGradient,
                fill: true,
                tension: 0.4
            }, {
                label: 'P95 Response Time',
                data: data?.p95 || this.generateRandomData(24, 100, 500),
                borderColor: this.colors.warning,
                backgroundColor: p95Gradient,
                fill: true,
                tension: 0.4
            }]
        };

        const options = {
            ...this.defaultOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return value + 'ms';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Response Time (ms)',
                        font: {
                            family: 'Inter, sans-serif',
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    }
                }
            },
            plugins: {
                ...this.defaultOptions.plugins,
                tooltip: {
                    ...this.defaultOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y}ms`;
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, {
            type: 'line',
            data: defaultData,
            options: options
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    createServiceDistributionChart(canvasId, data = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        const defaultData = {
            labels: data?.labels || ['Note Service', 'User Service', 'Order Service', 'Payment Service'],
            datasets: [{
                data: data?.values || [45, 25, 20, 10],
                backgroundColor: [
                    this.colors.primary,
                    this.colors.success,
                    this.colors.warning,
                    this.colors.info,
                    this.colors.secondary,
                    this.colors.danger
                ],
                borderWidth: 0,
                hoverBorderWidth: 2,
                hoverBorderColor: '#fff'
            }]
        };

        const options = {
            ...this.defaultOptions,
            cutout: '60%',
            plugins: {
                ...this.defaultOptions.plugins,
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            family: 'Inter, sans-serif'
                        }
                    }
                },
                tooltip: {
                    ...this.defaultOptions.plugins.tooltip,
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
            data: defaultData,
            options: options
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    createErrorRateChart(canvasId, data = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        const values = data?.values || [2.1, 1.8, 3.2, 0.9, 4.1, 2.3, 1.5];
        const labels = data?.labels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        
        const defaultData = {
            labels: labels,
            datasets: [{
                label: 'Error Rate (%)',
                data: values,
                backgroundColor: values.map(val => 
                    val > 5 ? this.colors.danger : 
                    val > 2 ? this.colors.warning : 
                    this.colors.success
                ),
                borderColor: values.map(val => 
                    val > 5 ? this.colors.danger : 
                    val > 2 ? this.colors.warning : 
                    this.colors.success
                ),
                borderWidth: 2,
                borderRadius: 4,
                borderSkipped: false,
            }]
        };

        const options = {
            ...this.defaultOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    max: Math.max(...values) * 1.2,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Error Rate (%)',
                        font: {
                            family: 'Inter, sans-serif',
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                ...this.defaultOptions.plugins,
                legend: {
                    display: false
                },
                tooltip: {
                    ...this.defaultOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            return `Error Rate: ${context.parsed.y}%`;
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, {
            type: 'bar',
            data: defaultData,
            options: options
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    createSystemMetricsChart(canvasId, data = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        const cpuGradient = this.createGradient(ctx, this.colors.primary + '80', this.colors.primary + '20');
        const memoryGradient = this.createGradient(ctx, this.colors.success + '80', this.colors.success + '20');
        
        const defaultData = {
            labels: this.generateTimeLabels(24),
            datasets: [{
                label: 'CPU Usage (%)',
                data: data?.cpu || this.generateRandomData(24, 10, 80),
                borderColor: this.colors.primary,
                backgroundColor: cpuGradient,
                fill: true,
                tension: 0.4,
                yAxisID: 'y'
            }, {
                label: 'Memory Usage (%)',
                data: data?.memory || this.generateRandomData(24, 20, 90),
                borderColor: this.colors.success,
                backgroundColor: memoryGradient,
                fill: true,
                tension: 0.4,
                yAxisID: 'y'
            }]
        };

        const options = {
            ...this.defaultOptions,
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Usage (%)',
                        font: {
                            family: 'Inter, sans-serif',
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    }
                }
            }
        };

        const chart = new Chart(ctx, {
            type: 'line',
            data: defaultData,
            options: options
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    createAnomalyTimelineChart(canvasId, data = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        const anomalies = data?.anomalies || [
            { time: '2024-01-01T10:00:00Z', severity: 'critical', count: 3 },
            { time: '2024-01-01T14:00:00Z', severity: 'warning', count: 1 },
            { time: '2024-01-01T18:00:00Z', severity: 'high', count: 2 }
        ];
        
        const labels = anomalies.map(a => new Date(a.time).toLocaleTimeString());
        const values = anomalies.map(a => a.count);
        const colors = anomalies.map(a => {
            switch(a.severity) {
                case 'critical': return this.colors.danger;
                case 'high': return this.colors.warning;
                case 'medium': return this.colors.info;
                default: return this.colors.secondary;
            }
        });
        
        const defaultData = {
            labels: labels,
            datasets: [{
                label: 'Anomalies Detected',
                data: values,
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 2,
                pointRadius: 8,
                pointHoverRadius: 10
            }]
        };

        const options = {
            ...this.defaultOptions,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        stepSize: 1,
                        callback: function(value) {
                            return Number.isInteger(value) ? value : '';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Number of Anomalies',
                        font: {
                            family: 'Inter, sans-serif',
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    }
                }
            },
            plugins: {
                ...this.defaultOptions.plugins,
                tooltip: {
                    ...this.defaultOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const anomaly = anomalies[context.dataIndex];
                            return [
                                `Count: ${context.parsed.y}`,
                                `Severity: ${anomaly.severity}`,
                                `Time: ${new Date(anomaly.time).toLocaleString()}`
                            ];
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, {
            type: 'scatter',
            data: defaultData,
            options: options
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    createServiceHealthChart(canvasId, data = null) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        const services = data?.services || [
            { name: 'Note Service', health: 95 },
            { name: 'User Service', health: 88 },
            { name: 'Order Service', health: 76 },
            { name: 'Payment Service', health: 92 }
        ];
        
        const labels = services.map(s => s.name);
        const values = services.map(s => s.health);
        const colors = values.map(val => 
            val >= 90 ? this.colors.success :
            val >= 75 ? this.colors.warning :
            val >= 50 ? this.colors.danger :
            this.colors.dark
        );
        
        const defaultData = {
            labels: labels,
            datasets: [{
                label: 'Health Score',
                data: values,
                backgroundColor: colors,
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 4
            }]
        };

        const options = {
            ...this.defaultOptions,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                ...this.defaultOptions.plugins,
                legend: {
                    display: false
                },
                tooltip: {
                    ...this.defaultOptions.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            return `Health Score: ${context.parsed.x}%`;
                        }
                    }
                }
            }
        };

        const chart = new Chart(ctx, {
            type: 'bar',
            data: defaultData,
            options: options
        });

        this.charts[canvasId] = chart;
        return chart;
    }

    // Utility methods
    updateChart(canvasId, newData) {
        const chart = this.charts[canvasId];
        if (chart) {
            if (newData.labels) chart.data.labels = newData.labels;
            if (newData.datasets) {
                newData.datasets.forEach((dataset, index) => {
                    if (chart.data.datasets[index]) {
                        Object.assign(chart.data.datasets[index], dataset);
                    }
                });
            }
            chart.update('none'); // No animation for real-time updates
        }
    }

    updateChartData(canvasId, datasetIndex, newData) {
        const chart = this.charts[canvasId];
        if (chart && chart.data.datasets[datasetIndex]) {
            chart.data.datasets[datasetIndex].data = newData;
            chart.update('none');
        }
    }

    addDataPoint(canvasId, label, ...values) {
        const chart = this.charts[canvasId];
        if (chart) {
            chart.data.labels.push(label);
            values.forEach((value, index) => {
                if (chart.data.datasets[index]) {
                    chart.data.datasets[index].data.push(value);
                }
            });
            
            // Keep only last 50 points for performance
            if (chart.data.labels.length > 50) {
                chart.data.labels.shift();
                chart.data.datasets.forEach(dataset => {
                    dataset.data.shift();
                });
            }
            
            chart.update('none');
        }
    }

    destroyChart(canvasId) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
            delete this.charts[canvasId];
        }
    }

    destroyAllCharts() {
        Object.keys(this.charts).forEach(canvasId => {
            this.destroyChart(canvasId);
        });
    }

    resizeChart(canvasId) {
        const chart = this.charts[canvasId];
        if (chart) {
            chart.resize();
        }
    }

    resizeAllCharts() {
        Object.values(this.charts).forEach(chart => {
            chart.resize();
        });
    }

    // Data generation utilities
    generateTimeLabels(hours = 24, interval = 1) {
        const labels = [];
        const now = new Date();
        
        for (let i = hours - 1; i >= 0; i -= interval) {
            const time = new Date(now.getTime() - (i * 60 * 60 * 1000));
            labels.push(time.getHours().toString().padStart(2, '0') + ':00');
        }
        
        return labels;
    }

    generateRandomData(length, min = 0, max = 100) {
        return Array(length).fill(0).map(() => 
            Math.floor(Math.random() * (max - min + 1)) + min
        );
    }

    generateTrendData(length, start = 50, trend = 0.1, volatility = 5) {
        const data = [];
        let current = start;
        
        for (let i = 0; i < length; i++) {
            current += (Math.random() - 0.5) * volatility + trend;
            current = Math.max(0, current); // Ensure non-negative
            data.push(Math.round(current * 100) / 100);
        }
        
        return data;
    }

    getColorPalette(count) {
        const colors = Object.values(this.colors);
        const palette = [];
        
        for (let i = 0; i < count; i++) {
            palette.push(colors[i % colors.length]);
        }
        
        return palette;
    }

    // Animation utilities
    animateChart(canvasId, duration = 1000) {
        const chart = this.charts[canvasId];
        if (chart) {
            chart.update({
                duration: duration,
                easing: 'easeInOutQuart'
            });
        }
    }

    // Export utilities
    exportChartAsImage(canvasId, filename = 'chart.png') {
        const chart = this.charts[canvasId];
        if (chart) {
            const link = document.createElement('a');
            link.download = filename;
            link.href = chart.toBase64Image();
            link.click();
        }
    }

    // Theme utilities
    setDarkTheme() {
        Chart.defaults.color = '#e2e8f0';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
        Chart.defaults.backgroundColor = 'rgba(255, 255, 255, 0.1)';
        
        // Update existing charts
        Object.values(this.charts).forEach(chart => {
            chart.update();
        });
    }

    setLightTheme() {
        Chart.defaults.color = '#374151';
        Chart.defaults.borderColor = 'rgba(0, 0, 0, 0.1)';
        Chart.defaults.backgroundColor = 'rgba(0, 0, 0, 0.05)';
        
        // Update existing charts
        Object.values(this.charts).forEach(chart => {
            chart.update();
        });
    }
}

// Initialize and export
const monitoringCharts = new MonitoringCharts();

// Auto-resize charts on window resize
window.addEventListener('resize', () => {
    monitoringCharts.resizeAllCharts();
});

// Export for global use
window.MonitoringCharts = MonitoringCharts;
window.monitoringCharts = monitoringCharts;