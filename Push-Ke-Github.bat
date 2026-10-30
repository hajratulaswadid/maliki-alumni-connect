@echo off
title Push Maliki Alumni Connect ke GitHub
cd /d "%~dp0"

echo =====================================================================
echo   UPLOAD PROYEK KE GITHUB (hajratulaswad/maliki-alumni-connect)
echo =====================================================================
echo.

git remote remove origin 2>nul
git remote add origin https://github.com/hajratulaswad/maliki-alumni-connect.git
git branch -M main

echo Mengirim commit ke GitHub...
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo =====================================================================
    echo  [BERHASIL] Repository berhasil diupload ke GitHub!
    echo  Link Repo: https://github.com/hajratulaswad/maliki-alumni-connect
    echo =====================================================================
) else (
    echo.
    echo [CATATAN] Jika gagal, pastikan Anda sudah membuat repository kosong
    echo bernama 'maliki-alumni-connect' di https://github.com/new
)

echo.
pause
