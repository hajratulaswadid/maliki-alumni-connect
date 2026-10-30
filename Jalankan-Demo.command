#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
echo "====================================================================="
echo " Menjalankan MALIKI ALUMNI CONNECT dalam Mode Demonstrasi"
echo " Port: 8765 | http://127.0.0.1:8765"
echo "====================================================================="

if command -v python3 &>/dev/null; then
    python3 app.py --demo
elif command -v python &>/dev/null; then
    python app.py --demo
else
    echo "[ERROR] Python 3 tidak ditemukan di sistem PATH."
    read -p "Tekan Enter untuk keluar..."
fi
