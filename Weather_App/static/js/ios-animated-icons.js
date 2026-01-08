// iOS Weather Animated Icons
class WeatherIconAnimator {
  static createAnimatedSun() {
    return `
      <svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
        <!-- Sun rays (rotating) -->
        <g class="sun-rays" style="transform-origin: center; animation: rotateSunRays 8s linear infinite;">
          <line x1="100" y1="20" x2="100" y2="40" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="141.4" y1="29.3" x2="155.6" y2="44.4" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="170.7" y1="58.6" x2="180" y2="72.8" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="180" y1="100" x2="160" y2="100" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="170.7" y1="141.4" x2="155.6" y2="155.6" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="141.4" y1="170.7" x2="127.2" y2="180" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="100" y1="180" x2="100" y2="160" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="58.6" y1="170.7" x2="44.4" y2="155.6" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="29.3" y1="141.4" x2="20" y2="127.2" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="20" y1="100" x2="40" y2="100" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="29.3" y1="58.6" x2="44.4" y2="44.4" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
          <line x1="58.6" y1="29.3" x2="72.8" y2="20" stroke="#FFD93D" stroke-width="4" stroke-linecap="round"/>
        </g>
        
        <!-- Sun circle (pulsing) -->
        <circle cx="100" cy="100" r="45" fill="url(#sunGradient)" 
                style="animation: pulseSun 3s ease-in-out infinite;"/>
        
        <defs>
          <linearGradient id="sunGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#FFF176;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#FFD93D;stop-opacity:1" />
          </linearGradient>
        </defs>
        
        <style>
          @keyframes rotateSunRays {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes pulseSun {
            0%, 100% { r: 45; opacity: 1; }
            50% { r: 48; opacity: 0.9; }
          }
        </style>
      </svg>
    `;
  }

  static createAnimatedCloud() {
    return `
      <svg width="200" height="140" viewBox="0 0 200 140" xmlns="http://www.w3.org/2000/svg">
        <g style="animation: floatCloud 4s ease-in-out infinite;">
          <ellipse cx="70" cy="80" rx="35" ry="30" fill="#E8E8E8"/>
          <ellipse cx="100" cy="70" rx="40" ry="35" fill="#F5F5F5"/>
          <ellipse cx="130" cy="80" rx="35" ry="30" fill="#E8E8E8"/>
          <rect x="50" y="80" width="100" height="35" fill="#F0F0F0"/>
        </g>
        
        <style>
          @keyframes floatCloud {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
          }
        </style>
      </svg>
    `;
  }

  static createAnimatedRain() {
    return `
      <svg width="200" height="180" viewBox="0 0 200 180" xmlns="http://www.w3.org/2000/svg">
        <!-- Cloud -->
        <g style="animation: floatCloud 4s ease-in-out infinite;">
          <ellipse cx="70" cy="60" rx="35" ry="30" fill="#9E9E9E"/>
          <ellipse cx="100" cy="50" rx="40" ry="35" fill="#B0B0B0"/>
          <ellipse cx="130" cy="60" rx="35" ry="30" fill="#9E9E9E"/>
          <rect x="50" y="60" width="100" height="35" fill="#A8A8A8"/>
        </g>
        
        <!-- Rain drops -->
        <g class="rain-drops">
          <line x1="60" y1="100" x2="55" y2="130" stroke="#4A90E2" stroke-width="3" stroke-linecap="round"
                style="animation: rainFall 1.2s linear infinite;"/>
          <line x1="85" y1="100" x2="80" y2="130" stroke="#4A90E2" stroke-width="3" stroke-linecap="round"
                style="animation: rainFall 1.2s linear infinite 0.3s;"/>
          <line x1="110" y1="100" x2="105" y2="130" stroke="#4A90E2" stroke-width="3" stroke-linecap="round"
                style="animation: rainFall 1.2s linear infinite 0.6s;"/>
          <line x1="135" y1="100" x2="130" y2="130" stroke="#4A90E2" stroke-width="3" stroke-linecap="round"
                style="animation: rainFall 1.2s linear infinite 0.9s;"/>
        </g>
        
        <style>
          @keyframes floatCloud {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-5px); }
          }
          @keyframes rainFall {
            0% { opacity: 0; transform: translateY(-10px); }
            50% { opacity: 1; }
            100% { opacity: 0; transform: translateY(40px); }
          }
        </style>
      </svg>
    `;
  }

  static createAnimatedPartlyCloudy() {
    return `
      <svg width="220" height="160" viewBox="0 0 220 160" xmlns="http://www.w3.org/2000/svg">
        <!-- Sun (behind cloud) -->
        <g style="animation: rotateSlow 12s linear infinite; transform-origin: 80px 70px;">
          <circle cx="80" cy="70" r="30" fill="#FFD93D" opacity="0.9"/>
          <line x1="80" y1="25" x2="80" y2="35" stroke="#FFD93D" stroke-width="3" stroke-linecap="round"/>
          <line x1="110" y1="40" x2="115" y2="45" stroke="#FFD93D" stroke-width="3" stroke-linecap="round"/>
          <line x1="125" y1="70" x2="135" y2="70" stroke="#FFD93D" stroke-width="3" stroke-linecap="round"/>
          <line x1="110" y1="100" x2="115" y2="95" stroke="#FFD93D" stroke-width="3" stroke-linecap="round"/>
        </g>
        
        <!-- Cloud (in front) -->
        <g style="animation: floatCloud 5s ease-in-out infinite;">
          <ellipse cx="120" cy="90" rx="35" ry="30" fill="#F5F5F5"/>
          <ellipse cx="150" cy="80" rx="40" ry="35" fill="#FFFFFF"/>
          <ellipse cx="180" cy="90" rx="35" ry="30" fill="#F5F5F5"/>
          <rect x="100" y="90" width="100" height="35" fill="#FAFAFA"/>
        </g>
        
        <style>
          @keyframes rotateSlow {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes floatCloud {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-6px); }
          }
        </style>
      </svg>
    `;
  }

  // Replace weather icons with animated versions
  static initializeAnimatedIcons() {
    document.addEventListener("DOMContentLoaded", function () {
      // Find all weather icon images
      const weatherIcons = document.querySelectorAll(".current-img, .main-img");

      weatherIcons.forEach((icon) => {
        const iconSrc = icon.getAttribute("src");
        let animatedSVG = "";

        // Determine weather condition from src or other attributes
        if (iconSrc.includes("sun") || iconSrc.includes("clear")) {
          animatedSVG = WeatherIconAnimator.createAnimatedSun();
        } else if (iconSrc.includes("rain") || iconSrc.includes("mua")) {
          animatedSVG = WeatherIconAnimator.createAnimatedRain();
        } else if (iconSrc.includes("cloud") || iconSrc.includes("may")) {
          animatedSVG = WeatherIconAnimator.createAnimatedCloud();
        } else if (iconSrc.includes("partly")) {
          animatedSVG = WeatherIconAnimator.createAnimatedPartlyCloudy();
        } else {
          // Default to sun
          animatedSVG = WeatherIconAnimator.createAnimatedSun();
        }

        // Replace image with SVG
        const wrapper = document.createElement("div");
        wrapper.innerHTML = animatedSVG;
        wrapper.style.display = "inline-block";
        wrapper.style.width = icon.width || "120px";
        wrapper.style.height = icon.height || "120px";

        icon.parentNode.replaceChild(wrapper, icon);
      });
    });
  }
}

// Auto-initialize when script loads
WeatherIconAnimator.initializeAnimatedIcons();
