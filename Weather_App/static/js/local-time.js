function pad2(n) {
  return String(n).padStart(2, "0");
}

function updateLocalTime() {
  const d = new Date();

  const hh = pad2(d.getHours());
  const mm = pad2(d.getMinutes());
  const ss = pad2(d.getSeconds());

  const day = d.getDate();
  const month = d.getMonth() + 1;
  const year = d.getFullYear();

  const el = document.getElementById("local-time");
  if (el) {
    el.textContent = `Giờ địa phương: ${hh}:${mm}:${ss} ${day}/${month}/${year}`;
  }
}

updateLocalTime();
setInterval(updateLocalTime, 1000);
