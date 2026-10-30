@echo off
title MALIKI ALUMNI CONNECT - Mode Demonstrasi
cd /d "%~dp0"

echo =====================================================================
echo   MALIKI ALUMNI CONNECT - Inisialisasi Mode Demonstrasi
echo   Port: 8765 ^| http://127.0.0.1:8765
echo =====================================================================
echo.

where docker >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] Menjalankan server melalui Docker Desktop
    docker stop maliki_demo >nul 2>nul
    docker run --rm -d --name maliki_demo -v "%cd%:/app" -w /app -p 8765:8765 p2b_portal_terintegrasi-app:latest python app.py --demo
    ping 127.0.0.1 -n 3 >nul
    start "" http://127.0.0.1:8765
    echo.
    echo =====================================================================
    echo  SERVER MALIKI ALUMNI CONNECT AKTIF
    echo  Akses Web Lokal: http://127.0.0.1:8765
    echo.
    echo  Akun Demo:
    echo  - Pengurus / Admin : admin@demo.local  / DemoMaliki2026!
    echo  - Alumni / Usaha   : alumni@demo.local / DemoMaliki2026!
    echo  - Mitra Usaha      : mitra@demo.local  / DemoMaliki2026!
    echo  - Mentor           : mentor@demo.local / DemoMaliki2026!
    echo =====================================================================
    echo.
    pause
    goto end
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Menggunakan py launcher
    ping 127.0.0.1 -n 2 >nul
    start "" http://127.0.0.1:8765
    py -3 app.py --demo
    goto end
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Menggunakan python
    ping 127.0.0.1 -n 2 >nul
    start "" http://127.0.0.1:8765
    python app.py --demo
    goto end
)

echo [PERHATIAN] Python 3 atau Docker Desktop belum terdeteksi.
pause

:end
