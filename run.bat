@echo off
echo ========================================
echo   KHOI DONG WEATHER APP - iOS STYLE
echo ========================================
echo.

REM Kich hoat virtual environment neu co
if exist venv\Scripts\activate.bat (
    echo [+] Kich hoat virtual environment...
    call venv\Scripts\activate.bat
)

REM Kiem tra Django da cai chua
python -c "import django" 2>NUL
if errorlevel 1 (
    echo [!] Django chua duoc cai dat!
    echo [+] Dang cai dat dependencies...
    pip install django djangorestframework requests python-decouple
)

REM Chay migrations
echo.
echo [+] Chay database migrations...
C:\Users\quy23\AppData\Local\Programs\Python\Python313\python.exe manage.py makemigrations
C:\Users\quy23\AppData\Local\Programs\Python\Python313\python.exe manage.py migrate

REM Khoi dong server
echo.
echo ========================================
echo   SERVER DANG KHOI DONG...
echo ========================================
echo.
echo [*] Giao dien iOS Weather:  http://127.0.0.1:8000/ios/
echo [*] Giao dien cu:           http://127.0.0.1:8000/
echo [*] Admin:                  http://127.0.0.1:8000/admin/
echo.
echo Nhan Ctrl+C de dung server
echo ========================================
echo.

C:\Users\quy23\AppData\Local\Programs\Python\Python313\python.exe manage.py runserver

pause
