# 🚀 HƯỚNG DẪN CHẠY GIAO DIỆN iOS WEATHER

## Cách 1: Xem Demo HTML (Nhanh nhất - Không cần Django)

### Bước 1: Mở file demo

```bash
# Mở trực tiếp file trong browser
start demo-ios-weather.html
```

hoặc double-click vào file **demo-ios-weather.html**

✅ **Ưu điểm**: Xem ngay, không cần cài đặt gì
❌ **Nhược điểm**: Chỉ là demo, không có dữ liệu thật

---

## Cách 2: Chạy với Django (Giao diện đầy đủ)

### Bước 1: Cài đặt dependencies

```bash
cd Weather_Forecast_Py
pip install -r requirements.txt
```

Nếu không có requirements.txt, cài thủ công:

```bash
pip install django djangorestframework requests python-decouple
```

### Bước 2: Chạy migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Bước 3: Khởi động server

```bash
python manage.py runserver
```

### Bước 4: Mở trình duyệt

**Giao diện iOS Weather:**

```
http://127.0.0.1:8000/ios/
```

**Giao diện cũ:**

```
http://127.0.0.1:8000/
```

---

## 📱 Tính năng đã có

✅ **Gradient động** - Background thay đổi theo thời tiết
✅ **Glassmorphism** - Hiệu ứng kính mờ sang trọng  
✅ **Animated Icons** - SVG icons với animation
✅ **Tailwind CSS** - Utility classes mạnh mẽ
✅ **Bootstrap 5** - Components responsive
✅ **Smooth Animations** - Chuyển động mượt mà
✅ **Responsive** - Tối ưu cho mobile/tablet/desktop

---

## 🎨 Tùy chỉnh màu sắc

### Trong file index-ios.html, thay đổi config Tailwind:

```javascript
tailwind.config = {
  theme: {
    extend: {
      colors: {
        "ios-blue": "#4A90E2", // Đổi màu xanh chính
        "ios-light-blue": "#5FC7FF", // Đổi màu xanh nhạt
        // ... thêm màu của bạn
      },
    },
  },
};
```

### Trong file ios-weather.css, sửa gradients:

```css
.ios-weather-bg.clear-day {
  background: linear-gradient(180deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
}
```

---

## 🔧 Tích hợp API thật

### Trong file ios-weather-app.js, sửa hàm fetchWeatherData():

```javascript
async fetchWeatherData() {
  // Lấy location_id từ URL hoặc localStorage
  const locationId = 1; // Ví dụ: Hà Nội

  const response = await fetch(`/api/weather/current/?location_id=${locationId}`);
  const data = await response.json();

  return {
    location: data.city_name,
    current: {
      temp: data.temperature,
      feels_like: data.feels_like,
      // ... map thêm các field
    }
  };
}
```

---

## ⚡ Tối ưu hiệu năng

### 1. Minify CSS/JS trong production

```bash
# Cài đặt
pip install django-compressor

# Trong settings.py
INSTALLED_APPS += ['compressor']
COMPRESS_ENABLED = True
```

### 2. Cache static files

```python
# settings.py
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
```

### 3. Lazy load images

```html
<img src="..." loading="lazy" />
```

---

## 🐛 Troubleshooting

### Lỗi: Template not found

```bash
# Kiểm tra cấu trúc thư mục
Weather_App/
  templates/
    index-ios.html  # ← File phải ở đây
```

### Lỗi: Static files không load

```bash
python manage.py collectstatic
```

### Glassmorphism không hoạt động

- Kiểm tra browser hỗ trợ `backdrop-filter`
- Chrome/Edge: OK
- Firefox: Cần bật flag
- Safari: OK

---

## 📞 API Endpoints

### Lấy thời tiết hiện tại:

```
GET /api/weather/current/?location_id=1
```

### Tìm kiếm thành phố:

```
GET /api/weather/search/?city=Hanoi
```

### Thành phố nổi bật:

```
GET /api/weather/featured/
```

---

## 🎯 Checklist trước khi deploy

- [ ] Kiểm tra tất cả APIs hoạt động
- [ ] Test responsive trên mobile
- [ ] Optimize images
- [ ] Minify CSS/JS
- [ ] Set DEBUG = False
- [ ] Configure ALLOWED_HOSTS
- [ ] Collect static files
- [ ] Setup HTTPS

---

## 📚 Tài liệu tham khảo

- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Bootstrap 5 Docs](https://getbootstrap.com/docs/5.3/)
- [Django Templates](https://docs.djangoproject.com/en/stable/topics/templates/)
- [iOS Design Guidelines](https://developer.apple.com/design/)

---

## 💡 Tips & Tricks

### Thay đổi gradient theo giờ tự động:

```javascript
const hour = new Date().getHours();
if (hour >= 6 && hour < 12) {
  bg.classList.add("morning");
} else if (hour >= 12 && hour < 18) {
  bg.classList.add("afternoon");
} else {
  bg.classList.add("evening");
}
```

### Thêm haptic feedback (mobile):

```javascript
if ("vibrate" in navigator) {
  navigator.vibrate(10); // Rung nhẹ khi tap
}
```

### Smooth scroll indicator:

```javascript
container.addEventListener("scroll", (e) => {
  const scrollPercentage = (e.target.scrollLeft / e.target.scrollWidth) * 100;
  console.log(scrollPercentage + "%");
});
```

---

## 🎊 Chúc bạn thành công!

Nếu có vấn đề gì, check lại các bước trên hoặc xem file demo-ios-weather.html để tham khảo. 🚀
