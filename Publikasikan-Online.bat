@echo off
title PUBLIKASIKAN MALIKI ALUMNI CONNECT KE INTERNET (CLOUDFLARE)
cd /d "%~dp0"

echo =====================================================================
echo   MEMBUAT LINK AKSES PUBLIK (CLOUDFLARE TUNNEL) MALIKI ALUMNI CONNECT
echo =====================================================================
echo.

:: 1. Pastikan server lokal sudah berjalan di port 8765
docker ps | findstr "maliki_demo" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Menyalakan server lokal terlebih dahulu...
    docker run --rm -d --name maliki_demo -v "%cd%:/app" -w /app -p 8765:8765 p2b_portal_terintegrasi-app:latest python app.py --demo
    ping 127.0.0.1 -n 3 >nul
)

echo [OK] Server lokal aktif di port 8765.
echo.
echo Sedang menghubungkan ke Cloudflare Global Network...
echo.

docker stop maliki_tunnel >nul 2>nul
docker run --rm -it --name maliki_tunnel cloudflare/cloudflared:latest tunnel --url http://host.docker.internal:8765

pause
