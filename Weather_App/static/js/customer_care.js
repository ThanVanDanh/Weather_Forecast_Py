document.addEventListener('DOMContentLoaded', async function () {
            const locationSelect = document.getElementById('outfit-location-select');
            const weatherCondition = document.getElementById('outfit-weather-condition');
            const weatherIcon = document.getElementById('outfit-weather-icon');
            const weatherText = document.getElementById('outfit-weather-text');
            const adviceText = document.getElementById('outfit-advice-text');
            const outfitItemsContainer = document.getElementById('outfit-items-container');

            let citiesList = [];
            function getCurrentCityName() {
                const cityEl = document.getElementById('current-city');
                if (cityEl) {
                    const cityName = cityEl.innerText.trim();
                    console.log('[Outfit] Current city from header:', cityName);
                    if (cityName && cityName !== 'Chưa xác định') {
                        return cityName;
                    }
                }
                return null;
            }

            async function searchLocationByName(cityName) {
                if (!cityName) return null;

                try {
                    let searchQuery = cityName
                        .replace(/^(thành phố|tỉnh|tp\.?)\s*/i, '')
                        .trim();

                    console.log('[Outfit] Searching for:', searchQuery);

                    const response = await fetch(`/api/weather/search/?city=${encodeURIComponent(searchQuery)}`);
                    if (!response.ok) return null;

                    const locations = await response.json();
                    if (locations && locations.length > 0) {
                        console.log('[Outfit] Found location:', locations[0]);
                        return locations[0];
                    }
                } catch (error) {
                    console.error('[Outfit] Search error:', error);
                }
                return null;
            }

            // Load danh sách tất cả tỉnh/thành phố (34 tỉnh)
            async function loadLocations() {
                try {
                    const response = await fetch('/api/weather/locations/');
                    if (!response.ok) throw new Error('Không thể tải danh sách địa điểm');

                    citiesList = await response.json();
                    citiesList.forEach(city => {
                        const option = document.createElement('option');
                        option.value = city.id;
                        option.textContent = city.city_name_vn || city.city_name;
                        locationSelect.appendChild(option);
                    });

                    return citiesList;
                } catch (error) {
                    console.error('Lỗi tải danh sách địa điểm:', error);
                    return [];
                }
            }

            // Lấy icon thời tiết
            function getWeatherIconClass(code, isDay = 1) {
                if (code === 0) return isDay ? "fa-sun" : "fa-moon";
                if (code === 1 || code === 2) return isDay ? "fa-cloud-sun" : "fa-cloud-moon";
                if (code === 3) return "fa-cloud";
                if (code >= 45 && code <= 48) return "fa-smog";
                if (code >= 51 && code <= 67) return "fa-cloud-rain";
                if (code >= 71 && code <= 77) return "fa-snowflake";
                if (code >= 80 && code <= 82) return "fa-cloud-showers-heavy";
                if (code >= 85 && code <= 86) return "fa-snowflake";
                if (code >= 95 && code <= 99) return "fa-bolt";
                return "fa-cloud";
            }

            // Lấy mô tả thời tiết
            function getWeatherDescription(code, temp, isDay = 1) {
                let desc = "";
                if (code === 0) desc = isDay ? "Trời nắng" : "Trời quang";
                else if (code === 1 || code === 2) desc = "Ít mây";
                else if (code === 3) desc = "Nhiều mây";
                else if (code >= 45 && code <= 48) desc = "Sương mù";
                else if (code >= 51 && code <= 67) desc = "Có mưa";
                else if (code >= 71 && code <= 86) desc = "Có tuyết";
                else if (code >= 95) desc = "Có giông";
                else desc = "Có mây";

                return `${desc} ${Math.round(temp)}°C`;
            }

            // Tạo outfit items dựa trên thời tiết
            function generateOutfitItems(temp, weatherCode) {
                const items = [];

                if (temp >= 30) {
                    items.push({ icon: 'fa-shirt', text: 'Áo thun nhẹ' });
                    items.push({ icon: 'fa-hat-cowboy', text: 'Mũ/Nón' });
                    items.push({ icon: 'fa-glasses', text: 'Kính râm' });
                    items.push({ icon: 'fa-bottle-water', text: 'Mang nước' });
                } else if (temp >= 20) {
                    items.push({ icon: 'fa-shirt', text: 'Áo sơ mi' });
                    items.push({ icon: 'fa-vest', text: 'Áo khoác nhẹ' });
                } else if (temp >= 15) {
                    items.push({ icon: 'fa-vest', text: 'Áo khoác' });
                    items.push({ icon: 'fa-mitten', text: 'Khăn quàng' });
                } else {
                    items.push({ icon: 'fa-jacket', text: 'Áo ấm dày' });
                    items.push({ icon: 'fa-mitten', text: 'Găng tay' });
                    items.push({ icon: 'fa-socks', text: 'Vớ ấm' });
                }

                // Thêm ô/áo mưa nếu có mưa
                if (weatherCode >= 51 && weatherCode <= 82) {
                    items.push({ icon: 'fa-umbrella', text: 'Mang ô' });
                }

                return items;
            }

            // Load gợi ý trang phục cho location
            async function loadOutfitAdvice(locationId) {
                try {
                    adviceText.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="margin-right: 8px;"></i><span>Đang tải gợi ý...</span>';

                    const [outfitResp, currentResp] = await Promise.all([
                        fetch(`/api/weather/outfit/?location_id=${locationId}`),
                        fetch(`/api/weather/current/?location_id=${locationId}`)
                    ]);

                    let temp = 30;
                    let weatherCode = 1;
                    let isDay = 1;

                    // Xử lý dữ liệu thời tiết hiện tại
                    if (currentResp.ok) {
                        const currentData = await currentResp.json();
                        const current = currentData.current_weather;
                        temp = current.temperature;
                        weatherCode = current.weathercode;
                        isDay = current.is_day;

                        // Cập nhật weather condition
                        const iconClass = getWeatherIconClass(weatherCode, isDay);
                        weatherIcon.className = `fa-solid ${iconClass}`;
                        weatherText.textContent = getWeatherDescription(weatherCode, temp, isDay);
                    }

                    // Xử lý gợi ý trang phục
                    if (outfitResp.ok) {
                        const outfitData = await outfitResp.json();
                        adviceText.innerHTML = `
                    <i class="fa-solid fa-lightbulb" style="color: #ffc107; margin-right: 8px;"></i>
                    <span>"${outfitData.advice}"</span>
                `;
                    } else {
                        adviceText.innerHTML = `
                    <i class="fa-solid fa-lightbulb" style="color: #ffc107; margin-right: 8px;"></i>
                    <span>"Hãy mặc trang phục phù hợp với nhiệt độ ${Math.round(temp)}°C"</span>
                `;
                    }

                    // Hiển thị outfit items
                    const outfitItems = generateOutfitItems(temp, weatherCode);
                    outfitItemsContainer.innerHTML = outfitItems.map(item => `
                <div class="outfit-item">
                    <i class="fa-solid ${item.icon}"></i>
                    <span>${item.text}</span>
                </div>
            `).join('');
                    outfitItemsContainer.style.display = 'flex';

                } catch (error) {
                    console.error('Lỗi tải gợi ý trang phục:', error);
                    adviceText.innerHTML = `
                <i class="fa-solid fa-exclamation-triangle" style="color: #ff6b6b; margin-right: 8px;"></i>
                <span>Không thể tải gợi ý. Vui lòng thử lại sau.</span>
            `;
                }
            }

            locationSelect.addEventListener('change', function () {
                const locationId = this.value;
                if (locationId) {
                    loadOutfitAdvice(locationId);
                } else {
                    // Reset về trạng thái ban đầu
                    weatherIcon.className = 'fa-solid fa-cloud';
                    weatherText.textContent = 'Chọn địa điểm để xem gợi ý';
                    adviceText.innerHTML = `
                <i class="fa-solid fa-lightbulb" style="color: #ffc107; margin-right: 8px;"></i>
                <span>Vui lòng chọn tỉnh/thành phố để nhận gợi ý trang phục</span>
            `;
                    outfitItemsContainer.style.display = 'none';
                }
            });

            // Khởi tạo
            await loadLocations();

            // Lắng nghe sự kiện từ location.js
            document.addEventListener('weatherLocationUpdated', async (e) => {
                const data = e.detail;
                console.log('[Outfit] Received location update:', data);
                if (data && data.city) {
                    const loc = await searchLocationByName(data.city);
                    if (loc) {
                        locationSelect.value = loc.id;
                        loadOutfitAdvice(loc.id);
                    }
                }
            });

            // Lấy vị trí đã định vị từ current-city
            const currentCityName = getCurrentCityName();
            let defaultLocationId = null;

            if (currentCityName) {
                // Tìm kiếm location từ API
                const foundLocation = await searchLocationByName(currentCityName);
                if (foundLocation) {
                    defaultLocationId = foundLocation.id;
                    console.log(`[Outfit] Đã tìm thấy vị trí định vị: ${foundLocation.city_name_vn || foundLocation.city_name} (ID: ${defaultLocationId})`);
                }
            }
            // Nếu không tìm thấy, mặc định TP.HCM (id=30)
            if (!defaultLocationId) {
                defaultLocationId = 30;
                console.log('[Outfit] Không tìm thấy vị trí đã định vị, sử dụng mặc định TP.HCM');
            }

            locationSelect.value = defaultLocationId;
            loadOutfitAdvice(defaultLocationId);
        });

        // năng lượng mặt trời
        document.addEventListener('DOMContentLoaded', async function () {
            const solarLocationSelect = document.getElementById('solar-location-select');
            const solarInfoContainer = document.getElementById('solar-info-container');
            const solarLoading = document.getElementById('solar-loading');
            const solarError = document.getElementById('solar-error');
            const solarErrorText = document.getElementById('solar-error-text');

            const solarKwh = document.getElementById('solar-kwh');
            const solarRadiation = document.getElementById('solar-radiation');
            const solarSunshine = document.getElementById('solar-sunshine');
            const solarRating = document.getElementById('solar-rating');

            let solarCitiesList = [];

            function getCurrentCityName() {
                const cityEl = document.getElementById('current-city');
                if (cityEl) {
                    const cityName = cityEl.innerText.trim();
                    if (cityName && cityName !== 'Chưa xác định') {
                        return cityName;
                    }
                }
                return null;
            }

            async function searchLocationByName(cityName) {
                if (!cityName) return null;

                try {
                    let searchQuery = cityName
                        .replace(/^(thành phố|tỉnh|tp\.?)\s*/i, '')
                        .trim();

                    console.log('[Solar] Searching for:', searchQuery);

                    const response = await fetch(`/api/weather/search/?city=${encodeURIComponent(searchQuery)}`);
                    if (!response.ok) return null;

                    const locations = await response.json();
                    if (locations && locations.length > 0) {
                        console.log('[Solar] Found location:', locations[0]);
                        return locations[0];
                    }
                } catch (error) {
                    console.error('[Solar] Search error:', error);
                }
                return null;
            }

            // Load danh sách tất cả tỉnh/thành phố cho solar (34 tỉnh)
            async function loadSolarLocations() {
                try {
                    const response = await fetch('/api/weather/locations/');
                    if (!response.ok) throw new Error('Không thể tải danh sách địa điểm');

                    solarCitiesList = await response.json();
                    solarCitiesList.forEach(city => {
                        const option = document.createElement('option');
                        option.value = city.id;
                        option.textContent = city.city_name_vn || city.city_name;
                        solarLocationSelect.appendChild(option);
                    });

                    return solarCitiesList;
                } catch (error) {
                    console.error('Lỗi tải danh sách địa điểm:', error);
                    return [];
                }
            }

            // Hiển thị loading
            function showLoading() {
                solarInfoContainer.style.display = 'none';
                solarError.style.display = 'none';
                solarLoading.style.display = 'block';
            }

            // Hiển thị lỗi
            function showError(message) {
                solarInfoContainer.style.display = 'none';
                solarLoading.style.display = 'none';
                solarError.style.display = 'block';
                solarErrorText.textContent = message;
            }

            // Hiển thị dữ liệu
            function showData(data) {
                solarLoading.style.display = 'none';
                solarError.style.display = 'none';
                solarInfoContainer.style.display = 'block';

                const summary = data.summary;

                // Cập nhật các giá trị
                solarKwh.textContent = summary.estimated_kwh.toFixed(1);
                solarRadiation.textContent = `${summary.avg_radiation_w.toFixed(0)} W/m²`;
                solarSunshine.textContent = `${summary.sunshine_hours} giờ`;

                // Cập nhật rating với màu sắc
                solarRating.textContent = summary.rating;
                solarRating.className = 'value ' + summary.rating_color;
            }

            // Load dữ liệu bức xạ mặt trời
            async function loadSolarData(locationId) {
                showLoading();

                try {
                    const response = await fetch(`/api/weather/solar/?location_id=${locationId}`);
                    const data = await response.json();

                    if (response.ok && data.status === 'success') {
                        showData(data);
                    } else {
                        showError(data.error || 'Không thể tải dữ liệu bức xạ');
                    }
                } catch (error) {
                    console.error('Lỗi tải dữ liệu bức xạ:', error);
                    showError('Lỗi kết nối. Vui lòng thử lại sau.');
                }
            }

            // Event listener cho dropdown solar
            solarLocationSelect.addEventListener('change', function () {
                const locationId = this.value;
                if (locationId) {
                    loadSolarData(locationId);
                } else {
                    // Reset về trạng thái ban đầu
                    solarInfoContainer.style.display = 'block';
                    solarLoading.style.display = 'none';
                    solarError.style.display = 'none';
                    solarKwh.textContent = '--';
                    solarRadiation.textContent = '-- W/m²';
                    solarSunshine.textContent = '-- giờ';
                    solarRating.textContent = '--';
                    solarRating.className = 'value';
                }
            });

            // Khởi tạo
            await loadSolarLocations();

            // Lấy vị trí đã định vị từ current-city
            const currentCityName = getCurrentCityName();
            let defaultLocationId = null;

            if (currentCityName) {
                // Tìm kiếm location từ API
                const foundLocation = await searchLocationByName(currentCityName);
                if (foundLocation) {
                    defaultLocationId = foundLocation.id;
                    console.log(`[Solar] Đã tìm thấy vị trí định vị: ${foundLocation.city_name_vn || foundLocation.city_name} (ID: ${defaultLocationId})`);
                }
            }

            // Nếu không tìm thấy, mặc định TP.HCM (id=30)
            if (!defaultLocationId) {
                defaultLocationId = 30;
                console.log('[Solar] Không tìm thấy vị trí đã định vị, sử dụng mặc định TP.HCM');
            }

            solarLocationSelect.value = defaultLocationId;
            loadSolarData(defaultLocationId);
        });
