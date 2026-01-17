// weather/static/weather/js/script.js

document.addEventListener('DOMContentLoaded', () => {
    const DEFAULT_LOCATION_ID = 30; // TP.HCM
    const DEFAULT_CITY_NAME = "Ho Chi Minh City";

    // 1. Tải dữ liệu mặc định
    loadWeatherForLocation(DEFAULT_LOCATION_ID, DEFAULT_CITY_NAME);

    // 2. Tải các thành phố nổi bật
    loadFeaturedCities();
});


/**
 * Hàm xử lý tìm kiếm
 */
async function handleSearch(cityName) {
    try {
        const response = await fetch(`/api/weather/search/?city=${cityName}`);
        if (!response.ok) throw new Error("Không tìm thấy");

        const locations = await response.json();
        if (locations.length > 0) {
            const loc = locations[0];
            loadWeatherForLocation(loc.id, loc.city_name);
        } else {
            alert("Không tìm thấy tỉnh/thành phố này.");
        }
    } catch (e) {
        alert(e.message);
    }
}

/**
 * Hàm chính: Tải và hiển thị dữ liệu
 */
async function loadWeatherForLocation(locationId, cityName) {
    try {
        document.getElementById('current-city-name').innerText = `Thời tiết ${cityName}`;

        // Gọi API
        const [currentResponse, forecastResponse] = await Promise.all([
            fetch(`/api/weather/current/?location_id=${locationId}`),
            fetch(`/api/weather/forecast/?location_id=${locationId}`)
        ]);

        if (!currentResponse.ok) throw new Error('Không thể tải thời tiết hiện tại');

        const currentData = await currentResponse.json();
        console.log('[DEBUG] Current data:', currentData);
        
        // Cập nhật DOM
        updateCurrentWeatherDOM(currentData);

        // Hiển thị dự báo AI 5 ngày
        if (forecastResponse.ok) {
            const forecastData = await forecastResponse.json();
            console.log('[DEBUG] Forecast data:', forecastData);
            
            if (forecastData && forecastData.daily_forecast) {
                updateDailyForecastDOM(forecastData.daily_forecast);
            } else {
                console.error('[ERROR] No daily_forecast in response');
            }
        } else {
            console.error('[ERROR] Forecast response failed:', forecastResponse.status);
            const errorText = await forecastResponse.text();
            console.error('[ERROR] Response:', errorText);
        }

    } catch (error) {
        console.error("Lỗi tải dữ liệu:", error);
        document.getElementById('current-city-name').innerText = `Lỗi tải ${cityName}`;
    }
}

/**
 * Cập nhật khối thời tiết hiện tại
 */
function updateCurrentWeatherDOM(data) {
    const current = data.current_weather;
    const hourly = data.hourly;
    const daily = data.daily;

    // 1. Lấy is_day và icon ngay từ đầu
    const isDay = current.is_day;
    const icon = getWeatherIcon(current.weathercode, isDay);

    const now = new Date();
    const currentHourIndex = now.getHours();

    document.getElementById('current-temp').innerText = `${Math.round(current.temperature)}°`;
    document.getElementById('current-feels-like').innerText = `Cảm giác như ${Math.round(hourly.apparent_temperature[currentHourIndex])}°`;
    document.getElementById('current-temp-minmax').innerText = `${Math.round(daily.temperature_2m_min[0])}°/${Math.round(daily.temperature_2m_max[0])}°`;
    document.getElementById('current-humidity').innerText = `${hourly.relativehumidity_2m[currentHourIndex]}%`;
    document.getElementById('current-pressure').innerText = `${Math.round(hourly.pressure_msl[currentHourIndex])} hPa`;
    document.getElementById('current-visibility').innerText = `${(hourly.visibility[currentHourIndex] / 1000).toFixed(0)} km`;
    document.getElementById('current-wind').innerText = `${current.windspeed} km/h`;
    document.getElementById('current-uvi').innerText = `${daily.uv_index_max[0].toFixed(1)}`;

    // 2. Gọi hàm status với tham số isDay
    const statusText = getWeatherStatusFromCode(current.weathercode, isDay);
    document.getElementById('current-description').innerText = statusText;

    // 3. Gán icon (Dùng biến 'icon' đã khai báo ở trên)
    document.getElementById('current-icon').src = `/static/image/${icon}`;
}

/**
 * Cập nhật khối dự báo 5 ngày từ AI
 */
function updateDailyForecastDOM(dailyForecast) {
    console.log('[DEBUG] updateDailyForecastDOM called with:', dailyForecast);
    
    const container = document.getElementById('forecast-container');
    
    if (!container) {
        console.error('[ERROR] forecast-container not found!');
        return;
    }
    
    console.log('[DEBUG] Container found:', container);
    container.innerHTML = '';

    if (!dailyForecast || dailyForecast.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999;">Không có dữ liệu dự báo</p>';
        return;
    }

    console.log(`[DEBUG] Rendering ${dailyForecast.length} forecast cards`);
    
    // Hiển thị tối đa 5 ngày
    dailyForecast.slice(0, 5).forEach((day, index) => {
        const date = new Date(day.forecast_date);
        const dayOfWeek = date.toLocaleDateString('vi-VN', { weekday: 'long' });
        const dayMonth = date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });

        console.log(`[DEBUG] Card ${index}: ${dayOfWeek} ${dayMonth} - ${day.temp_max}°/${day.temp_min}°`);

        const card = document.createElement('a');
        card.href = '#';
        card.className = 'card forecast-card';
        card.innerHTML = `
            <h3><span>${dayOfWeek}</span> <span>${dayMonth}</span></h3>
            <img class="main-img" src="/static/image/mayden.png" alt="">
            <p class="img-eyes">
                <img class="detail-img" src="/static/image/icon-style-1-drop.svg" alt=""><span>-- %</span>
            </p>
            <div class="status"><p>Dự báo AI</p></div>
            <div class="temp"><p>${Math.round(day.temp_max)}°/ ${Math.round(day.temp_min)}°</p></div>
        `;
        container.appendChild(card);
    });
    
    console.log('[DEBUG] Forecast cards rendered successfully');
}

/**
 * Cập nhật khối dự báo AI
 */
function updateAIForecastDOM(forecastData) {
    const container = document.getElementById('forecast-container');
    container.innerHTML = '';

    if (!forecastData || forecastData.length === 0) {
        container.innerHTML = '<p>Không có dữ liệu dự báo AI.</p>';
        return;
    }

    forecastData.slice(0, 3).forEach((day, index) => {
        const date = new Date(day.forecast_date);
        let dayDisplay = index === 0 ? "Hôm nay" : date.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' });

        // SỬA LỖI: Đặt tên biến là 'icon' để khớp với template string bên dưới
        // (Dự báo tương lai thường mặc định là ban ngày = 1)
        const icon = getWeatherIcon(day.predicted_weather_code, 1);
        const statusText = getWeatherStatusFromCode(day.predicted_weather_code, 1);

        const card = document.createElement('div');
        card.className = 'card forecast-card';
        card.innerHTML = `
            <h3>${dayDisplay}</h3>
            <img class="main-img" src="/static/image/${icon}" alt="">
            <p class="img-eyes">
                <img class="detail-img" src="/static/image/icon-style-1-drop.svg" alt="">
                <span>${day.predicted_precipitation_probability || '--'} %</span>
            </p>
            <div class="status"><p>${statusText}</p></div>
            <div class="temp">${Math.round(day.predicted_temp_max)}°/ ${Math.round(day.predicted_temp_min)}°</div>
        `;
        container.appendChild(card);
    });
}

/**
 * Tải và hiển thị 9 thành phố nổi bật
 */
async function loadFeaturedCities() {
    try {
        const response = await fetch('/api/weather/featured/');
        if (!response.ok) throw new Error('Không thể tải thành phố nổi bật');

        const cities = await response.json();
        const container = document.getElementById('featured-cities-container');
        if(container) container.innerHTML = '';

        for (let i = 0; i < cities.length; i += 3) {
            const wrapper = document.createElement('div');
            wrapper.className = 'cities-wrapper';

            cities.slice(i, i + 3).forEach(city => {
                if (!city.current_weather) return;

                const weather = city.current_weather.current_weather;
                const daily = city.current_weather.daily;
                const hourly = city.current_weather.hourly;

                const isDay = weather.is_day;

                const statusText = getWeatherStatusFromCode(weather.weathercode, isDay);
                const icon = getWeatherIcon(weather.weathercode, isDay);

                const card = document.createElement('div');
                card.className = 'card city-card';
                card.innerHTML = `
                    <div class="main-title">${city.city_name}</div>
                    <img src="/static/image/${icon}" alt="" class="main-img">
                    <p class="img-eyes">
                        <img class="detail-img" src="/static/image/icon-style-1-drop.svg" alt="">
                        <span>${hourly.relativehumidity_2m[new Date().getHours()]} %</span>
                    </p>
                    <div class="status"><p>${statusText}</p></div>
                    <div class="temp">${Math.round(daily.temperature_2m_max[0])}°/ ${Math.round(daily.temperature_2m_min[0])}°</div>
                `;

                card.addEventListener('click', () => {
                    loadWeatherForLocation(city.id, city.city_name);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                });
                wrapper.appendChild(card);
            });
            if(container) container.appendChild(wrapper);
        }
    } catch (error) {
        console.error("Lỗi tải thành phố nổi bật:", error);
    }
}


// =======================================================
// HÀM TIỆN ÍCH
// =======================================================

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

// SỬA LỖI: Đổi tên tham số thứ 2 từ 'isCurrent' thành 'isDay' để khớp với logic bên trong
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