FROM python:3.11-slim

WORKDIR /app

# Salin seluruh kode proyek
COPY . /app

# Konfigurasi environment
ENV HOST=0.0.0.0
ENV PORT=8765
ENV MALIKI_DEMO=1

EXPOSE 8765

# Jalankan server
CMD ["python", "app.py", "--demo"]
