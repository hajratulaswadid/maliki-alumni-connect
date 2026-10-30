FROM python:3.11-slim

WORKDIR /app

# Buat direktori data dan user non-root (standar Hugging Face Spaces & security)
RUN useradd -m -u 1000 user && mkdir -p /app/data && chown -R user:user /app

# Salin seluruh kode proyek
COPY --chown=user:user . /app

USER user

# Konfigurasi environment
ENV HOST=0.0.0.0
ENV PORT=7860
ENV MALIKI_DEMO=1
ENV HOME=/home/user

EXPOSE 7860
EXPOSE 8765

# Jalankan server
CMD ["python", "app.py", "--demo"]
