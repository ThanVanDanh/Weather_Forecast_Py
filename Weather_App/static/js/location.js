console.log("location.js loaded (Browser GPS mode)");

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btn-locate");
  const cityEl = document.getElementById("current-city");
  if (!btn || !cityEl) return;

  btn.addEventListener("click", async (e) => {
    e.preventDefault();

    // Thay đổi text nút để báo đang xử lý
    const originalText = btn.innerText;
    btn.innerText = "Đang định vị...";
    btn.disabled = true;

    // Kiểm tra trình duyệt có hỗ trợ Geolocation không
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        // Thành công - có tọa độ GPS
        async (position) => {
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;
          console.log("GPS coordinates:", lat, lon);
          await sendLocationToServer(lat, lon);
          btn.innerText = originalText;
          btn.disabled = false;
        },
        // Lỗi hoặc người dùng từ chối
        async (error) => {
          console.warn("Geolocation error:", error.message);
          alert("Không thể lấy vị trí GPS. Vui lòng cho phép truy cập vị trí trong trình duyệt.");
          btn.innerText = originalText;
          btn.disabled = false;
        },
        // Options
        {
          enableHighAccuracy: true, // Độ chính xác cao (GPS)
          timeout: 10000,           // Timeout 10 giây
          maximumAge: 0             // Không dùng cache
        }
      );
    } else {
      alert("Trình duyệt không hỗ trợ định vị GPS.");
      btn.innerText = originalText;
      btn.disabled = false;
    }
  });
  if (cityEl.innerText.trim().includes("Chưa xác định") || cityEl.innerText.trim() === "") {
    console.log("Auto-locating user...");
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const lat = position.coords.latitude;
          const lon = position.coords.longitude;
          console.log("Auto-GPS coordinates:", lat, lon);
          await sendLocationToServer(lat, lon);
        },
        (error) => {
          console.log("Auto-location failed (silent):", error.message);
        }
      );
    }
  }
  // Helper để lấy cookie CSRF
  function getCookie(name) {
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

  // Gửi tọa độ GPS lên Server
  async function sendLocationToServer(lat, lon) {
    const csrftoken = getCookie('csrftoken');

    try {
      const res = await fetch("/api/weather/locate/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken
        },
        body: JSON.stringify({ latitude: lat, longitude: lon })
      });

      const data = await res.json();

      if (!res.ok || !data.ok) {
        alert(data.error || "Không xác định được vị trí");
        return;
      }

      // Hiển thị tên thành phố
      cityEl.innerText = data.city;
      console.log("Location found:", data);

      // Phát sự kiện để các trang khác (như Customer Care) bắt được
      const event = new CustomEvent('weatherLocationUpdated', { detail: data });
      document.dispatchEvent(event);

    } catch (err) {
      console.error(err);
      alert("Lỗi kết nối đến server");
    }
  }
});
// tìm kiếm tên thành phố
document.addEventListener('DOMContentLoaded', function () {
  const searchInput = document.getElementById('search-province-input');
  const searchBtn = document.getElementById('search-province-btn');
  const suggestionsBox = document.getElementById('search-suggestions');

  if (!searchInput || !suggestionsBox) return;

  let allLocations = [];
  let debounceTimer;

  // Load tất cả locations một lần
  async function loadAllLocations() {
    try {
      const response = await fetch('/api/weather/locations/');
      if (response.ok) {
        allLocations = await response.json();
      }
    } catch (error) {
      console.error('Lỗi tải danh sách địa điểm:', error);
    }
  }

  // Tạo slug từ tên tỉnh
  function createSlug(name) {
    return name.toLowerCase()
      .replace(/đ/g, 'd')
      .replace(/[áàảãạăắằẳẵặâấầẩẫậ]/g, 'a')
      .replace(/[éèẻẽẹêếềểễệ]/g, 'e')
      .replace(/[íìỉĩị]/g, 'i')
      .replace(/[óòỏõọôốồổỗộơớờởỡợ]/g, 'o')
      .replace(/[úùủũụưứừửữự]/g, 'u')
      .replace(/[ýỳỷỹỵ]/g, 'y')
      .replace(/\s+/g, '-')
      .replace(/[^\w-]/g, '');
  }

  // Lọc và hiển thị gợi ý
  function showSuggestions(query) {
    if (!query || query.length < 1) {
      suggestionsBox.style.display = 'none';
      return;
    }

    const normalizedQuery = query.toLowerCase()
      .replace(/đ/g, 'd')
      .replace(/[áàảãạăắằẳẵặâấầẩẫậ]/g, 'a')
      .replace(/[éèẻẽẹêếềểễệ]/g, 'e')
      .replace(/[íìỉĩị]/g, 'i')
      .replace(/[óòỏõọôốồổỗộơớờởỡợ]/g, 'o')
      .replace(/[úùủũụưứừửữự]/g, 'u')
      .replace(/[ýỳỷỹỵ]/g, 'y');

    const filtered = allLocations.filter(loc => {
      const nameVn = (loc.city_name_vn || '').toLowerCase();
      const nameEn = (loc.city_name || '').toLowerCase();
      const normalizedVn = nameVn
        .replace(/đ/g, 'd')
        .replace(/[áàảãạăắằẳẵặâấầẩẫậ]/g, 'a')
        .replace(/[éèẻẽẹêếềểễệ]/g, 'e')
        .replace(/[íìỉĩị]/g, 'i')
        .replace(/[óòỏõọôốồổỗộơớờởỡợ]/g, 'o')
        .replace(/[úùủũụưứừửữự]/g, 'u')
        .replace(/[ýỳỷỹỵ]/g, 'y');

      return normalizedVn.includes(normalizedQuery) ||
        nameEn.includes(normalizedQuery) ||
        nameVn.includes(query.toLowerCase());
    });

    if (filtered.length === 0) {
      suggestionsBox.innerHTML = '<div class="no-result">Không tìm thấy tỉnh/thành phố</div>';
    } else {
      suggestionsBox.innerHTML = filtered.map(loc => {
        const displayName = loc.city_name_vn || loc.city_name;
        return `<div class="suggestion-item" data-city="${loc.city_name}" data-id="${loc.id}">
                    <i class="fa-solid fa-location-dot"></i>${displayName}
                </div>`;
      }).join('');
    }

    suggestionsBox.style.display = 'block';
  }

  // Chuyển hướng đến trang tỉnh (và lưu lịch sử tìm kiếm)
  function goToProvince(cityName, locationId = null) {
    // Lưu lịch sử tìm kiếm trước khi chuyển trang
    if (locationId) {
      saveSearchHistoryBeforeNavigate(locationId, cityName);
    }

    const slug = createSlug(cityName);
    window.location.href = `/tinh/${slug}/`;
  }

  // Lưu lịch sử tìm kiếm vào localStorage (để sync lên DB sau)
  function saveSearchHistoryBeforeNavigate(locationId, cityName) {
    const historyItem = {
      locationId: locationId,
      cityName: cityName,
      temperature: null,  // Sẽ được cập nhật khi sync
      weatherCode: 1,
      isDay: 1,
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
    console.log('[Search History] Saved to localStorage before navigate:', historyItem);
  }

  // Event: Nhập text
  searchInput.addEventListener('input', function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      showSuggestions(this.value.trim());
    }, 200);
  });

  // Event: Focus vào input
  searchInput.addEventListener('focus', function () {
    if (this.value.trim().length > 0) {
      showSuggestions(this.value.trim());
    }
  });

  // Event: Click vào gợi ý
  suggestionsBox.addEventListener('click', function (e) {
    const item = e.target.closest('.suggestion-item');
    if (item) {
      const cityName = item.dataset.city;
      const locationId = parseInt(item.dataset.id);
      goToProvince(cityName, locationId);
    }
  });

  // Event: Nhấn Enter
  searchInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      const firstItem = suggestionsBox.querySelector('.suggestion-item');
      if (firstItem) {
        const locationId = parseInt(firstItem.dataset.id);
        goToProvince(firstItem.dataset.city, locationId);
      }
    }
  });

  // Event: Click nút tìm kiếm
  searchBtn.addEventListener('click', function () {
    const query = searchInput.value.trim();
    if (query) {
      const firstItem = suggestionsBox.querySelector('.suggestion-item');
      if (firstItem) {
        const locationId = parseInt(firstItem.dataset.id);
        goToProvince(firstItem.dataset.city, locationId);
      } else {
        // Thử tìm kiếm trực tiếp
        const matched = allLocations.find(loc => {
          const nameVn = (loc.city_name_vn || '').toLowerCase();
          const nameEn = (loc.city_name || '').toLowerCase();
          return nameVn.includes(query.toLowerCase()) || nameEn.includes(query.toLowerCase());
        });
        if (matched) {
          goToProvince(matched.city_name, matched.id);
        } else {
          alert('Không tìm thấy tỉnh/thành phố: ' + query);
        }
      }
    }
  });

  // Event: Click ra ngoài để đóng gợi ý
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.search-bar')) {
      suggestionsBox.style.display = 'none';
    }
  });

  // Khởi tạo
  loadAllLocations();
});
