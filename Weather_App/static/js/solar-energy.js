// Solar Energy Page - JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initSolarChart();
    initProvinceButtons();
});

// Initialize Solar Radiation Chart
function initSolarChart() {
    const ctx = document.getElementById('solarChart');
    if (!ctx) return;

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'],
            datasets: [
                {
                    label: 'Bức xạ trực tiếp',
                    data: [0, 0, 0, 15, 120, 350, 680, 750, 850, 600, 200, 0],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointBackgroundColor: '#00d4ff',
                    pointBorderColor: '#051428',
                    pointBorderWidth: 2,
                    pointHoverRadius: 7,
                },
                {
                    label: 'Bức xạ khuếch tán',
                    data: [5, 5, 8, 25, 80, 150, 200, 220, 200, 150, 50, 10],
                    borderColor: '#1abc9c',
                    backgroundColor: 'rgba(26, 188, 156, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointBackgroundColor: '#1abc9c',
                    pointBorderColor: '#051428',
                    pointBorderWidth: 2,
                    pointHoverRadius: 7,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#b8d4e0',
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        padding: 20
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(5, 20, 40, 0.9)',
                    titleColor: '#00d4ff',
                    bodyColor: '#b8d4e0',
                    borderColor: '#00d4ff',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y + ' W/m²';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 1000,
                    grid: {
                        color: 'rgba(0, 212, 255, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#b8d4e0',
                        font: {
                            size: 11
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 212, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#b8d4e0',
                        font: {
                            size: 11
                        }
                    }
                }
            }
        }
    });

    return chart;
}

// Province Button Interaction
function initProvinceButtons() {
    const buttons = document.querySelectorAll('.province-btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            const province = this.textContent.trim();
            console.log('Selected province:', province);
            
            // Here you can add API call to fetch data for selected province
            updateSolarData(province);
        });
    });
}

// Update Solar Data for Selected Province
function updateSolarData(province) {
    // Simulated API call - replace with actual API endpoint
    console.log(`Fetching solar data for ${province}...`);
    
    // Example: You could call an API like this
    // fetch(`/api/weather/solar/?location=${province}`)
    //     .then(response => response.json())
    //     .then(data => {
    //         updateMetrics(data);
    //     })
    //     .catch(error => console.error('Error:', error));
}

// Update Metric Cards
function updateMetrics(data) {
    // This function would update the metric values based on API response
    // Example:
    // document.getElementById('solar-radiation-value').textContent = data.radiation;
    // document.getElementById('uv-index-value').textContent = data.uv_index;
}

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add animation on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'fadeInUp 0.6s ease-out forwards';
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe metric cards and forecast items
document.querySelectorAll('.metric-card, .forecast-item, .potential-card, .recommendation-item').forEach(el => {
    el.style.opacity = '0';
    observer.observe(el);
});

// Add fadeInUp animation keyframe
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);
