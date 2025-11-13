// Store gauge chart instances
const gaugeCharts = {};
const gaugeValues = Array(8).fill(0);

// Create a gauge chart using Chart.js (180-degree half circle)
function createGaugeChart(gaugeId, initialValue = 0) {
    const ctx = document.getElementById(`gauge-${gaugeId}`).getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [
                {
                    data: [initialValue, 90 - initialValue],
                    backgroundColor: [
                        '#4caf50', // Green
                        '#fff'     // White
                    ],
                    borderColor: '#000',
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
            rotation: -90,
            circumference: 180,
            cutout: '75%'
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
                    
                    const text = `${gaugeValues[gaugeId - 1].toFixed(5)}°C`;
                    const textX = Math.round((width - chart.ctx.measureText(text).width) / 2);
                    const textY = height / 1.8;
                    
                    chart.ctx.fillStyle = '#000';
                    chart.ctx.fillText(text, textX, textY);
                    chart.ctx.save();
                }
            }
        ]
    });
    
    gaugeCharts[gaugeId] = chart;
    return chart;
}

// Determine color based on gauge value - only green
function getColorByValue(value) {
    return '#4caf50'; // Green only
}

// Update the status indicator border color - green only
function updateStatusIndicator(gaugeId, value) {
    const wrapper = document.getElementById(`gauge-wrapper-${gaugeId}`);
    wrapper.classList.remove('status-normal', 'status-warning', 'status-critical');
    wrapper.classList.add('status-normal'); // Always green
}

// Update gauge chart with new value
function updateGaugeChart(gaugeId, newValue) {
    if (gaugeCharts[gaugeId]) {
        gaugeValues[gaugeId - 1] = newValue;
        
        // Update chart data
        gaugeCharts[gaugeId].data.datasets[0].data = [newValue, 90 - newValue];
        gaugeCharts[gaugeId].data.datasets[0].backgroundColor = [
            '#4caf50', // Green
            '#fff'     // White
        ];
        gaugeCharts[gaugeId].update();
    }
    
    // Update text display
    const displayElement = document.getElementById(`gauge-value-${gaugeId}`);
    if (displayElement) {
        displayElement.innerText = `${newValue.toFixed(5)} °C`;
    }
    
    // Update status indicator
    updateStatusIndicator(gaugeId, newValue);
}

// Fetch gauge data from API
function fetchGaugeData() {
    fetch('/api/gauges')
        .then(response => response.json())
        .then(data => {
            data.gauges.forEach((gauge) => {
                const gaugeId = gauge.id;
                const value = gauge.value;
                
                if (value >= 0 && value <= 90) {
                    updateGaugeChart(gaugeId, value);
                }
            });
        })
        .catch(error => console.error('Error fetching gauge data:', error));
}

// Initialize all gauge charts
function initializeGauges() {
    for (let i = 1; i <= 8; i++) {
        createGaugeChart(i, 0);
        updateStatusIndicator(i, 0);
    }
    
    // Fetch initial data and set up interval for updates
    fetchGaugeData();
    setInterval(fetchGaugeData, 2000); // Update every 2 seconds
}

// Start initialization when DOM is ready
document.addEventListener('DOMContentLoaded', initializeGauges);