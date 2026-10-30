@echo off
title Pasang Domain Kampus UIN Malang
cd /d "%~dp0"

echo =====================================================================
echo   PEMASANGAN DOMAIN: alumni-connect.uin-malang.ac.id
echo =====================================================================
echo.

:: Cek izin Administrator
openfiles >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Meminta hak akses Administrator...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

set HOSTS_PATH=%windir%\System32\drivers\etc\hosts

findstr /i "alumni-connect.uin-malang.ac.id" "%HOSTS_PATH%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] Domain 'alumni-connect.uin-malang.ac.id' sudah terpasang sebelumnya!
) else (
    echo. >> "%HOSTS_PATH%"
    echo 127.0.0.1  alumni-connect.uin-malang.ac.id >> "%HOSTS_PATH%"
    echo [BERHASIL] Domain 'alumni-connect.uin-malang.ac.id' berhasil ditambahkan ke sistem!
)

echo.
echo =====================================================================
echo  Sekarang Anda bisa membuka browser di:
echo  http://alumni-connect.uin-malang.ac.id:8765
echo =====================================================================
echo.
pause
