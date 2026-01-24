// weather/static/weather/js/script.js

document.addEventListener('DOMContentLoaded', () => {

    // Tự động làm mờ và ẩn các message Django trên mọi trang
    const messages = document.querySelectorAll('.fade-out-message');
    messages.forEach(function (msg) {
        setTimeout(function () {
            msg.classList.add('hide');
            setTimeout(function () {
                msg.style.display = 'none';
            }, 700);
        }, 1000);
    });

    // Chỉ chạy logic index.html nếu có forecast-container
    if (!document.getElementById('forecast-container')) {
        console.log('[DEBUG] Not on index.html, skipping script.js initialization');
        return;
    }


    const DEFAULT_LOCATION_ID = 30; // TP.HCM

    // Kiểm tra xem có location đã lưu từ định vị trước đó không
    const savedLocation = localStorage.getItem('userLocatedCity');
    
    if (savedLocation) {
        // Nếu có location đã lưu, sử dụng nó
        try {
            const locData = JSON.parse(savedLocation);
            console.log('[DEBUG] Loading saved location:', locData);
            loadWeatherForLocation(
                locData.locationId, 
                locData.cityName, 
                locData.lat, 
                locData.lon
            );
        } catch (e) {
            console.error('[DEBUG] Error parsing saved location:', e);
            // Fallback về TP.HCM nếu parse lỗi
            loadDefaultLocation();
        }
    } else {
        // Nếu chưa định vị, load TP.HCM mặc định
        loadDefaultLocation();
    }

    // Hàm load location mặc định (TP.HCM)
    function loadDefaultLocation() {
        fetch(`/api/weather/search/?city=Ho Chi Minh City`)
            .then(res => res.json())
            .then(locations => {
                if (locations.length > 0) {
                    const loc = locations[0];
                    const cityNameDisplay = loc.city_name_vn || loc.city_name;
                    const lat = loc.latitude;
                    const lon = loc.longitude;
                    loadWeatherForLocation(DEFAULT_LOCATION_ID, cityNameDisplay, lat, lon);
                } else {
                    loadWeatherForLocation(DEFAULT_LOCATION_ID, "Ho Chi Minh City", null, null);
                }
            })
            .catch(() => {
                loadWeatherForLocation(DEFAULT_LOCATION_ID, "Ho Chi Minh City", null, null);
            });
    }

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
            const cityNameDisplay = loc.city_name_vn || loc.city_name;
            const lat = loc.latitude;
            const lon = loc.longitude;
            const slug = loc.slug;
            // Lưu lịch sử tìm kiếm vào localStorage
            saveSearchHistory(loc.id, cityNameDisplay, slug);

            loadWeatherForLocation(loc.id, cityNameDisplay, lat, lon);
        } else {
            alert("Không tìm thấy tỉnh/thành phố này.");
        }
    } catch (e) {
        alert(e.message);
    }
}

/**
 * Hàm chính: Tải và hiển thị dữ liệu (Lazy Loading)
 */
async function loadWeatherForLocation(locationId, cityName, lat, lon) {
    try {
        document.getElementById('current-city-name').innerText = `Thời tiết ${cityName}`;

        console.log(`[DEBUG] Loading weather for locationId=${locationId}, cityName=${cityName}`);

        // Nếu không có lat/lon, fetch từ API location
        if (!lat || !lon) {
            const locResponse = await fetch(`/api/weather/search/?city=${encodeURIComponent(cityName)}`);
            if (locResponse.ok) {
                const locations = await locResponse.json();
                if (locations.length > 0) {
                    lat = locations[0].latitude;
                    lon = locations[0].longitude;
                }
            }
        }

        // === BƯỚC 1: Load Current Weather NGAY (Open-Meteo - rất nhanh) ===
        console.log('[DEBUG] Loading current weather from Open-Meteo...');
        const meteoUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&timezone=Asia/Ho_Chi_Minh&current_weather=true&daily=weathercode,temperature_2m_max,temperature_2m_min,uv_index_max,sunrise,sunset&hourly=temperature_2m,apparent_temperature,relativehumidity_2m,pressure_msl,visibility`;

        const currentResponse = await fetch(meteoUrl);

        if (!currentResponse.ok) {
            throw new Error(`Lỗi HTTP current: ${currentResponse.status}`);
        }

        const currentData = await currentResponse.json();
        console.log('[DEBUG] ✅ Current weather loaded instantly');

        // Cập nhật current weather NGAY LẬP TỨC
        updateCurrentWeatherDOM(currentData);

        // === BƯỚC 2: Hiển thị Loading cho Forecast ===
        const forecastContainer = document.getElementById('forecast-container');
        if (forecastContainer) {
            forecastContainer.innerHTML = '<p style="text-align:center;padding:40px;color:#999;"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải dự báo 5 ngày...</p>';
        }

        // === BƯỚC 3: Load Forecast SAU (Django API - có thể mất 2-3s) ===
        console.log('[DEBUG] Loading forecast from Django API (may take 2-3s)...');
        const forecastResponse = await fetch(`/api/weather/forecast/?location_id=${locationId}`);

        if (forecastResponse.ok) {
            const forecastData = await forecastResponse.json();
            console.log('[DEBUG] ✅ Forecast data loaded');

            if (forecastData && forecastData.daily_forecast) {
                updateDailyForecastDOM(forecastData.daily_forecast);
            } else {
                console.error('[ERROR] No daily_forecast in response');
                if (forecastContainer) {
                    forecastContainer.innerHTML = '<p style="text-align:center;color:#ff6b6b;">Không có dữ liệu dự báo</p>';
                }
            }
        } else {
            console.error('[ERROR] Forecast response failed:', forecastResponse.status);
            const errorText = await forecastResponse.text();
            console.error('[ERROR] Response:', errorText);
            if (forecastContainer) {
                forecastContainer.innerHTML = '<p style="text-align:center;color:#ff6b6b;">Lỗi tải dự báo</p>';
            }
        }

    } catch (error) {
        console.error("Lỗi tải dữ liệu:", error);
        document.getElementById('current-city-name').innerText = `Lỗi tải ${cityName}`;
    }
}

/**
 * Cập nhật khối thời tiết hiện tại (từ Open-Meteo data)
 */
function updateCurrentWeatherDOM(data) {
    // Chỉ chạy trên index.html
    if (!document.getElementById('current-temp')) {
        return;
    }

    const current = data.current_weather;
    const hourly = data.hourly;
    const daily = data.daily;

    // 1. Lấy is_day và icon ngay từ đầu
    const isDay = Number(current.is_day) === 1 ? 1 : 0;
    const icon = getWeatherIcon(current.weathercode, isDay);
    updateBackgroundVideo(current.weathercode, isDay);

    const now = new Date();
    const currentHourIndex = now.getHours();

    // Cập nhật nhiệt độ chính
    let currentTemp = current.temperature;
    if (hourly && hourly.temperature_2m && hourly.temperature_2m[currentHourIndex]) {
        currentTemp = hourly.temperature_2m[currentHourIndex];
    }

    document.getElementById('current-temp').innerText = `${Math.round(currentTemp)}°`;

    // Cập nhật feels like
    if (hourly && hourly.apparent_temperature) {
        const feelsLike = Math.round(hourly.apparent_temperature[currentHourIndex]);
        document.getElementById('current-feels-like').innerText = `Cảm giác như ${feelsLike}°`;
    }

    // Min/Max
    if (daily && daily.temperature_2m_min && daily.temperature_2m_max) {
        const tempMin = Math.round(daily.temperature_2m_min[0]);
        const tempMax = Math.round(daily.temperature_2m_max[0]);
        document.getElementById('current-temp-minmax').innerText = `${tempMin}°/${tempMax}°`;
    }

    // Độ ẩm
    if (hourly && hourly.relativehumidity_2m) {
        document.getElementById('current-humidity').innerText = `${hourly.relativehumidity_2m[currentHourIndex]}%`;
    }

    // Áp suất
    if (hourly && hourly.pressure_msl) {
        document.getElementById('current-pressure').innerText = `${Math.round(hourly.pressure_msl[currentHourIndex])} hPa`;
    }

    // Tầm nhìn
    if (hourly && hourly.visibility) {
        const visibilityKm = (hourly.visibility[currentHourIndex] / 1000).toFixed(0);
        document.getElementById('current-visibility').innerText = `${visibilityKm} km`;
    }

    // Gió
    document.getElementById('current-wind').innerText = `${current.windspeed} km/h`;

    // UV
    if (daily && daily.uv_index_max) {
        document.getElementById('current-uvi').innerText = `${daily.uv_index_max[0].toFixed(1)}`;
    }

    // Status text
    const statusText = getWeatherStatusFromCode(current.weathercode, isDay);
    document.getElementById('current-description').innerText = statusText;

    // Icon
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

        // Dự đoán icon dựa trên nhiệt độ (vì không có weathercode)
        let weatherCode = 1; // Mặc định: nắng nhẹ
        const avgTemp = (day.temp_max + day.temp_min) / 2;
        if (day.temp_max > 35) {
            weatherCode = 0; // Nắng gắt
        } else if (day.temp_max > 30) {
            weatherCode = 1; // Nắng nhẹ/mây rải rác
        } else if (day.temp_max < 20) {
            weatherCode = 3; // Nhiều mây/mát
        }

        const icon = getWeatherIcon(weatherCode, 1); // Ban ngày = 1
        const statusText = getWeatherStatusFromCode(weatherCode, 1);

        console.log(`[DEBUG] Card ${index}: ${dayOfWeek} ${dayMonth} - ${day.temp_max}°/${day.temp_min}° - ${statusText}`);

        const card = document.createElement('a');
        card.href = '#';
        card.className = 'card forecast-card';
        card.innerHTML = `
            <h3><span>${dayOfWeek}</span> <span>${dayMonth}</span></h3>
            <img class="main-img" src="/static/image/${icon}" alt="${statusText}">
            <div class="status"><p>${statusText}</p></div>
            <div class="temp"><p>${Math.round(day.temp_min)}°/ ${Math.round(day.temp_max)}°</p></div>
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

        const icon = getWeatherIcon(day.predicted_weather_code, 1);
        const statusText = getWeatherStatusFromCode(day.predicted_weather_code, 1);

        const card = document.createElement('div');
        card.className = 'card forecast-card';
        card.innerHTML = `
            <h3>${dayDisplay}</h3>
            <img class="main-img" src="/static/image/${icon}" alt="">
            <div class="status"><p>${statusText}</p></div>
            <div class="temp">${Math.round(day.predicted_temp_min)}°/ ${Math.round(day.predicted_temp_max)}°</div>
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
        if (container) container.innerHTML = '';

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

                const cityNameDisplay = city.city_name_vn || city.city_name;
                const card = document.createElement('div');
                card.className = 'card city-card';
                card.innerHTML = `
                    <div class="main-title">${cityNameDisplay}</div>
                    <img src="/static/image/${icon}" alt="" class="main-img">
                    <p class="img-eyes">
                        <img class="detail-img" src="/static/image/icon-style-1-drop.svg" alt="">
                        <span>${hourly.relativehumidity_2m[new Date().getHours()]} %</span>
                    </p>
                    <div class="status"><p>${statusText}</p></div>
                    <div class="temp">${Math.round(daily.temperature_2m_min[0])}°/ ${Math.round(daily.temperature_2m_max[0])}°</div>
                `;

                card.addEventListener('click', () => {
                    loadWeatherForLocation(city.id, cityNameDisplay, city.latitude, city.longitude);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                });
                wrapper.appendChild(card);
            });
            if (container) container.appendChild(wrapper);
        }
    } catch (error) {
        console.error("Lỗi tải thành phố nổi bật:", error);
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
        // return "mayrairac.mp4";
        case 3: // Nhiều mây
            return "nhieumay.mp4";
        case 45:
        case 48:
            return "amu.mp4";
        case 51: case 53: case 55: // Mưa phùn
        case 61: case 63: case 65: // Mưa thường
        case 80: case 81: case 82: // Mưa rào
            return "rain6.mp4";

        // TUYẾT
        case 56: case 57:
        case 66: case 67:
        case 71: case 73: case 75: case 77:
        case 85: case 86:
            return "tuyet.mp4";

        // nhóm giông bão
        case 95: // Có giông
        case 96: case 99: // Giông mưa đá
            return "giong.mp4";

        default:
            return "nhieumay.mp4";
    }
}
// update backgound
function updateBackgroundVideo(code, isDay) {
    const videoElement = document.getElementById('global-bg-video');
    if (!videoElement) return;
    const fileName = getWeatherVideoName(code, isDay);
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
        case 0:
            return isDay ? "Trời nắng" : "Trời quang đãng";
        case 1:
            return isDay ? "Nắng nhẹ" : "Ít mây";
        case 2:
            return isDay ? "Mây rải rác" : "Đêm có mây";
        case 3:
            return "Nhiều mây";
        case 45:
        case 48:
            return "Sương mù";
        case 51:
            return "Mưa phùn nhẹ";
        case 53:
            return "Mưa phùn vừa";
        case 55:
            return "Mưa phùn dày";
        case 56:
        case 57:
            return "Mưa phùn lạnh";
        case 61:
            return "Mưa nhỏ";
        case 63:
            return "Mưa vừa";
        case 65:
            return "Mưa to";
        case 66:
        case 67:
            return "Mưa lạnh";
        case 71:
            return "Tuyết rơi nhẹ";
        case 73:
            return "Tuyết rơi vừa";
        case 75:
            return "Tuyết rơi dày";
        case 77:
            return "Tuyết hạt";
        case 80:
            return "Mưa rào nhẹ";
        case 81:
            return "Mưa rào vừa";
        case 82:
            return "Mưa rào to";
        case 85:
        case 86:
            return "Mưa tuyết";
        case 95:
            return "Có giông";
        case 96:
        case 99:
            return "Giông mưa đá";
        default:
            return "Có mây";
    }
}

// =======================================================
// LỊCH SỬ TÌM KIẾM - LƯU VÀO DATABASE (THEO USER)
// =======================================================

/**
 * Lưu lịch sử tìm kiếm vào database thông qua API
 * @param {number} locationId - ID của địa điểm
 * @param {string} cityName - Tên thành phố
 * @param {string} slug - Slug của thành phố
 */
async function saveSearchHistory(locationId, cityName, slug) {
    try {
        // Lấy thời tiết hiện tại để lưu cùng lịch sử
        const weatherResponse = await fetch(`/api/weather/current/?location_id=${locationId}`);
        let temp = null;
        let weatherCode = 1;
        let isDay = 1;

        if (weatherResponse.ok) {
            const data = await weatherResponse.json();
            const current = data.current_weather;
            temp = Math.round(current.temperature);
            weatherCode = current.weathercode;
            isDay = current.is_day;
        }

        // Lấy CSRF token từ cookie
        const csrfToken = getCsrfToken();

        // Gọi API lưu lịch sử (yêu cầu đăng nhập)
        const response = await fetch('/api/weather/search-history/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                location_id: locationId,
                temperature: temp,
                weather_code: weatherCode,
                is_day: isDay
            })
        });

        if (response.ok) {
            const result = await response.json();
            console.log('[Search History] Saved to DB:', result);
        } else if (response.status === 401) {
            // User chưa đăng nhập - fallback lưu vào localStorage
            console.log('[Search History] User not logged in, saving to localStorage');
            saveToLocalStorage(locationId, cityName, temp, weatherCode, isDay, slug);
        } else {
            console.error('[Search History] API error:', response.status);
        }

    } catch (error) {
        console.error('[Search History] Error saving:', error);
    }
}

// Lấy CSRF token từ cookie
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Fallback: Lưu vào localStorage nếu chưa đăng nhập
function saveToLocalStorage(locationId, cityName, temp, weatherCode, isDay, slug) {
    const historyItem = {
        locationId: locationId,
        cityName: cityName,
        temperature: temp,
        weatherCode: weatherCode,
        isDay: isDay,
        slug: slug,
        timestamp: new Date().toISOString()
    };

    let history = JSON.parse(localStorage.getItem('weatherSearchHistory') || '[]');

    // Xóa mục trùng lặp
    history = history.filter(item => item.locationId !== locationId);

    // Thêm mục mới vào đầu
    history.unshift(historyItem);

    // Giữ tối đa 10 mục
    if (history.length > 10) {
        history = history.slice(0, 10);
    }

    localStorage.setItem('weatherSearchHistory', JSON.stringify(history));
    console.log('[Search History] Saved to localStorage:', historyItem);
}