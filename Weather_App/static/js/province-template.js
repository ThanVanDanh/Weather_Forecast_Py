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

    const now = new Date();
    const currentHourIndex = now.getHours();

    let currentTemp = current.temperature; // Fallback
    if (hourly && hourly.temperature_2m && hourly.temperature_2m[currentHourIndex]) {
        currentTemp = hourly.temperature_2m[currentHourIndex];
    }
    const tempElement = document.getElementById('current-temperature');
    if (tempElement) tempElement.textContent = `${Math.round(currentTemp)}°`;

    const isDay = Number(current.is_day) === 1 ? 1 : 0;


    const statusText = getWeatherStatusFromCode(current.weathercode, isDay);
    const statusElement = document.getElementById('current-status-text');
    if (statusElement) statusElement.textContent = statusText;
    if (typeof updateBackgroundVideo === "function") {
        console.log("Đang cập nhật background video...");
        updateBackgroundVideo(current.weathercode, isDay);
    }

    const iconName = getWeatherIcon(current.weathercode, isDay);
    const iconContainer = document.getElementById('current-icon');
    if (iconContainer) {
        iconContainer.innerHTML = `<img src="/static/image/${iconName}" alt="${statusText}" style="width: 80px; height: 80px;">`;
    }

    if (hourly && hourly.apparent_temperature) {
        const feelsLike = Math.round(hourly.apparent_temperature[currentHourIndex]);
        const feelsLikeElement = document.getElementById('current-feels-like');
        if (feelsLikeElement) feelsLikeElement.textContent = `${feelsLike}°`;
    }

    if (daily && daily.temperature_2m_min && daily.temperature_2m_max) {
        const tempMin = Math.round(daily.temperature_2m_min[0]);
        const tempMax = Math.round(daily.temperature_2m_max[0]);
        const minMaxElement = document.getElementById('detail-temp-minmax');
        if (minMaxElement) minMaxElement.textContent = `${tempMin}°/${tempMax}°`;
    }

    if (hourly && hourly.relativehumidity_2m) {
        const humidity = hourly.relativehumidity_2m[currentHourIndex];
        const humidityElement = document.getElementById('detail-humidity');
        if (humidityElement) humidityElement.textContent = `${humidity}%`;
    }

    if (hourly && hourly.pressure_msl) {
        const pressure = Math.round(hourly.pressure_msl[currentHourIndex]);
        const pressureElement = document.getElementById('detail-pressure');
        if (pressureElement) pressureElement.textContent = `${pressure} hPa`;
    }

    if (hourly && hourly.visibility) {
        const visibilityKm = (hourly.visibility[currentHourIndex] / 1000).toFixed(1);
        const visElement = document.getElementById('detail-visibility');
        if (visElement) visElement.textContent = `${visibilityKm} km`;
    }

    const windElement = document.getElementById('detail-wind-speed');
    if (windElement) windElement.textContent = `${current.windspeed} km/h`;

    if (daily && daily.uv_index_max) {
        const uvMax = daily.uv_index_max[0];
        const uvElement = document.getElementById('detail-uv-max');
        if (uvElement) uvElement.textContent = uvMax;
    }
    if (hourly && hourly.temperature_2m) {
        const hourlyTemps = hourly.temperature_2m;

        const NGAY_HOURS = [6,7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17];
        const DEM_HOURS = [18,19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5];

        const tempNgayElement = document.getElementById('temp-ngay');
        if (tempNgayElement) tempNgayElement.textContent = getMinMaxTempForPeriod(hourlyTemps, NGAY_HOURS);

        const tempDemElement = document.getElementById('temp-dem');
        if (tempDemElement) tempDemElement.textContent = getMinMaxTempForPeriod(hourlyTemps, DEM_HOURS);
    }

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
function getWeatherVideoName(code, isDay) {

    if (!isDay && (code >= 0 && code <= 2)) {
        return "troidem.mp4";
    }

    switch (code) {
        case 0: // Quang đãng
        case 1: // Nắng nhẹ
            return "troisang.mp4";

        case 2: // Mây rải rác
            return "mayrairac.mp4";
        case 3: // Nhiều mây
            return "nhieumay.mp4";

        //  NHÓM SƯƠNG MÙ
        case 45:
        case 48:
            return "amu.mp4";

        //  NHÓM MƯA
        case 51: case 53: case 55: // Mưa phùn
        case 61: case 63: case 65: // Mưa thường
        case 80: case 81: case 82: // Mưa rào
            return "rain6.mp4";

        //  NHÓM MƯA LẠNH / TUYẾT
        case 56: case 57: // Mưa phùn lạnh
        case 66: case 67: // Mưa lạnh
            return "rain6.mp4";

        case 71: case 73: case 75: case 77: // Tuyết
        case 85: case 86: // Mưa tuyết
            return "nhieumay.mp4";

        // --- NHÓM GIÔNG BÃO ---
        case 95: // Có giông
        case 96: case 99: // Giông mưa đá
            return "rain6.mp4";

        default:
            return "nhieumay.mp4";
    }
}

function updateAirQualityDOM(data) {
    if (!data || !data.current) {
        console.error("Dữ liệu Air Quality không hợp lệ");
        return;
    }
    
    const current = data.current;
    
    const eaqi = current.european_aqi || 0;
    
    let level, color, desc;
    if (eaqi <= 20) {
        level = 'Tốt';
        color = '#4CAF50';
        desc = 'Chất lượng không khí tốt, không ảnh hưởng sức khỏe';
    } else if (eaqi <= 40) {
        level = 'Khá';
        color = '#8BC34A';
        desc = 'Chất lượng không khí chấp nhận được';
    } else if (eaqi <= 60) {
        level = 'Trung bình';
        color = '#FFC107';
        desc = 'Nhóm nhạy cảm nên hạn chế hoạt động ngoài trời';
    } else if (eaqi <= 80) {
        level = 'Kém';
        color = '#FF9800';
        desc = 'Ảnh hưởng sức khỏe, hạn chế ra ngoài';
    } else {
        level = 'Rất kém';
        color = '#F44336';
        desc = 'Nguy hiểm! Tránh hoạt động ngoài trời';
    }
    

    const gaugeElement = document.querySelector('.aqi-gauge span');
    if (gaugeElement) {
        gaugeElement.textContent = level;
        gaugeElement.style.color = color;
        gaugeElement.style.fontWeight = 'bold';
    }
    

    const descElement = document.querySelector('.aqi-main p');
    if (descElement) {
        descElement.textContent = desc;
    }
    

    const detailsGrid = document.querySelector('.aqi-details-grid');
    if (detailsGrid) {
        detailsGrid.innerHTML = `
            <div>CO <strong>${(current.carbon_monoxide || 0).toFixed(0)}</strong></div>
            <div>NH<sub>3</sub> <strong>${(current.ammonia || 0).toFixed(2)}</strong></div>
            <div>NO<sub>2</sub> <strong>${(current.nitrogen_dioxide || 0).toFixed(2)}</strong></div>
            <div>O<sub>3</sub> <strong>${(current.ozone || 0).toFixed(1)}</strong></div>
            <div>PM10 <strong>${(current.pm10 || 0).toFixed(1)}</strong></div>
            <div>PM2.5 <strong>${(current.pm2_5 || 0).toFixed(1)}</strong></div>
            <div>SO<sub>2</sub> <strong>${(current.sulphur_dioxide || 0).toFixed(2)}</strong></div>
        `;
    }
}

function updateBackgroundVideo(code, isDay) {
    const videoElement = document.getElementById('global-bg-video');


    if (!videoElement) return;

    const availableVideos = new Set([
        'amu.mp4',
        'mayrairac.mp4',
        'nhieumay.mp4',
        'rain6.mp4',
        'troidem.mp4',
        'troisang.mp4'
    ]);

    let fileName = getWeatherVideoName(code, isDay);
    if (!availableVideos.has(fileName)) {
        console.warn('[Video] File không tồn tại trong static/video, fallback:', fileName);
        fileName = 'nhieumay.mp4';
    }
    const newSrc = `/static/video/${fileName}`;

    const currentSrc = videoElement.querySelector('source').getAttribute('src');

    if (currentSrc && currentSrc.includes(fileName)) {
        console.log(`[Video] Giữ nguyên video: ${fileName}`);
        return;
    }

    console.log(`[Video] Đổi background sang: ${fileName}`);


    videoElement.querySelector('source').src = newSrc;
    videoElement.load();
    videoElement.play().catch(e => console.log("Autoplay bị chặn hoặc lỗi:", e));
}

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

function renderHourlyForecast(hourlyData) {
    const container = document.getElementById('hourly-forecast-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!hourlyData || hourlyData.length === 0) {
        container.innerHTML = '<p>Không có dữ liệu dự báo 24h</p>';
        return;
    }

    const now = new Date();

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

        let weatherCode = 1;
        if (hour.temperature > 35) weatherCode = 0;
        else if (hour.temperature > 30) weatherCode = 1;
        else if (hour.temperature < 20) weatherCode = 3;
        
        const isDay = date.getHours() >= 6 && date.getHours() <= 18 ? 1 : 0;
        const icon = getWeatherIcon(weatherCode, isDay);
        const statusText = getWeatherStatusFromCode(weatherCode, isDay);
        
        const div = document.createElement('div');
        div.className = 'hourly-item';

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

        let label;
        if (index === 0) {
            label = `${dayOfWeek} ${dayMonth}`;
        } else {
            label = `${dayOfWeek} ${dayMonth}`;
        }

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

        console.log('[DEBUG] Loading current weather for:', cityName, 'lat:', lat, 'lon:', lon);
        
        const meteoUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&timezone=Asia/Ho_Chi_Minh&current_weather=true&daily=weathercode,temperature_2m_max,temperature_2m_min,uv_index_max,sunrise,sunset&hourly=temperature_2m,apparent_temperature,relativehumidity_2m,pressure_msl,visibility`;
        
        const currentResponse = await fetch(meteoUrl);
        
        if (!currentResponse.ok) {
            throw new Error(`Lỗi HTTP current: ${currentResponse.status}`);
        }
        
        const currentData = await currentResponse.json();
        console.log('[DEBUG] ✅ Current weather loaded instantly');

        updateCurrentWeatherDOM(currentData, cityName);

        console.log('[DEBUG] Loading air quality...');
        const airQualityUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,ammonia`;
        
        fetch(airQualityUrl)
            .then(res => res.json())
            .then(aqData => {
                console.log('[DEBUG] ✅ Air Quality loaded');
                updateAirQualityDOM(aqData);
            })
            .catch(err => {
                console.error('[DEBUG] ❌ Air Quality error:', err);
            });

        const hourlyContainer = document.getElementById('hourly-forecast-container');
        const dailyContainer = document.getElementById('daily-forecast-container');
        
        if (hourlyContainer) {
            hourlyContainer.innerHTML = '<p style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dự báo 24h...</p>';
        }
        if (dailyContainer) {
            dailyContainer.innerHTML = '<p style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dự báo 5 ngày...</p>';
        }

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
            // biểu đồ 12h
            if (forecastData.hourly_forecast && forecastData.hourly_forecast.length >= 12) {
                const loader = document.getElementById('hourlyChart12h-loader');
                const chartCanvas = document.getElementById('hourlyChart12h');
                if (loader) loader.style.display = '';
                if (chartCanvas) chartCanvas.style.display = 'none';
                setTimeout(() => {
                    const now = new Date();
                    const currentHour = now.getHours();
                    let hourLabels = [];
                    let tempData = [];
                    let humidityData = [];
                    for (let i = 0; i < 12; i++) {
                        const hour = forecastData.hourly_forecast[i];

                        let date = hour.forecast_time ? new Date(hour.forecast_time) : null;
                        let label = date ? (date.getHours()<10?'0':'')+date.getHours()+':00' : (i<10?'0':'')+i+':00';
                        hourLabels.push(label);
                        tempData.push(Math.round(hour.temperature));
                        humidityData.push(Math.round(hour.humidity));
                    }
                    drawHourlyChart12h(hourLabels, tempData, humidityData);
                    if (loader) loader.style.display = 'none';
                    if (chartCanvas) chartCanvas.style.display = '';
                }, 200);
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

    function getMinMaxTempForPeriod(hourlyTemps, hoursToInclude) {
        if (!hourlyTemps || hourlyTemps.length < 24) return "--°/--°";

        const temperatures = hoursToInclude.map(h => hourlyTemps[h]).filter(temp => temp !== null && temp !== undefined);

        if (temperatures.length === 0) return "--°/--°";

        const minTemp = Math.round(Math.min(...temperatures));
        const maxTemp = Math.round(Math.max(...temperatures));

        return `${minTemp}°/${maxTemp}°`;
    }

// ===  chuyển đổi thoi gian ===

function formatTime(isoString) {
    if (!isoString) return '--:--';
    const date = new Date(isoString);
    // Format theo kiểu 12 giờ (AM/PM)
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
}

document.addEventListener('DOMContentLoaded', () => {
    // Dữ liệu giả lập (thay cho dữ liệu thật từ API)
    if (typeof LOCATION_ID !== 'undefined' && LOCATION_ID && typeof LAT !== 'undefined' && typeof LON !== 'undefined') {
        loadProvinceDetails(LOCATION_ID, CITY_NAME, LAT, LON);
    }

    Chart.register(ChartDataLabels);


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
        options: sharedLineChartOptions()
    });
}

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
        options: sharedLineChartOptions()
    });
}

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

function drawHourlyChart12h(labels, tempData, humidityData) {
    const ctx = document.getElementById('hourlyChart12h');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Nhiệt độ',
                    data: tempData,
                    borderColor: '#22c55e',
                    backgroundColor: '#22c55e',
                    yAxisID: 'y',
                    tension: 0.1,
                    datalabels: {
                        color: '#22c55e',
                        align: 'top',
                        font: {weight: 'bold', size: 13},
                        formatter: (value) => value + '°'
                    }
                },
                {
                    label: 'Độ ẩm',
                    data: humidityData,
                    borderColor: '#3b82f6',
                    backgroundColor: '#3b82f6',
                    yAxisID: 'y1',
                    tension: 0.1,
                    datalabels: {
                        color: '#3b82f6',
                        align: 'top',
                        font: {weight: 'bold', size: 13},
                        formatter: (value) => value + '%'
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
                    labels: {usePointStyle: true, boxWidth: 8}
                },
                tooltip: {enabled: true},
                datalabels: {
                    display: true,
                    offset: 5
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    position: 'left',
                    min: 0,
                    max: 50,
                    title: {display: true, text: 'Nhiệt độ (°C)'}
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    min: 0,
                    max: 100,
                    title: {display: true, text: 'Độ ẩm (%)'},
                    grid: {drawOnChartArea: false}
                },
                x: {
                    grid: {display: false}
                }
            },
            elements: {
                point: {radius: 0}
            }
        }
    });
}
