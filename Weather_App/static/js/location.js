document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btn-locate");
  const cityEl = document.getElementById("current-city");
  if (!btn || !cityEl) return;

  btn.addEventListener("click", async (e) => {
    e.preventDefault();
    cityEl.innerText = "Đang định vị...";

    try {
      // Lấy vị trí xấp xỉ theo IP
      const r = await fetch("https://ipapi.co/json/");
      const j = await r.json();

      const lat = Number(j.latitude);
      const lon = Number(j.longitude);

      // Gửi về Django để map 34 tỉnh
      const res = await fetch("/api/locate-user/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat, lon })
      });

      const data = await res.json();
      if (res.ok && data.ok) {
        cityEl.innerText = data.city;   // ✅ HIỆN TỈNH
      } else {
        cityEl.innerText = "Không xác định";
      }
    } catch {
      cityEl.innerText = "Không xác định";
    }
  });
});
