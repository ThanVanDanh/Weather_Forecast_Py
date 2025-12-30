/**
 * iOS Weather App - Animated Weather Icons
 * SVG-based animated icons for weather conditions
 */

// Create animated weather icons dynamically
class WeatherIconAnimator {
  constructor() {
    this.icons = {
      sun: this.createSunIcon,
      moon: this.createMoonIcon,
      cloud: this.createCloudIcon,
      rain: this.createRainIcon,
      snow: this.createSnowIcon,
      thunderstorm: this.createThunderstormIcon,
      cloudy: this.createCloudyIcon,
      partlyCloudy: this.createPartlyCloudyIcon,
      fog: this.createFogIcon,
      wind: this.createWindIcon,
    };
  }

  createSunIcon() {
    return `
            <div class="weather-icon-animated sun-icon">
                <svg width="120" height="120" viewBox="0 0 120 120">
                    <!-- Sun rays -->
                    <g class="sun-rays">
                        <line x1="60" y1="10" x2="60" y2="25" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                        <line x1="60" y1="95" x2="60" y2="110" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                        <line x1="10" y1="60" x2="25" y2="60" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                        <line x1="95" y1="60" x2="110" y2="60" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                        <line x1="25" y1="25" x2="35" y2="35" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                        <line x1="85" y1="85" x2="95" y2="95" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                        <line x1="25" y1="95" x2="35" y2="85" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                        <line x1="85" y1="35" x2="95" y2="25" stroke="rgba(255, 220, 100, 0.8)" stroke-width="3" stroke-linecap="round"/>
                    </g>
                    <!-- Sun circle -->
                    <circle cx="60" cy="60" r="25" fill="url(#sunGradient)">
                        <animate attributeName="r" values="25;27;25" dur="3s" repeatCount="indefinite"/>
                    </circle>
                    <defs>
                        <radialGradient id="sunGradient">
                            <stop offset="0%" style="stop-color:#FFE484;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#FFC837;stop-opacity:1" />
                        </radialGradient>
                    </defs>
                </svg>
                <style>
                    .sun-rays { 
                        animation: rotate 30s linear infinite; 
                        transform-origin: center;
                    }
                </style>
            </div>
        `;
  }

  createMoonIcon() {
    return `
            <div class="weather-icon-animated moon-icon">
                <svg width="120" height="120" viewBox="0 0 120 120">
                    <path d="M 60 20 A 40 40 0 1 0 60 100 A 30 30 0 1 1 60 20" 
                          fill="url(#moonGradient)" opacity="0.95">
                        <animate attributeName="opacity" values="0.95;1;0.95" dur="4s" repeatCount="indefinite"/>
                    </path>
                    <defs>
                        <radialGradient id="moonGradient">
                            <stop offset="0%" style="stop-color:#F0E68C;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#E6D96F;stop-opacity:1" />
                        </radialGradient>
                    </defs>
                </svg>
            </div>
        `;
  }

  createCloudIcon() {
    return `
            <div class="weather-icon-animated cloud-icon cloud-float">
                <svg width="120" height="80" viewBox="0 0 120 80">
                    <path d="M 30 50 Q 30 35 45 35 Q 50 25 60 25 Q 75 25 80 35 Q 95 35 95 50 Q 95 65 80 65 L 40 65 Q 30 65 30 50" 
                          fill="url(#cloudGradient)" opacity="0.95"/>
                    <defs>
                        <linearGradient id="cloudGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#FFFFFF;stop-opacity:0.95" />
                            <stop offset="100%" style="stop-color:#E8E8E8;stop-opacity:0.95" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
        `;
  }

  createRainIcon() {
    return `
            <div class="weather-icon-animated rain-icon">
                <svg width="120" height="120" viewBox="0 0 120 120">
                    <!-- Cloud -->
                    <path d="M 30 40 Q 30 25 45 25 Q 50 15 60 15 Q 75 15 80 25 Q 95 25 95 40 Q 95 55 80 55 L 40 55 Q 30 55 30 40" 
                          fill="url(#rainCloudGradient)" opacity="0.9"/>
                    <!-- Rain drops -->
                    <g class="rain-drops">
                        <line x1="40" y1="65" x2="38" y2="85" stroke="#4A90E2" stroke-width="2.5" stroke-linecap="round" opacity="0.8">
                            <animate attributeName="y1" values="65;75;65" dur="1s" repeatCount="indefinite"/>
                            <animate attributeName="y2" values="85;95;85" dur="1s" repeatCount="indefinite"/>
                        </line>
                        <line x1="55" y1="65" x2="53" y2="85" stroke="#4A90E2" stroke-width="2.5" stroke-linecap="round" opacity="0.8">
                            <animate attributeName="y1" values="65;75;65" dur="1s" begin="0.2s" repeatCount="indefinite"/>
                            <animate attributeName="y2" values="85;95;85" dur="1s" begin="0.2s" repeatCount="indefinite"/>
                        </line>
                        <line x1="70" y1="65" x2="68" y2="85" stroke="#4A90E2" stroke-width="2.5" stroke-linecap="round" opacity="0.8">
                            <animate attributeName="y1" values="65;75;65" dur="1s" begin="0.4s" repeatCount="indefinite"/>
                            <animate attributeName="y2" values="85;95;85" dur="1s" begin="0.4s" repeatCount="indefinite"/>
                        </line>
                    </g>
                    <defs>
                        <linearGradient id="rainCloudGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#B0C4D4;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#8BA6BD;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
        `;
  }

  createSnowIcon() {
    return `
            <div class="weather-icon-animated snow-icon">
                <svg width="120" height="120" viewBox="0 0 120 120">
                    <!-- Cloud -->
                    <path d="M 30 40 Q 30 25 45 25 Q 50 15 60 15 Q 75 15 80 25 Q 95 25 95 40 Q 95 55 80 55 L 40 55 Q 30 55 30 40" 
                          fill="url(#snowCloudGradient)" opacity="0.9"/>
                    <!-- Snowflakes -->
                    <g class="snowflakes">
                        <g transform="translate(40, 70)">
                            <circle cx="0" cy="0" r="3" fill="white" opacity="0.9">
                                <animate attributeName="cy" values="0;20;0" dur="2s" repeatCount="indefinite"/>
                                <animate attributeName="opacity" values="0.9;0.5;0.9" dur="2s" repeatCount="indefinite"/>
                            </circle>
                        </g>
                        <g transform="translate(60, 70)">
                            <circle cx="0" cy="0" r="3" fill="white" opacity="0.9">
                                <animate attributeName="cy" values="0;20;0" dur="2s" begin="0.5s" repeatCount="indefinite"/>
                                <animate attributeName="opacity" values="0.9;0.5;0.9" dur="2s" begin="0.5s" repeatCount="indefinite"/>
                            </circle>
                        </g>
                        <g transform="translate(80, 70)">
                            <circle cx="0" cy="0" r="3" fill="white" opacity="0.9">
                                <animate attributeName="cy" values="0;20;0" dur="2s" begin="1s" repeatCount="indefinite"/>
                                <animate attributeName="opacity" values="0.9;0.5;0.9" dur="2s" begin="1s" repeatCount="indefinite"/>
                            </circle>
                        </g>
                    </g>
                    <defs>
                        <linearGradient id="snowCloudGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#E0E7EF;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#C5D5E4;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
        `;
  }

  createThunderstormIcon() {
    return `
            <div class="weather-icon-animated thunderstorm-icon">
                <svg width="120" height="140" viewBox="0 0 120 140">
                    <!-- Dark cloud -->
                    <path d="M 30 40 Q 30 25 45 25 Q 50 15 60 15 Q 75 15 80 25 Q 95 25 95 40 Q 95 55 80 55 L 40 55 Q 30 55 30 40" 
                          fill="url(#stormCloudGradient)" opacity="0.95"/>
                    <!-- Lightning bolt -->
                    <path d="M 65 55 L 55 80 L 65 80 L 55 105" 
                          stroke="#FFE484" 
                          stroke-width="3" 
                          fill="none" 
                          stroke-linecap="round"
                          stroke-linejoin="round">
                        <animate attributeName="opacity" values="0;1;0;1;0" dur="2s" repeatCount="indefinite"/>
                    </path>
                    <!-- Rain -->
                    <line x1="40" y1="60" x2="38" y2="75" stroke="#4A90E2" stroke-width="2" opacity="0.7">
                        <animate attributeName="y1" values="60;70;60" dur="0.8s" repeatCount="indefinite"/>
                        <animate attributeName="y2" values="75;85;75" dur="0.8s" repeatCount="indefinite"/>
                    </line>
                    <line x1="75" y1="60" x2="73" y2="75" stroke="#4A90E2" stroke-width="2" opacity="0.7">
                        <animate attributeName="y1" values="60;70;60" dur="0.8s" begin="0.3s" repeatCount="indefinite"/>
                        <animate attributeName="y2" values="75;85;75" dur="0.8s" begin="0.3s" repeatCount="indefinite"/>
                    </line>
                    <defs>
                        <linearGradient id="stormCloudGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#4A5F7A;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#3D5266;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
        `;
  }

  createPartlyCloudyIcon() {
    return `
            <div class="weather-icon-animated partly-cloudy-icon">
                <svg width="120" height="100" viewBox="0 0 120 100">
                    <!-- Sun -->
                    <g transform="translate(25, -10)">
                        <circle cx="35" cy="35" r="18" fill="url(#sunGradient2)">
                            <animate attributeName="r" values="18;20;18" dur="3s" repeatCount="indefinite"/>
                        </circle>
                        <g class="sun-rays" transform="translate(35, 35)">
                            <line x1="0" y1="-28" x2="0" y2="-35" stroke="rgba(255, 220, 100, 0.8)" stroke-width="2"/>
                            <line x1="20" y1="-20" x2="25" y2="-25" stroke="rgba(255, 220, 100, 0.8)" stroke-width="2"/>
                            <line x1="28" y1="0" x2="35" y2="0" stroke="rgba(255, 220, 100, 0.8)" stroke-width="2"/>
                        </g>
                    </g>
                    <!-- Cloud -->
                    <g class="cloud-float" transform="translate(10, 20)">
                        <path d="M 30 50 Q 30 35 45 35 Q 50 25 60 25 Q 75 25 80 35 Q 95 35 95 50 Q 95 65 80 65 L 40 65 Q 30 65 30 50" 
                              fill="url(#cloudGradient2)" opacity="0.95"/>
                    </g>
                    <defs>
                        <radialGradient id="sunGradient2">
                            <stop offset="0%" style="stop-color:#FFE484;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#FFC837;stop-opacity:1" />
                        </radialGradient>
                        <linearGradient id="cloudGradient2" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#FFFFFF;stop-opacity:0.95" />
                            <stop offset="100%" style="stop-color:#E8E8E8;stop-opacity:0.95" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
        `;
  }

  createFogIcon() {
    return `
            <div class="weather-icon-animated fog-icon">
                <svg width="120" height="100" viewBox="0 0 120 100">
                    <g opacity="0.7">
                        <line x1="20" y1="30" x2="100" y2="30" stroke="#B0B0B0" stroke-width="4" stroke-linecap="round">
                            <animate attributeName="x2" values="100;90;100" dur="4s" repeatCount="indefinite"/>
                        </line>
                        <line x1="15" y1="45" x2="105" y2="45" stroke="#B0B0B0" stroke-width="4" stroke-linecap="round">
                            <animate attributeName="x2" values="105;95;105" dur="4s" begin="0.5s" repeatCount="indefinite"/>
                        </line>
                        <line x1="20" y1="60" x2="100" y2="60" stroke="#B0B0B0" stroke-width="4" stroke-linecap="round">
                            <animate attributeName="x2" values="100;90;100" dur="4s" begin="1s" repeatCount="indefinite"/>
                        </line>
                        <line x1="25" y1="75" x2="95" y2="75" stroke="#B0B0B0" stroke-width="4" stroke-linecap="round">
                            <animate attributeName="x2" values="95;85;95" dur="4s" begin="1.5s" repeatCount="indefinite"/>
                        </line>
                    </g>
                </svg>
            </div>
        `;
  }

  createWindIcon() {
    return `
            <div class="weather-icon-animated wind-icon">
                <svg width="120" height="100" viewBox="0 0 120 100">
                    <g>
                        <path d="M 20 30 Q 40 20 60 30 Q 80 40 100 30" 
                              stroke="#4A90E2" 
                              stroke-width="3" 
                              fill="none" 
                              stroke-linecap="round">
                            <animate attributeName="d" 
                                     values="M 20 30 Q 40 20 60 30 Q 80 40 100 30;
                                             M 20 30 Q 40 40 60 30 Q 80 20 100 30;
                                             M 20 30 Q 40 20 60 30 Q 80 40 100 30" 
                                     dur="2s" 
                                     repeatCount="indefinite"/>
                        </path>
                        <path d="M 15 50 Q 35 40 55 50 Q 75 60 95 50" 
                              stroke="#4A90E2" 
                              stroke-width="3" 
                              fill="none" 
                              stroke-linecap="round">
                            <animate attributeName="d" 
                                     values="M 15 50 Q 35 40 55 50 Q 75 60 95 50;
                                             M 15 50 Q 35 60 55 50 Q 75 40 95 50;
                                             M 15 50 Q 35 40 55 50 Q 75 60 95 50" 
                                     dur="2s" 
                                     begin="0.3s"
                                     repeatCount="indefinite"/>
                        </path>
                        <path d="M 20 70 Q 40 60 60 70 Q 80 80 100 70" 
                              stroke="#4A90E2" 
                              stroke-width="3" 
                              fill="none" 
                              stroke-linecap="round">
                            <animate attributeName="d" 
                                     values="M 20 70 Q 40 60 60 70 Q 80 80 100 70;
                                             M 20 70 Q 40 80 60 70 Q 80 60 100 70;
                                             M 20 70 Q 40 60 60 70 Q 80 80 100 70" 
                                     dur="2s" 
                                     begin="0.6s"
                                     repeatCount="indefinite"/>
                        </path>
                    </g>
                </svg>
            </div>
        `;
  }

  createCloudyIcon() {
    return `
            <div class="weather-icon-animated cloudy-icon">
                <svg width="120" height="100" viewBox="0 0 120 100">
                    <!-- Back cloud -->
                    <g class="cloud-float" opacity="0.7" transform="translate(5, 10)">
                        <path d="M 25 45 Q 25 30 40 30 Q 45 20 55 20 Q 70 20 75 30 Q 90 30 90 45 Q 90 60 75 60 L 35 60 Q 25 60 25 45" 
                              fill="url(#cloudGradient3)"/>
                    </g>
                    <!-- Front cloud -->
                    <g class="cloud-float" transform="translate(15, 25)">
                        <path d="M 25 45 Q 25 30 40 30 Q 45 20 55 20 Q 70 20 75 30 Q 90 30 90 45 Q 90 60 75 60 L 35 60 Q 25 60 25 45" 
                              fill="url(#cloudGradient4)"/>
                    </g>
                    <defs>
                        <linearGradient id="cloudGradient3" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#D0D0D0;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#B8B8B8;stop-opacity:1" />
                        </linearGradient>
                        <linearGradient id="cloudGradient4" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#FFFFFF;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#E0E0E0;stop-opacity:1" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
        `;
  }

  getIcon(weatherCondition) {
    const condition = weatherCondition.toLowerCase();

    if (condition.includes("thunder") || condition.includes("storm")) {
      return this.createThunderstormIcon();
    } else if (condition.includes("rain") || condition.includes("drizzle")) {
      return this.createRainIcon();
    } else if (condition.includes("snow")) {
      return this.createSnowIcon();
    } else if (
      condition.includes("fog") ||
      condition.includes("mist") ||
      condition.includes("haze")
    ) {
      return this.createFogIcon();
    } else if (condition.includes("wind")) {
      return this.createWindIcon();
    } else if (condition.includes("cloud")) {
      if (condition.includes("few") || condition.includes("scattered")) {
        return this.createPartlyCloudyIcon();
      } else {
        return this.createCloudyIcon();
      }
    } else if (condition.includes("clear") || condition.includes("sun")) {
      const hour = new Date().getHours();
      if (hour >= 6 && hour < 18) {
        return this.createSunIcon();
      } else {
        return this.createMoonIcon();
      }
    }

    // Default to cloudy
    return this.createCloudyIcon();
  }
}

// Export for use in other scripts
if (typeof module !== "undefined" && module.exports) {
  module.exports = WeatherIconAnimator;
}
