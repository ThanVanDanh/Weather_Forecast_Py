/**
 * iOS Weather App - Main Application JavaScript
 * Handles dynamic content loading, animations, and interactions
 */

class iOSWeatherApp {
  constructor() {
    this.iconAnimator = new WeatherIconAnimator();
    this.currentWeatherData = null;
    this.init();
  }

  init() {
    console.log("iOS Weather App initialized");
    this.loadCurrentWeather();
    this.setupBackgroundUpdater();
  }

  /**
   * Load current weather data
   */
  async loadCurrentWeather() {
    try {
      // Replace with your actual API endpoint
      // For demonstration, using mock data
      const response = await this.fetchWeatherData();
      this.currentWeatherData = response;
      this.updateUI(response);
    } catch (error) {
      console.error("Error loading weather:", error);
      this.showError();
    }
  }

  /**
   * Fetch weather data from API
   */
  async fetchWeatherData() {
    // TODO: Replace with actual API call
    // For now, return mock data for demonstration
    return {
      location: "Hồ Chí Minh",
      current: {
        temp: 32,
        feels_like: 35,
        temp_min: 28,
        temp_max: 34,
        humidity: 75,
        pressure: 1013,
        visibility: 10,
        wind_speed: 12,
        wind_deg: 180,
        uvi: 8,
        weather: [
          {
            main: "Clear",
            description: "Trời quang đãng",
            icon: "01d",
          },
        ],
        dt: Date.now() / 1000,
      },
      hourly: this.generateMockHourlyData(),
      daily: this.generateMockDailyData(),
    };
  }

  /**
   * Update UI with weather data
   */
  updateUI(data) {
    this.updateCurrentWeather(data.current, data.location);
    this.updateHourlyForecast(data.hourly);
    this.updateDailyForecast(data.daily);
    this.updateWeatherDetails(data.current);
    this.updateBackground(data.current.weather[0].main, data.current.dt);
  }

  /**
   * Update current weather display
   */
  updateCurrentWeather(current, location) {
    // Location
    const cityName = document.getElementById("current-city-name");
    if (cityName) cityName.textContent = location;

    // Temperature
    const tempDisplay = document.getElementById("current-temp-large");
    if (tempDisplay) {
      tempDisplay.innerHTML = `${Math.round(current.temp)}<sup>°</sup>`;
    }

    // Description
    const description = document.getElementById("current-description");
    if (description) {
      description.textContent = current.weather[0].description;
    }

    // Temp Range
    const tempHigh = document.getElementById("temp-high-main");
    const tempLow = document.getElementById("temp-low-main");
    if (tempHigh) tempHigh.textContent = `${Math.round(current.temp_max)}°`;
    if (tempLow) tempLow.textContent = `${Math.round(current.temp_min)}°`;

    // Animated Icon
    this.updateAnimatedIcon(current.weather[0].main);

    // Animate elements
    this.animateEntry();
  }

  /**
   * Update animated weather icon
   */
  updateAnimatedIcon(weatherCondition) {
    const container = document.getElementById("animated-icon-container");
    if (!container) return;

    const iconHTML = this.iconAnimator.getIcon(weatherCondition);
    container.innerHTML = iconHTML;
    container.classList.add("ios-fade-in");
  }

  /**
   * Update hourly forecast
   */
  updateHourlyForecast(hourly) {
    const container = document.getElementById("hourly-forecast-container");
    if (!container) return;

    container.innerHTML = "";

    hourly.slice(0, 24).forEach((hour, index) => {
      const hourItem = this.createHourlyItem(hour, index);
      container.appendChild(hourItem);
    });

    // Add horizontal scroll indicator
    this.addScrollIndicator(container);
  }

  /**
   * Create hourly forecast item
   */
  createHourlyItem(hourData, index) {
    const div = document.createElement("div");
    div.className = "ios-hour-item";
    div.style.animationDelay = `${index * 0.05}s`;

    const time = new Date(hourData.dt * 1000);
    const timeString = index === 0 ? "Bây giờ" : time.getHours() + ":00";

    div.innerHTML = `
            <div class="ios-hour-time">${timeString}</div>
            <i class="fas ${this.getWeatherIcon(
              hourData.weather[0].main
            )}" style="font-size: 32px;"></i>
            ${
              hourData.pop > 0
                ? `<div class="ios-hour-rain"><i class="fas fa-droplet"></i> ${Math.round(
                    hourData.pop * 100
                  )}%</div>`
                : ""
            }
            <div class="ios-hour-temp">${Math.round(hourData.temp)}°</div>
        `;

    return div;
  }

  /**
   * Update daily forecast
   */
  updateDailyForecast(daily) {
    const container = document.getElementById("daily-forecast-container");
    if (!container) return;

    container.innerHTML = "";

    daily.slice(0, 7).forEach((day, index) => {
      const dayItem = this.createDailyItem(day, index);
      container.appendChild(dayItem);
    });
  }

  /**
   * Create daily forecast item
   */
  createDailyItem(dayData, index) {
    const div = document.createElement("div");
    div.className = "ios-day-item";
    div.style.animationDelay = `${index * 0.1}s`;

    const date = new Date(dayData.dt * 1000);
    const dayName = index === 0 ? "Hôm nay" : this.getDayName(date.getDay());

    const tempRange = dayData.temp.max - dayData.temp.min;
    const tempPercentage = ((dayData.temp.max - dayData.temp.min) / 30) * 100;

    div.innerHTML = `
            <div class="ios-day-name">${dayName}</div>
            <i class="fas ${this.getWeatherIcon(
              dayData.weather[0].main
            )} ios-day-icon" style="font-size: 28px;"></i>
            ${
              dayData.pop > 0
                ? `<div class="ios-day-rain"><i class="fas fa-droplet"></i> ${Math.round(
                    dayData.pop * 100
                  )}%</div>`
                : '<div style="width: 50px;"></div>'
            }
            <div class="ios-day-temp-range">
                <div class="ios-temp-low">${Math.round(dayData.temp.min)}°</div>
                <div class="ios-temp-bar" style="width: ${Math.max(
                  60,
                  tempPercentage
                )}px;"></div>
                <div class="ios-temp-high">${Math.round(
                  dayData.temp.max
                )}°</div>
            </div>
        `;

    return div;
  }

  /**
   * Update weather details
   */
  updateWeatherDetails(current) {
    // UV Index
    const uvValue = document.getElementById("detail-uv");
    const uvDesc = document.getElementById("detail-uv-desc");
    const uvIndicator = document.getElementById("uv-indicator");

    if (uvValue && current.uvi !== undefined) {
      uvValue.textContent = Math.round(current.uvi);
      const uvInfo = this.getUVInfo(current.uvi);
      if (uvDesc) uvDesc.textContent = uvInfo.description;
      if (uvIndicator) {
        uvIndicator.style.left = `${Math.min((current.uvi / 11) * 100, 100)}%`;
      }
    }

    // Wind
    const windValue = document.getElementById("detail-wind");
    const windDirection = document.getElementById("detail-wind-direction");
    if (windValue)
      windValue.textContent = `${Math.round(current.wind_speed)} km/h`;
    if (windDirection)
      windDirection.textContent = this.getWindDirection(current.wind_deg);

    // Humidity
    const humidity = document.getElementById("detail-humidity");
    if (humidity) humidity.textContent = `${current.humidity}%`;

    // Feels Like
    const feelsLike = document.getElementById("detail-feels-like");
    const feelsDesc = document.getElementById("detail-feels-desc");
    if (feelsLike) feelsLike.textContent = `${Math.round(current.feels_like)}°`;
    if (feelsDesc) {
      const diff = current.feels_like - current.temp;
      if (diff > 2) feelsDesc.textContent = "Nóng hơn nhiệt độ thực tế";
      else if (diff < -2) feelsDesc.textContent = "Lạnh hơn nhiệt độ thực tế";
      else feelsDesc.textContent = "Tương tự nhiệt độ thực tế";
    }

    // Visibility
    const visibility = document.getElementById("detail-visibility");
    const visibilityDesc = document.getElementById("detail-visibility-desc");
    if (visibility)
      visibility.textContent = `${(current.visibility / 1000).toFixed(1)} km`;
    if (visibilityDesc) {
      const vis = current.visibility / 1000;
      if (vis >= 10) visibilityDesc.textContent = "Tầm nhìn tuyệt vời";
      else if (vis >= 5) visibilityDesc.textContent = "Tầm nhìn khá tốt";
      else visibilityDesc.textContent = "Tầm nhìn hạn chế";
    }

    // Pressure
    const pressure = document.getElementById("detail-pressure");
    if (pressure) pressure.textContent = `${current.pressure} hPa`;
  }

  /**
   * Update background based on weather condition
   */
  updateBackground(weatherCondition, timestamp) {
    const bg = document.getElementById("weatherBg");
    if (!bg) return;

    // Remove all weather classes
    bg.classList.remove(
      "clear-day",
      "clear-night",
      "clouds",
      "rain",
      "snow",
      "sunset"
    );

    // Determine time of day
    const hour = new Date(timestamp * 1000).getHours();
    const isNight = hour < 6 || hour >= 18;
    const isSunset = hour >= 17 && hour < 19;

    // Apply appropriate class
    const condition = weatherCondition.toLowerCase();

    if (isSunset && condition.includes("clear")) {
      bg.classList.add("sunset");
    } else if (condition.includes("clear")) {
      bg.classList.add(isNight ? "clear-night" : "clear-day");
    } else if (
      condition.includes("rain") ||
      condition.includes("drizzle") ||
      condition.includes("thunder")
    ) {
      bg.classList.add("rain");
    } else if (condition.includes("snow")) {
      bg.classList.add("snow");
    } else if (condition.includes("cloud")) {
      bg.classList.add("clouds");
    } else {
      bg.classList.add("clear-day");
    }
  }

  /**
   * Setup background auto-updater
   */
  setupBackgroundUpdater() {
    // Update background every minute to handle time-based changes
    setInterval(() => {
      if (this.currentWeatherData) {
        this.updateBackground(
          this.currentWeatherData.current.weather[0].main,
          Date.now() / 1000
        );
      }
    }, 60000); // Every minute
  }

  /**
   * Animate entry of elements
   */
  animateEntry() {
    const elements = document.querySelectorAll(".ios-fade-in, .ios-slide-up");
    elements.forEach((el, index) => {
      el.style.animationDelay = `${index * 0.1}s`;
    });
  }

  /**
   * Add scroll indicator for horizontal scroll
   */
  addScrollIndicator(container) {
    container.addEventListener("scroll", () => {
      // Could add visual feedback for scrolling
    });
  }

  /**
   * Get UV index information
   */
  getUVInfo(uvi) {
    if (uvi <= 2) return { description: "Thấp", color: "#3EA72D" };
    if (uvi <= 5) return { description: "Trung bình", color: "#FFF300" };
    if (uvi <= 7) return { description: "Cao", color: "#F18B00" };
    if (uvi <= 10) return { description: "Rất cao", color: "#E53210" };
    return { description: "Cực kỳ cao", color: "#B54596" };
  }

  /**
   * Get wind direction
   */
  getWindDirection(degrees) {
    const directions = [
      "Bắc",
      "Đông Bắc",
      "Đông",
      "Đông Nam",
      "Nam",
      "Tây Nam",
      "Tây",
      "Tây Bắc",
    ];
    const index = Math.round(degrees / 45) % 8;
    return directions[index];
  }

  /**
   * Get day name in Vietnamese
   */
  getDayName(dayIndex) {
    const days = [
      "Chủ nhật",
      "Thứ 2",
      "Thứ 3",
      "Thứ 4",
      "Thứ 5",
      "Thứ 6",
      "Thứ 7",
    ];
    return days[dayIndex];
  }

  /**
   * Get Font Awesome icon class for weather condition
   */
  getWeatherIcon(condition) {
    const icons = {
      Clear: "fa-sun",
      Clouds: "fa-cloud",
      Rain: "fa-cloud-rain",
      Drizzle: "fa-cloud-drizzle",
      Thunderstorm: "fa-cloud-bolt",
      Snow: "fa-snowflake",
      Mist: "fa-smog",
      Fog: "fa-smog",
      Haze: "fa-smog",
    };
    return icons[condition] || "fa-cloud";
  }

  /**
   * Generate mock hourly data for demonstration
   */
  generateMockHourlyData() {
    const hourly = [];
    const baseTemp = 28;
    const now = Date.now() / 1000;

    for (let i = 0; i < 24; i++) {
      const variance = Math.sin(((i - 6) * Math.PI) / 12) * 4;
      hourly.push({
        dt: now + i * 3600,
        temp: baseTemp + variance + (Math.random() * 2 - 1),
        feels_like: baseTemp + variance + 2,
        humidity: 70 + Math.random() * 20,
        pop: i > 12 && i < 18 ? Math.random() * 0.5 : Math.random() * 0.2,
        weather: [
          {
            main: i > 12 && i < 18 ? "Rain" : i % 3 === 0 ? "Clouds" : "Clear",
            description: "Mô tả thời tiết",
          },
        ],
      });
    }
    return hourly;
  }

  /**
   * Generate mock daily data for demonstration
   */
  generateMockDailyData() {
    const daily = [];
    const baseTemp = 28;
    const now = Date.now() / 1000;

    for (let i = 0; i < 7; i++) {
      const variance = Math.random() * 4 - 2;
      daily.push({
        dt: now + i * 86400,
        temp: {
          min: baseTemp + variance - 3,
          max: baseTemp + variance + 5,
        },
        humidity: 70 + Math.random() * 20,
        pop: Math.random() * 0.6,
        weather: [
          {
            main: i % 3 === 0 ? "Rain" : i % 2 === 0 ? "Clouds" : "Clear",
            description: "Mô tả thời tiết",
          },
        ],
      });
    }
    return daily;
  }

  /**
   * Show error message
   */
  showError() {
    const cityName = document.getElementById("current-city-name");
    if (cityName) {
      cityName.textContent = "Không thể tải dữ liệu thời tiết";
    }
  }
}

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.weatherApp = new iOSWeatherApp();
});

// Handle page visibility changes
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && window.weatherApp) {
    window.weatherApp.loadCurrentWeather();
  }
});
