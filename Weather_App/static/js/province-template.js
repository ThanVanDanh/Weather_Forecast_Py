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

    // 1. Cập nhật Nhiệt độ chính (lấy từ temperature_2m tại giờ hiện tại)
    let currentTemp = current.temperature; // Fallback
    if (hourly && hourly.temperature_2m && hourly.temperature_2m[currentHourIndex]) {
        currentTemp = hourly.temperature_2m[currentHourIndex];
    }
    const tempElement = document.getElementById('current-temperature');
    if (tempElement) tempElement.textContent = `${Math.round(currentTemp)}°`;

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

// ============== WEATHER HELPER FUNCTIONS ==============
function getWeatherIcon(code, isDay = 1) {
    if (code === 0) return isDay === 1 ? "ngay.png" : "dem.png";
    if (code === 1 || code === 2) return isDay === 1 ? "nangcomay.png" : "demcomay.png";
    if (code === 3) return "nhieumay.png";
    if (code >= 45 && code <= 48) return "suongmu.png";
    if (code >= 51 && code <= 67) return "mua.png";
    if (code >= 71 && code <= 77) return "tuyet.png";
    if (code >= 80 && code <= 82) return "mua.png";
    if (code >= 85 && code <= 86) return "tuyet.png";
    if (code >= 95 && code <= 99) return "giongbao.png";
    return "mayden.png";
}

function getWeatherStatusFromCode(code, isDay = 1) {
    if (code === null || code === undefined) return "--";

    switch (code) {
        case 0: return isDay ? "Trời nắng" : "Trời quang đãng";
        case 1: return isDay ? "Nắng nhẹ" : "Ít mây";
        case 2: return isDay ? "Mây rải rác" : "Đêm có mây";
        case 3: return "Nhiều mây";
        case 45: case 48: return "Sương mù";
        case 51: return "Mưa phùn nhẹ";
        case 53: return "Mưa phùn vừa";
        case 55: return "Mưa phùn dày";
        case 56: case 57: return "Mưa phùn lạnh";
        case 61: return "Mưa nhỏ";
        case 63: return "Mưa vừa";
        case 65: return "Mưa to";
        case 66: case 67: return "Mưa lạnh";
        case 71: return "Tuyết rơi nhẹ";
        case 73: return "Tuyết rơi vừa";
        case 75: return "Tuyết rơi dày";
        case 77: return "Tuyết hạt";
        case 80: return "Mưa rào nhẹ";
        case 81: return "Mưa rào vừa";
        case 82: return "Mưa rào to";
        case 85: case 86: return "Mưa tuyết";
        case 95: return "Có giông";
        case 96: case 99: return "Giông mưa đá";
        default: return "Có mây";
    }
}

// ============== FORECAST RENDER FUNCTIONS ==============
// Hàm render dự báo 24h
function renderHourlyForecast(hourlyData) {
    const container = document.getElementById('hourly-forecast-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!hourlyData || hourlyData.length === 0) {
        container.innerHTML = '<p>Không có dữ liệu dự báo 24h</p>';
        return;
    }
    
    // Lấy thời gian hiện tại
    const now = new Date();
    
    // Lọc chỉ lấy các giờ trong tương lai (forecast_time > now)
    const futureHours = hourlyData.filter(hour => {
        const forecastTime = new Date(hour.forecast_time);
        return forecastTime > now;
    });
    
    console.log('[DEBUG] Total hourly data:', hourlyData.length, 'Future hours:', futureHours.length);
    
    if (futureHours.length === 0) {
        container.innerHTML = '<p>Không có dữ liệu dự báo giờ tới</p>';
        return;
    }
    
    // Hiển thị tối đa 24h tiếp theo
    futureHours.slice(0, 24).forEach(hour => {
        const date = new Date(hour.forecast_time);
        const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
        
        // Dự đoán weathercode từ nhiệt độ (vì không có weathercode)
        let weatherCode = 1;
        if (hour.temperature > 35) weatherCode = 0;
        else if (hour.temperature > 30) weatherCode = 1;
        else if (hour.temperature < 20) weatherCode = 3;
        
        const isDay = date.getHours() >= 6 && date.getHours() <= 18 ? 1 : 0;
        const icon = getWeatherIcon(weatherCode, isDay);
        const statusText = getWeatherStatusFromCode(weatherCode, isDay);
        
        const div = document.createElement('div');
        div.className = 'hourly-item';
        
        // Format humidity: nếu có thì hiển thị, không thì '--'
        const humidityDisplay = hour.humidity !== null && hour.humidity !== undefined 
            ? `${Math.round(hour.humidity)}%` 
            : '--';
        
        div.innerHTML = `
            <p class="hourly-time">${timeStr}</p>
            <img class="hourly-icon" src="/static/image/${icon}" alt="${statusText}">
            <p class="hourly-temp">${Math.round(hour.temperature)}°</p>
            <span class="hourly-humidity"><i class="fa-solid fa-droplet"></i> ${humidityDisplay}</span>
            <p class="hourly-desc">${statusText}</p>
        `;
        container.appendChild(div);
    });
}

// Hàm render dự báo 5 ngày
function renderDailyForecast(dailyData, hourlyData) {
    const container = document.querySelector('.daily-forecast-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!dailyData || dailyData.length === 0) {
        container.innerHTML = '<p>Không có dữ liệu dự báo 5 ngày</p>';
        return;
    }
    
    dailyData.slice(0, 5).forEach((day, index) => {
        const date = new Date(day.forecast_date);
        const dayOfWeek = date.toLocaleDateString('vi-VN', { weekday: 'short' });
        const dayMonth = date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
        
        // Backend dự báo từ ngày mai, nên index 0 = ngày mai
        let label;
        if (index === 0) {
            label = `${dayOfWeek} ${dayMonth}`;
        } else {
            label = `${dayOfWeek} ${dayMonth}`;
        }
        
        // Dự đoán weathercode từ nhiệt độ
        let weatherCode = 1;
        if (day.temp_max > 35) weatherCode = 0;
        else if (day.temp_max > 30) weatherCode = 1;
        else if (day.temp_max < 20) weatherCode = 3;
        
        const icon = getWeatherIcon(weatherCode, 1);
        const statusText = getWeatherStatusFromCode(weatherCode, 1);
        
        const div = document.createElement('div');
        div.className = 'forecast-item';
        div.innerHTML = `
            <strong>${label}</strong>
            <span>${Math.round(day.temp_min)}° / ${Math.round(day.temp_max)}°</span>
            <img src="/static/image/${icon}" alt="${statusText}">
            <span>${statusText}</span>
        `;
        container.appendChild(div);
    });
}

// Hàm tải dữ liệu chi tiết cho trang tỉnh/thành phố
async function loadProvinceDetails(locationId, cityName, lat, lon) {
    if (!lat || !lon) {
        document.getElementById('current-status-text').textContent = 'Lỗi: Thiếu tọa độ vị trí';
        return;
    }

    try {
        // === BƯỚC 1: Load Current Weather NGAY (rất nhanh - Open-Meteo API) ===
        console.log('[DEBUG] Loading current weather for:', cityName, 'lat:', lat, 'lon:', lon);
        
        const meteoUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&timezone=Asia/Ho_Chi_Minh&current_weather=true&daily=weathercode,temperature_2m_max,temperature_2m_min,uv_index_max,sunrise,sunset&hourly=temperature_2m,apparent_temperature,relativehumidity_2m,pressure_msl,visibility`;
        
        const currentResponse = await fetch(meteoUrl);
        
        if (!currentResponse.ok) {
            throw new Error(`Lỗi HTTP current: ${currentResponse.status}`);
        }
        
        const currentData = await currentResponse.json();
        console.log('[DEBUG] ✅ Current weather loaded instantly');
        
        // Hiển thị current weather NGAY LẬP TỨC
        updateCurrentWeatherDOM(currentData, cityName);
        
        // === BƯỚC 2: Hiển thị Loading cho Forecasts ===
        const hourlyContainer = document.getElementById('hourly-forecast-container');
        const dailyContainer = document.getElementById('daily-forecast-container');
        
        if (hourlyContainer) {
            hourlyContainer.innerHTML = '<p style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dự báo 24h...</p>';
        }
        if (dailyContainer) {
            dailyContainer.innerHTML = '<p style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dự báo 5 ngày...</p>';
        }
        
        // === BƯỚC 3: Load Forecasts SAU (có thể mất 2-3s do predict) ===
        console.log('[DEBUG] Loading forecasts (may take 2-3s)...');
        const forecastResponse = await fetch(`/api/weather/forecast/?location_id=${locationId}`);
        
        if (forecastResponse.ok) {
            const forecastData = await forecastResponse.json();
            console.log('[DEBUG] ✅ Forecast data loaded');
            
            // Render dự báo 24h
            if (forecastData.hourly_forecast) {
                console.log('[DEBUG] Rendering hourly forecast, count:', forecastData.hourly_forecast.length);
                renderHourlyForecast(forecastData.hourly_forecast);
            } else {
                console.error('[ERROR] No hourly_forecast in response');
                if (hourlyContainer) hourlyContainer.innerHTML = '<p>Không có dữ liệu dự báo 24h</p>';
            }
            
            // Render dự báo 5 ngày
            if (forecastData.daily_forecast) {
                console.log('[DEBUG] Rendering daily forecast, count:', forecastData.daily_forecast.length);
                renderDailyForecast(forecastData.daily_forecast, forecastData.hourly_forecast);

                // Lazy: chỉ khi daily_forecast đã về thì mới vẽ biểu đồ min/max
                const daily5 = forecastData.daily_forecast.slice(0, 5);
                const labels = daily5.map(d => formatShortDayLabel(d.forecast_date));
                const minTemps = daily5.map(d => Math.round(d.temp_min));
                const maxTemps = daily5.map(d => Math.round(d.temp_max));
                drawDailyMinMaxChart(labels, minTemps, maxTemps);
            } else {
                console.error('[ERROR] No daily_forecast in response');
                if (dailyContainer) dailyContainer.innerHTML = '<p>Không có dữ liệu dự báo 5 ngày</p>';
            }
        } else {
            console.error('[ERROR] Forecast API failed:', forecastResponse.status);
            if (hourlyContainer) hourlyContainer.innerHTML = '<p>Lỗi tải dự báo 24h</p>';
            if (dailyContainer) dailyContainer.innerHTML = '<p>Lỗi tải dự báo 5 ngày</p>';
        }

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
    if (typeof LOCATION_ID !== 'undefined' && LOCATION_ID && typeof LAT !== 'undefined' && typeof LON !== 'undefined') {
        loadProvinceDetails(LOCATION_ID, CITY_NAME, LAT, LON);
    }
    // //////////////////////////////////////////////////////////////////////////////
    // Đăng ký plugin datalabels cho tất cả biểu đồ
    Chart.register(ChartDataLabels);

    // Giữ biểu đồ 12h tới & lượng mưa theo dữ liệu placeholder hiện tại
    // (biểu đồ min/max 5 ngày sẽ vẽ lazy sau khi API daily_forecast trả về)
    const hourlyLabels = ['16:00', '17:00', '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00', '01:00', '02:00', '03:00'];
    const hourlyTemps = [27, 25, 24, 23, 20, 21, 21, 21, 21, 21, 21, 20];
    const hourlyRain = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    drawHourlyChart(hourlyLabels, hourlyTemps, hourlyRain);

    const dailyRainLabels = ['CN 16', 'T2 17', 'T3 18', 'T4 19', 'T5 20', 'T6 21', 'T7 22'];
    const dailyRainAmounts = [0, 1.51, 11.99, 0.23, 0, 0, 0];
    drawDailyRainChart(dailyRainLabels, dailyRainAmounts);
});

let dailyMinMaxChartInstance = null;

function formatShortDayLabel(dateString) {
    const d = new Date(dateString);
    const weekdays = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
    const wd = weekdays[d.getDay()];
    return `${wd} ${d.getDate()}`;
}

function drawDailyMinMaxChart(labels, minData, maxData) {
    const ctx = document.getElementById('dailyWeatherChart');
    if (!ctx) return;

    if (dailyMinMaxChartInstance) {
        dailyMinMaxChartInstance.destroy();
        dailyMinMaxChartInstance = null;
    }

    const allTemps = [...minData, ...maxData].filter(v => v !== null && v !== undefined);
    const tMin = allTemps.length ? Math.floor(Math.min(...allTemps) - 2) : 0;
    const tMax = allTemps.length ? Math.ceil(Math.max(...allTemps) + 2) : 40;

    dailyMinMaxChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Nhiệt độ max',
                    data: maxData,
                    borderColor: '#22c55e',
                    backgroundColor: '#22c55e',
                    tension: 0.1,
                    datalabels: {
                        color: '#22c55e',
                        align: 'top',
                        font: { weight: 'bold', size: 13 },
                        formatter: (value) => `${value}°`
                    }
                },
                {
                    label: 'Nhiệt độ min',
                    data: minData,
                    borderColor: '#f97316',
                    backgroundColor: '#f97316',
                    tension: 0.1,
                    datalabels: {
                        color: '#f97316',
                        align: 'bottom',
                        font: { weight: 'bold', size: 13 },
                        formatter: (value) => `${value}°`
                    }
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    align: 'center',
                    labels: { usePointStyle: true, boxWidth: 8 }
                },
                tooltip: { enabled: true },
                datalabels: {
                    display: true,
                    offset: 5
                }
            },
            scales: {
                y: {
                    min: tMin,
                    max: tMax,
                    ticks: { stepSize: 5 }
                },
                x: {
                    grid: { display: false }
                }
            },
            elements: {
                point: { radius: 0 }
            }
        }
    });
}

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