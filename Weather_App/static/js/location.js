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

    } catch (err) {
      console.error(err);
      alert("Lỗi kết nối đến server");
    }
  }
});
