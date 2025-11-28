// Chờ cho toàn bộ HTML tải xong mới chạy
document.addEventListener('DOMContentLoaded', () => {
    // Dữ liệu giả lập (thay cho dữ liệu thật từ API)
    const fakeApiData = [
        { time: "01:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "02:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "03:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "04:00 PM", temp: "17°/18°", humidity: 95, desc: "Có mưa", icon: "/static/image/mayden.png" },
        { time: "05:00 PM", temp: "17°/17°", humidity: 95, desc: "Có mưa", icon: "/static/image/mayden.png" },
        { time: "06:00 PM", temp: "17°/17°", humidity: 96, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "07:00 PM", temp: "16°/17°", humidity: 96, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "08:00 PM", temp: "16°/16°", humidity: 97, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "09:00 PM", temp: "16°/16°", humidity: 97, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "10:00 PM", temp: "15°/16°", humidity: 98, desc: "Trời quang", icon: "/static/image/mayden.png" },
        { time: "11:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "12:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "13:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "14:00 PM", temp: "17°/18°", humidity: 95, desc: "Có mưa", icon: "/static/image/mayden.png" },
        { time: "15:00 PM", temp: "17°/17°", humidity: 95, desc: "Có mưa", icon: "/static/image/mayden.png" },
        { time: "16:00 PM", temp: "17°/17°", humidity: 96, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "17:00 PM", temp: "16°/17°", humidity: 96, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "18:00 PM", temp: "16°/16°", humidity: 97, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "19:00 PM", temp: "16°/16°", humidity: 97, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "20:00 PM", temp: "15°/16°", humidity: 98, desc: "Trời quang", icon: "/static/image/mayden.png" },
        { time: "21:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "22:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "23:00 PM", temp: "18°/18°", humidity: 94, desc: "Mây đen u ám", icon: "/static/image/mayden.png" },
        { time: "24:00 PM", temp: "17°/18°", humidity: 95, desc: "Có mưa", icon: "/static/image/mayden.png" },
    ];

    // 1. Lấy container từ HTML bằng ID
    const container = document.getElementById("hourly-forecast-container");

    // 2. Lặp qua mảng dữ liệu
    fakeApiData.forEach(forecast => {

        // 3. Tạo một chuỗi HTML cho mỗi item
        const itemHTML = `
            <div class="hourly-item">
               <p class="hourly-time">${forecast.time}</p>
               <img class="hourly-icon" src="${forecast.icon}" alt="${forecast.desc}">
               <p class="hourly-temp">${forecast.temp}</p>
               <span class="hourly-humidity"><i class="fa-solid fa-droplet"></i> ${forecast.humidity}%</span>
               <p class="hourly-desc">${forecast.desc}</p>
            </div>
        `;

        // 4. Chèn chuỗi HTML vừa tạo vào cuối container
        container.insertAdjacentHTML("beforeend", itemHTML);
    });
    // //////////////////////////////////////////////////////////////////////////////
    // Đăng ký plugin datalabels cho tất cả biểu đồ
    Chart.register(ChartDataLabels);

    // ==========================================================
    // DỮ LIỆU VÀ HÀM VẼ BIỂU ĐỒ 1 (12H TỚI)
    // ==========================================================
    const hourlyLabels = ['16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00', '01:00', '02:00', '03:00'];
    const hourlyTemps = [27, 25, 24, 23, 20, 21, 21, 21, 21, 21, 21, 20];
    const hourlyRain = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];

    drawHourlyChart(hourlyLabels, hourlyTemps, hourlyRain);

    // ==========================================================
    // DỮ LIỆU VÀ HÀM VẼ BIỂU ĐỒ 2 (NGÀY TỚI)
    // ==========================================================
    const dailyLabels = ['CN 16', 'T2 17', 'T3 18', 'T4 19', 'T5 20', 'T6 21', 'T7 22'];
    const dailyTemps = [24, 22, 17, 13, 18, 17, 19];
    const dailyRain = [0, 98, 100, 96, 0, 0, 0];

    drawDailyWeatherChart(dailyLabels, dailyTemps, dailyRain);

    // ==========================================================
    // DỮ LIỆU VÀ HÀM VẼ BIỂU ĐỒ 3 (LƯỢNG MƯA)
    // ==========================================================
    const dailyRainLabels = ['CN 16', 'T2 17', 'T3 18', 'T4 19', 'T5 20', 'T6 21', 'T7 22'];
    const dailyRainAmounts = [0, 1.51, 11.99, 0.23, 0, 0, 0]; // Dùng 0 cho các ngày không có dữ liệu

    drawDailyRainChart(dailyRainLabels, dailyRainAmounts);
});

// ==========================================================
// HÀM VẼ BIỂU ĐỒ 1: #hourlyChart
// ==========================================================
function drawHourlyChart(labels, tempData, rainData) {
    const ctx = document.getElementById('hourlyChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Nhiệt độ',
                    data: tempData,
                    borderColor: '#22c55e', // Xanh lá
                    backgroundColor: '#22c55e',
                    tension: 0.1,
                    datalabels: {
                        color: '#22c55e',
                        align: 'top',
                        font: { weight: 'bold', size: 13 },
                        formatter: (value) => value + '°'
                    }
                },
                {
                    label: 'Khả năng có mưa',
                    data: rainData,
                    borderColor: '#f97316', // Cam
                    backgroundColor: '#f97316',
                    tension: 0.1,
                    datalabels: {
                        color: '#333',
                        align: 'top',
                        font: { weight: 'bold', size: 13 },
                        formatter: (value) => value + '%'
                    }
                }
            ]
        },
        options: sharedLineChartOptions() // Dùng chung options
    });
}

// ==========================================================
// HÀM VẼ BIỂU ĐỒ 2: #dailyWeatherChart
// ==========================================================
function drawDailyWeatherChart(labels, tempData, rainData) {
    const ctx = document.getElementById('dailyWeatherChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Nhiệt độ',
                    data: tempData,
                    borderColor: '#22c55e', // Xanh lá
                    backgroundColor: '#22c55e',
                    tension: 0.1,
                    datalabels: {
                        color: '#22c55e',
                        align: 'top',
                        font: { weight: 'bold', size: 13 },
                        formatter: (value) => value + '°'
                    }
                },
                {
                    label: 'Khả năng có mưa',
                    data: rainData,
                    borderColor: '#f97316', // Cam
                    backgroundColor: '#f97316',
                    tension: 0.1,
                    datalabels: {
                        color: (context) => (context.dataset.data[context.dataIndex] > 0 ? '#f97316' : '#333'), // Màu cam nếu > 0
                        align: 'top',
                        font: { weight: 'bold', size: 13 },
                        formatter: (value) => value + '%'
                    }
                }
            ]
        },
        options: sharedLineChartOptions() // Dùng chung options
    });
}

// ==========================================================
// HÀM VẼ BIỂU ĐỒ 3: #dailyRainChart (Bar Chart)
// ==========================================================
function drawDailyRainChart(labels, data) {
    const ctx = document.getElementById('dailyRainChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Lượng mưa (mm)',
                data: data,
                backgroundColor: 'rgba(54, 162, 235, 0.2)', // Xanh nhạt
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1,
                datalabels: {
                    color: '#333',
                    align: 'top',
                    anchor: 'end',
                    font: { weight: 'bold' },
                    formatter: (value) => (value > 0 ? value : '') // Chỉ hiện số > 0
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: { enabled: true },
                datalabels: {
                    display: true,
                    offset: -5
                }
            },
            scales: {
                y: {
                    min: 0,
                    max: 25,
                    ticks: { stepSize: 5 }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

// ==========================================================
// HÀM CHIA SẺ OPTIONS CHO 2 BIỂU ĐỒ ĐƯỜNG
// ==========================================================
function sharedLineChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                align: 'center',
                labels: { usePointStyle: true, boxWidth: 8 }
            },
            tooltip: { enabled: false },
            datalabels: {
                display: true,
                offset: 5
            }
        },
        scales: {
            y: {
                min: 0,
                max: 120,
                ticks: { stepSize: 20 }
            },
            x: {
                grid: { display: false }
            }
        },
        elements: {
            point: { radius: 0 }
        }
    };
}