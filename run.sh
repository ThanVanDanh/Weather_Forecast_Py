#!/bin/bash

echo "========================================"
echo "  KHOI DONG WEATHER APP - iOS STYLE"
echo "========================================"
echo ""

# Kich hoat virtual environment neu co
if [ -f "venv/bin/activate" ]; then
    echo "[+] Kich hoat virtual environment..."
    source venv/bin/activate
fi

# Kiem tra Django da cai chua
python -c "import django" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[!] Django chua duoc cai dat!"
    echo "[+] Dang cai dat dependencies..."
    pip install django djangorestframework requests python-decouple
fi

# Chay migrations
echo ""
echo "[+] Chay database migrations..."
python manage.py makemigrations
python manage.py migrate

# Khoi dong server
echo ""
echo "========================================"
echo "  SERVER DANG KHOI DONG..."
echo "========================================"
echo ""
echo "[*] Giao dien iOS Weather:  http://127.0.0.1:8000/ios/"
echo "[*] Giao dien cu:           http://127.0.0.1:8000/"
echo "[*] Admin:                  http://127.0.0.1:8000/admin/"
echo ""
echo "Nhan Ctrl+C de dung server"
echo "========================================"
echo ""

python manage.py runserver
