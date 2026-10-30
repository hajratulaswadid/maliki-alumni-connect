@echo off
title Hentikan Demo Maliki Alumni Connect
echo Menghentikan server Maliki Alumni Connect...
docker stop maliki_demo >nul 2>nul
echo Server telah dimatikan.
timeout /t 2 >nul
