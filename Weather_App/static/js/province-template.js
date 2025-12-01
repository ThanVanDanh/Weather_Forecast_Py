// Hàm tiện ích để cập nhật DOM
// province-template.js
function updateCurrentWeatherDOM(data, cityName) {
    console.log("Dữ liệu API trả về:", data);
    console.log("Hourly Temp:", data?.hourly?.temperature_2m);
    if (!data || !data.current_weather) {
        console.error("Dữ liệu API thiếu current_weather.");
        return;
    }

    const current = data.current_weather;
    const hourly = data.hourly;
    const daily = data.daily;

    // Lấy giờ hiện tại để tra cứu trong mảng hourly (0-23)
    const now = new Date();
    const currentHourIndex = now.getHours();

    // 1. Cập nhật Nhiệt độ chính
    const tempElement = document.getElementById('current-temperature');
    if (tempElement) tempElement.textContent = `${Math.round(current.temperature)}°`;

    // 2. Cập nhật Trạng thái chữ & Icon
    const isDay = current.is_day !== undefined ? current.is_day : 1;

    const statusText = getWeatherStatusFromCode(current.weathercode, isDay);
    const statusElement = document.getElementById('current-status-text');
    if (statusElement) statusElement.textContent = statusText;

    const iconName = getWeatherIcon(current.weathercode, isDay);
    const iconContainer = document.getElementById('current-icon');
    if (iconContainer) {
        // Thay thế icon cũ bằng thẻ img
        iconContainer.innerHTML = `<img src="/static/image/${iconName}" alt="${statusText}" style="width: 80px; height: 80px;">`;
    }

    // 3. Cập nhật Cảm giác như (Apparent Temperature)
    if (hourly && hourly.apparent_temperature) {
        const feelsLike = Math.round(hourly.apparent_temperature[currentHourIndex]);
        const feelsLikeElement = document.getElementById('current-feels-like');
        if (feelsLikeElement) feelsLikeElement.textContent = `${feelsLike}°`;
    }

    // 4. Cập nhật Min/Max trong ngày
    if (daily && daily.temperature_2m_min && daily.temperature_2m_max) {
        const tempMin = Math.round(daily.temperature_2m_min[0]);
        const tempMax = Math.round(daily.temperature_2m_max[0]);
        const minMaxElement = document.getElementById('detail-temp-minmax');
        if (minMaxElement) minMaxElement.textContent = `${tempMin}°/${tempMax}°`;
    }

    // 5. Cập nhật Độ ẩm (Lấy theo giờ hiện tại)
    if (hourly && hourly.relativehumidity_2m) {
        const humidity = hourly.relativehumidity_2m[currentHourIndex];
        const humidityElement = document.getElementById('detail-humidity');
        if (humidityElement) humidityElement.textContent = `${humidity}%`;
    }

    // 6. Cập nhật Áp suất
    if (hourly && hourly.pressure_msl) {
        const pressure = Math.round(hourly.pressure_msl[currentHourIndex]);
        const pressureElement = document.getElementById('detail-pressure');
        if (pressureElement) pressureElement.textContent = `${pressure} hPa`;
    }

    // 7. Cập nhật Tầm nhìn (đổi m sang km)
    if (hourly && hourly.visibility) {
        const visibilityKm = (hourly.visibility[currentHourIndex] / 1000).toFixed(1);
        const visElement = document.getElementById('detail-visibility');
        if (visElement) visElement.textContent = `${visibilityKm} km`;
    }

    // 8. Cập nhật Gió
    const windElement = document.getElementById('detail-wind-speed');
    if (windElement) windElement.textContent = `${current.windspeed} km/h`;

    // 9. Cập nhật UV Max
    if (daily && daily.uv_index_max) {
        const uvMax = daily.uv_index_max[0];
        const uvElement = document.getElementById('detail-uv-max');
        if (uvElement) uvElement.textContent = uvMax;
    }
    // Nhiệt độ theo khoảng thời gian (Ngày/Đêm)
    if (hourly && hourly.temperature_2m) {
        const hourlyTemps = hourly.temperature_2m;

        // Ngày: 7h sáng đến 7h tối (12 tiếng)
        const NGAY_HOURS = [6,7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17];
        // Đêm: 7h tối đến 7h sáng (12 tiếng, bao gồm qua nửa đêm)
        const DEM_HOURS = [18,19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5];

        const tempNgayElement = document.getElementById('temp-ngay');
        if (tempNgayElement) tempNgayElement.textContent = getMinMaxTempForPeriod(hourlyTemps, NGAY_HOURS);

        const tempDemElement = document.getElementById('temp-dem');
        if (tempDemElement) tempDemElement.textContent = getMinMaxTempForPeriod(hourlyTemps, DEM_HOURS);
    }
    //Cập nhật Bình minh / Hoàng hôn ===
    if (daily && daily.sunrise && daily.sunset) {
        // API trả về dạng: "2023-11-01T06:05" -> Cần format thành "06:05 AM"
        const sunriseTime = formatTime(daily.sunrise[0]);
        const sunsetTime = formatTime(daily.sunset[0]);

        const sunriseElement = document.getElementById('sunrise-time');
        if (sunriseElement) sunriseElement.textContent = sunriseTime;

        const sunsetElement = document.getElementById('sunset-time');
        if (sunsetElement) sunsetElement.textContent = sunsetTime;
    }
}
// Hàm tải dữ liệu chi tiết cho trang tỉnh/thành phố
async function loadProvinceDetails(locationId, cityName) {
    if (!locationId) {
        // Lỗi nếu không có ID (thường xảy ra nếu backend không tìm thấy Location)
        document.getElementById('current-status-text').textContent = 'Lỗi: Không tìm thấy ID vị trí';
        return;
    }

    // API đã định nghĩa trong Weather_App/urls.py
    const apiUrl = `/api/weather/current/?location_id=${locationId}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`Lỗi HTTP: ${response.status}`);
        }
        const data = await response.json();

        // Cập nhật thông tin thời tiết hiện tại lên DOM
        updateCurrentWeatherDOM(data, cityName);

        // TODO: Cập nhật logic vẽ biểu đồ bằng dữ liệu thật (data.hourly, data.daily)
        // drawHourlyChart(data.hourly);
        // drawDailyChart(data.daily);

    } catch (error) {
        console.error('Lỗi khi tải dữ liệu thời tiết:', error);
        document.getElementById('current-status-text').textContent = 'Lỗi tải dữ liệu';
    }
}

//Hàm tiện ích để tính Min/Max nhiệt độ
    /**
     * Tính toán nhiệt độ Min/Max trong một khoảng giờ (ví dụ: Sáng, Tối)
     * @param {Array<number>} hourlyTemps Mảng nhiệt độ theo giờ (24 giá trị)
     * @param {number[]} hoursToInclude Các chỉ số giờ cần tính (ví dụ: [5, 6, 7, 8, 9, 10])
     * @returns {string} Chuỗi định dạng "Min°/Max°"
     */
    function getMinMaxTempForPeriod(hourlyTemps, hoursToInclude) {
        if (!hourlyTemps || hourlyTemps.length < 24) return "--°/--°";

        const temperatures = hoursToInclude.map(h => hourlyTemps[h]).filter(temp => temp !== null && temp !== undefined);

        if (temperatures.length === 0) return "--°/--°";

        const minTemp = Math.round(Math.min(...temperatures));
        const maxTemp = Math.round(Math.max(...temperatures));

        return `${minTemp}°/${maxTemp}°`;
    }

// === HÀM TIỆN ÍCH chuyển đổi thoi gian ===
/**
 * Hàm chuyển đổi thời gian ISO (2023-11-01T06:05) sang giờ phút (06:05 AM)
 */
function formatTime(isoString) {
    if (!isoString) return '--:--';
    const date = new Date(isoString);
    // Format theo kiểu 12 giờ (AM/PM)
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
}
// Chờ cho toàn bộ HTML tải xong mới chạy
document.addEventListener('DOMContentLoaded', () => {
    // Dữ liệu giả lập (thay cho dữ liệu thật từ API)
    if (typeof LOCATION_ID !== 'undefined' && LOCATION_ID) {
        loadProvinceDetails(LOCATION_ID, CITY_NAME);
    }
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