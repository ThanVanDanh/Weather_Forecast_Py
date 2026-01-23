// search-history.js - Xử lý lịch sử tìm kiếm trên trang Customer Care

document.addEventListener('DOMContentLoaded', async function () {
    const historyContainer = document.querySelector('.history-list');

    if (!historyContainer) return;

    // Lấy CSRF token
    function getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }
        return null;
    }

    // Lấy icon thời tiết
    function getWeatherIcon(code, isDay = 1) {
        if (code === 0) return isDay ? 'fa-sun' : 'fa-moon';
        if (code === 1 || code === 2) return isDay ? 'fa-cloud-sun' : 'fa-cloud-moon';
        if (code === 3) return 'fa-cloud';
        if (code >= 45 && code <= 48) return 'fa-smog';
        if (code >= 51 && code <= 67) return 'fa-cloud-rain';
        if (code >= 71 && code <= 77) return 'fa-snowflake';
        if (code >= 80 && code <= 82) return 'fa-cloud-showers-heavy';
        if (code >= 95) return 'fa-bolt';
        return 'fa-cloud';
    }

    // Hiển thị lịch sử
    function displayHistory(historyData) {
        if (!historyData || historyData.length === 0) {
            historyContainer.innerHTML = `
                <div id="history-empty-state" style="text-align: center; padding: 30px; color: rgba(255,255,255,0.6);">
                    <i class="fa-solid fa-clock-rotate-left" style="font-size: 48px; opacity: 0.3; margin-bottom: 15px;"></i>
                    <p>Chưa có lịch sử tìm kiếm</p>
                    <p style="font-size: 12px;">Hãy tìm kiếm thời tiết trên trang chủ</p>
                </div>
            `;
            return;
        }

        let html = '';
        historyData.forEach(item => {
            const date = new Date(item.timestamp);
            const timeStr = date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
            const dateStr = date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
            const weatherIcon = getWeatherIcon(item.weatherCode, item.isDay);
            const temp = item.temperature !== null ? `${item.temperature}°C` : '--';

            html += `
                <div class="history-item" data-location-id="${item.locationId}" data-city="${item.cityName}" style="cursor: pointer;">
                    <div class="history-info">
                        <i class="fa-solid fa-location-dot"></i>
                        <div>
                            <strong>${item.cityName}</strong>
                            <span>${timeStr} - ${dateStr}</span>
                        </div>
                    </div>
                    <div class="history-weather">
                        <span class="temp">${temp}</span>
                        <i class="fa-solid ${weatherIcon}"></i>
                    </div>
                </div>
            `;
        });

        html += `
            <button id="clear-history-btn" style="margin-top: 15px; padding: 10px 20px; background: rgba(255,107,107,0.2); border: 1px solid rgba(255,107,107,0.5); color: #ff6b6b; border-radius: 8px; cursor: pointer; width: 100%;">
                <i class="fa-solid fa-trash"></i> Xóa toàn bộ lịch sử
            </button>
        `;

        historyContainer.innerHTML = html;

        // Thêm event click cho các item
        historyContainer.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', function () {
                const cityName = this.dataset.city;
                window.location.href = `/?search=${encodeURIComponent(cityName)}`;
            });
        });

        // Thêm event cho nút xóa
        const clearBtn = document.getElementById('clear-history-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', clearSearchHistory);
        }
    }

    // Load lịch sử từ API
    async function loadSearchHistory() {
        try {
            const response = await fetch('/api/weather/search-history/');

            if (response.ok) {
                const data = await response.json();
                console.log('[Search History] Loaded from DB:', data.history.length);

                // Kiểm tra localStorage có dữ liệu mới cần sync không
                const localHistory = JSON.parse(localStorage.getItem('weatherSearchHistory') || '[]');
                if (localHistory.length > 0) {
                    console.log('[Search History] Found', localHistory.length, 'items in localStorage, syncing...');

                    // Sync những item mới từ localStorage lên DB
                    await syncLocalStorageToDatabase(localHistory);

                    // Load lại từ DB sau khi sync
                    const newResponse = await fetch('/api/weather/search-history/');
                    if (newResponse.ok) {
                        const newData = await newResponse.json();
                        displayHistory(newData.history);
                        localStorage.removeItem('weatherSearchHistory');
                        console.log('[Search History] Sync complete, cleared localStorage');
                        return;
                    }
                }

                displayHistory(data.history);
            } else {
                console.log('[Search History] API error, loading from localStorage');
                loadFromLocalStorage();
            }
        } catch (error) {
            console.error('[Search History] Error:', error);
            loadFromLocalStorage();
        }
    }

    // Đồng bộ localStorage lên database
    async function syncLocalStorageToDatabase(localHistory) {
        const csrfToken = getCsrfToken();

        for (const item of localHistory) {
            try {
                // Lấy nhiệt độ thực tế từ API nếu chưa có
                let temperature = item.temperature;
                let weatherCode = item.weatherCode || 1;
                let isDay = item.isDay !== undefined ? item.isDay : 1;

                if (temperature === null || temperature === undefined) {
                    try {
                        const weatherResponse = await fetch(`/api/weather/current/?location_id=${item.locationId}`);
                        if (weatherResponse.ok) {
                            const weatherData = await weatherResponse.json();
                            const current = weatherData.current_weather;
                            temperature = Math.round(current.temperature);
                            weatherCode = current.weathercode;
                            isDay = current.is_day;
                        }
                    } catch (e) {
                        console.log('[Search History] Could not fetch weather');
                    }
                }

                await fetch('/api/weather/search-history/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        location_id: item.locationId,
                        temperature: temperature,
                        weather_code: weatherCode,
                        is_day: isDay
                    })
                });
            } catch (error) {
                console.error('[Search History] Error syncing item:', error);
            }
        }
        console.log('[Search History] Synced', localHistory.length, 'items to DB');
    }

    // Fallback: Load từ localStorage
    function loadFromLocalStorage() {
        let history = JSON.parse(localStorage.getItem('weatherSearchHistory') || '[]');
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        history = history.filter(item => new Date(item.timestamp) > thirtyDaysAgo);
        localStorage.setItem('weatherSearchHistory', JSON.stringify(history));
        displayHistory(history);
    }

    // Xóa toàn bộ lịch sử
    async function clearSearchHistory() {
        if (!confirm('Bạn có chắc muốn xóa toàn bộ lịch sử tìm kiếm?')) return;

        try {
            await fetch('/api/weather/search-history/', {
                method: 'DELETE',
                headers: { 'X-CSRFToken': getCsrfToken() }
            });
        } catch (error) {
            console.error('[Search History] Error clearing:', error);
        }

        localStorage.removeItem('weatherSearchHistory');
        loadSearchHistory();
    }

    // Khởi tạo
    await loadSearchHistory();
});
