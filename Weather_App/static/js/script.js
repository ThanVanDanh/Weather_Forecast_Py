// fetch("../templates/header.html")
//     .then(response => response.text())
//     .then(data => {
//         document.getElementById("header-placeholder").innerHTML = data;
//     });
// fetch("../templates/footer.html")
//     .then(response => response.text())
//     .then(data => {
//         document.getElementById("footer-placeholder").innerHTML = data;
//     });
// weather/static/weather/js/script.js

// Chờ cho toàn bộ HTML tải xong mới chạy
document.addEventListener('DOMContentLoaded', () => {

    // ID của tỉnh/thành phố mặc định khi tải trang
    // (Kiểm tra ID của 'Da Nang' trong Bảng Location sau khi import)
    const DEFAULT_LOCATION_ID = 30;
    const DEFAULT_CITY_NAME = "Ho Chi Minh City";

    // 1. Tải dữ liệu mặc định khi mở trang
    loadWeatherForLocation(DEFAULT_LOCATION_ID, DEFAULT_CITY_NAME);

    // 2. Tải các thành phố nổi bật
    loadFeaturedCities();

    // 3. Bạn tự thêm logic tìm kiếm (header.js?)
    //    Khi người dùng tìm kiếm, họ sẽ gọi hàm:
    //    handleSearch(cityName)
});


/**
 * Hàm xử lý tìm kiếm (ví dụ)
 */
async function handleSearch(cityName) {
    try {
        const response = await fetch(`/api/weather/search/?city=${cityName}`);
        if (!response.ok) throw new Error("Không tìm thấy");

        const locations = await response.json();
        if (locations.length > 0) {
            // Lấy kết quả đầu tiên
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
 * Hàm chính: Tải và hiển thị TẤT CẢ dữ liệu cho 1 địa điểm
 * @param {number} locationId ID của địa điểm (từ Bảng Location)
 * @param {string} cityName Tên để hiển thị
 */
async function loadWeatherForLocation(locationId, cityName) {
    try {
        // Cập nhật tên thành phố trước
        document.getElementById('current-city-name').innerText = `Thời tiết ${cityName}`;
        // (Bạn có thể thêm 1 icon "loading" ở đây)

        // Gọi song song 2 API: Hiện tại (từ Meteo) và Tương lai (từ AI)
        const [currentResponse, forecastResponse] = await Promise.all([
            fetch(`/api/weather/current/?location_id=${locationId}`),
            // fetch(`/api/weather/forecast/ai/?location_id=${locationId}`)
        ]);

        if (!currentResponse.ok) throw new Error('Không thể tải thời tiết hiện tại');
        // if (!forecastResponse.ok) throw new Error('Không thể tải dự báo AI');

        const currentData = await currentResponse.json();
        // const forecastData = await forecastResponse.json();

        // Cập nhật DOM
        updateCurrentWeatherDOM(currentData);
        // updateAIForecastDOM(forecastData);

    } catch (error) {
        console.error("Lỗi tải dữ liệu:", error);
        document.getElementById('current-city-name').innerText = `Lỗi tải ${cityName}`;
    }
}

/**
 * Cập nhật khối thời tiết hiện tại (HTML)
 * @param {object} data JSON trả về từ API Meteo (đã qua Service)
 */
function updateCurrentWeatherDOM(data) {
    // API Meteo trả về JSON rất phức tạp, ta phải "bóc tách"
    const current = data.current_weather;
    const hourly = data.hourly;
    const daily = data.daily;

    // Lấy chỉ số của giờ hiện tại (Meteo trả về mảng theo giờ)
    const now = new Date();
    // (Meteo trả về 24 giá trị cho 'hourly', từ 0-23)
    const currentHourIndex = now.getHours();

    // Cập nhật các giá trị
    document.getElementById('current-temp').innerText = `${Math.round(current.temperature)}°`;
    document.getElementById('current-feels-like').innerText = `Cảm giác như ${Math.round(hourly.apparent_temperature[currentHourIndex])}°`;
    document.getElementById('current-temp-minmax').innerText = `${Math.round(daily.temperature_2m_min[0])}°/${Math.round(daily.temperature_2m_max[0])}°`;
    document.getElementById('current-humidity').innerText = `${hourly.relativehumidity_2m[currentHourIndex]}%`;
    document.getElementById('current-pressure').innerText = `${Math.round(hourly.pressure_msl[currentHourIndex])} hPa`;
    document.getElementById('current-visibility').innerText = `${(hourly.visibility[currentHourIndex] / 1000).toFixed(0)} km`;
    document.getElementById('current-wind').innerText = `${current.windspeed} km/h`;
    document.getElementById('current-uvi').innerText = `${daily.uv_index_max[0].toFixed(1)}`;

    // Đổi code ra chữ
    const statusText = getWeatherStatusFromCode(current.weathercode, true);
    document.getElementById('current-description').innerText = statusText;

    // Đổi code ra icon
    const iconName = getWeatherIcon(current.weathercode);
    document.getElementById('current-icon').src = `/static/image/${iconName}`;
}

/**
 * Cập nhật khối dự báo AI (HTML)
 * @param {Array} forecastData Mảng các đối tượng dự báo từ Bảng 4
 */
function updateAIForecastDOM(forecastData) {
    const container = document.getElementById('forecast-container');
    container.innerHTML = ''; // Xóa dự báo cũ

    if (forecastData.length === 0) {
        container.innerHTML = '<p>Không có dữ liệu dự báo AI.</p>';
        return;
    }

    // Chỉ lấy 3 ngày đầu tiên (theo yêu cầu HTML)
    forecastData.slice(0, 3).forEach((day, index) => {
        const date = new Date(day.forecast_date);
        let dayDisplay = "";

        if (index === 0) {
            dayDisplay = "Hôm nay";
        } else {
            dayDisplay = date.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' }); // "T2 03/11"
        }

        const iconName = getWeatherIcon(day.predicted_weather_code);
        const statusText = getWeatherStatusFromCode(day.predicted_weather_code, false);

        const card = document.createElement('div');
        card.className = 'card forecast-card';
        card.innerHTML = `
            <h3>${dayDisplay}</h3>
            <img class="main-img" src="/static/image/${iconName}" alt="">
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
        container.innerHTML = ''; // Xóa cũ

        // Chia 9 thành phố thành 3 hàng (wrapper)
        for (let i = 0; i < cities.length; i += 3) {
            const wrapper = document.createElement('div');
            wrapper.className = 'cities-wrapper';

            cities.slice(i, i + 3).forEach(city => {
                // Kiểm tra xem Bảng 2 (Cache) đã có dữ liệu chưa
                if (!city.current_weather) {
                    console.warn(`Thành phố ${city.city_name} chưa có cache.`);
                    return;
                }

                const weather = city.current_weather.current_weather;
                const daily = city.current_weather.daily;
                const hourly = city.current_weather.hourly;
                const iconName = getWeatherIcon(weather.weathercode);
                const statusText = getWeatherStatusFromCode(weather.weathercode, true);

                const card = document.createElement('div');
                card.className = 'card city-card';
                card.innerHTML = `
                    <div class="main-title">${city.city_name}</div>
                    <img src="/static/weather/image/${iconName}" alt="" class="main-img">
                    <p class="img-eyes">
                        <img class="detail-img" src="/static/weather/image/icon-style-1-drop.svg" alt="">
                        <span>${hourly.relativehumidity_2m[new Date().getHours()]} %</span>
                    </p>
                    <div class="status"><p>${statusText}</p></div>
                    <div class="temp">${Math.round(daily.temperature_2m_max[0])}°/ ${Math.round(daily.temperature_2m_min[0])}°</div>
                `;

                // Thêm sự kiện click để tải trang chính
                card.addEventListener('click', () => {
                    loadWeatherForLocation(city.id, city.city_name);
                    window.scrollTo({ top: 0, behavior: 'smooth' }); // Cuộn lên đầu
                });
                wrapper.appendChild(card);
            });
            container.appendChild(wrapper);
        }

    } catch (error) {
        console.error("Lỗi tải thành phố nổi bật:", error);
    }
}


// =======================================================
// HÀM TIỆN ÍCH (Đổi Mã WMO ra chữ và icon)
// =======================================================

// (Bạn cần thêm các icon: weather.png, mayden.png, nang.png...
// vào thư mục 'static/weather/image/')

function getWeatherIcon(code) {
    if (code === 0) return "nang.png"; // Trời quang
    if (code >= 1 && code <= 3) return "mayden.png"; // Nắng, có mây
    if (code >= 45 && code <= 48) return "mayden.png"; // Sương mù
    if (code >= 51 && code <= 67) return "weather.png"; // Mưa
    if (code >= 71 && code <= 77) return "weather.png"; // Tuyết (không áp dụng)
    if (code >= 80 && code <= 82) return "weather.png"; // Mưa rào
    if (code >= 95 && code <= 99) return "weather.png"; // Giông bão
    return "mayden.png"; // Mặc định
}

function getWeatherStatusFromCode(code, isCurrent) {
    if (code === null || code === undefined) return "--";
    // (Đây là mã WMO Weather Interpretation Codes)
    switch (code) {
        case 0: return "Trời quang";
        case 1: return "Trời quang";
        case 2: return "Mây rải rác";
        case 3: return "Nhiều mây";
        case 45: case 48: return "Sương mù";
        case 51: return "Mưa phù";
        case 53: return "Mưa vừa";
        case 55: return "Mưa to";
        case 61: return "Mưa nhỏ";
        case 63: return "Mưa vừa";
        case 65: return "Mưa to";
        case 80: return "Mưa rào nhỏ";
        case 81: return "Mưa rào vừa";
        case 82: return "Mưa rào to";
        case 95: case 96: case 99: return "Giông bão";
        default: return isCurrent ? "Có mây" : "--";
    }
}