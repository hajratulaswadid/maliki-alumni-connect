---
title: Maliki Alumni Connect
emoji: 🎓
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# MALIKI ALUMNI CONNECT
## Aplikasi Jejaring dan Kolaborasi Ekonomi Alumni UIN Maulana Malik Ibrahim Malang

**Status:** MVP / pilot yang dapat dijalankan secara lokal atau pada server sendiri. **Belum di-hosting di internet** dan **belum merupakan aplikasi produksi yang telah diaudit keamanan**.

Aplikasi dibuat berdasarkan *Rencana Program Kerja Divisi Ekonomi Digital dan Kewirausahaan IKA UIN Maulana Malik Ibrahim Malang, Kerangka Strategis 2026–2031, Rencana Aksi 2027* (draf tertanggal 29 Oktober 2026). Nama/target program di dokumen adalah usulan pengurus dan bukan hasil penetapan resmi.

### Fitur yang sudah berfungsi

1. **Direktori alumni**: daftar alumni berbasis persetujuan, fakultas, profesi, wilayah, keahlian, verifikasi oleh pengurus, dan perubahan profil.
2. **Jejaring usaha**: registrasi dan kurasi usaha alumni; pencarian berdasarkan sektor dan wilayah.
3. **Katalog produk/jasa**: produk terkait usaha pemilik; kurasi sebelum publikasi; URL foto produk opsional; tautan rujukan.
4. **Profesi dan mentor**: direktori keahlian alumni, pengajuan mentor, review pengurus, penugasan mentor kepada tenant.
5. **Kelas alumni**: pembuatan kelas oleh pengurus, kuota, buka/tutup pendaftaran, daftar daring, riwayat pendaftaran dan pencatatan kelulusan kelas.
6. **Inkubasi bisnis**: pengajuan ide/usaha, asesmen administratif, persetujuan tenant, penugasan mentor, jurnal/catatan pendampingan.
7. **Business matching**: pengiriman lead ke pemilik usaha, status tindak lanjut, dan komunikasi pesan privat antara pengirim dan pemilik usaha.
8. **Perjanjian kerja sama bisnis antaralumni**: pengajuan rancangan, persetujuan mitra atas draf, review pengurus, cetak/"Simpan sebagai PDF" melalui dialog cetak browser, referensi arsip dokumen final yang ditandatangani, audit peristiwa PKS, dan izin kedua pihak untuk menampilkan ringkasan PKS aktif.
9. **Dashboard anggota & pengurus**: verifikasi profil, kurasi katalog/mentor/tenant, ringkasan capaian KPI tahun 2027, dan pengelolaan informasi.
10. **Permintaan hak data pribadi**: pengajuan permintaan akses, koreksi, penarikan persetujuan atau penghapusan kepada pengurus untuk diproses secara administratif. Fitur ini **tidak menghapus data otomatis**.

### Mulai dalam mode demonstrasi (tanpa instalasi paket)

**Prasyarat:** Python 3.10 atau lebih baru. Tidak ada `pip install`, Node.js, atau database eksternal yang diperlukan.

**Windows**: klik `Jalankan-Demo.bat`, atau jalankan:

```powershell
py -3 app.py --demo
```
atau jika menggunakan perintah `python`:
```powershell
python app.py --demo
```

**macOS/Linux**: klik `Jalankan-Demo.command` (jika izin eksekusi memungkinkan), atau:

```bash
python3 app.py --demo
```

Lalu buka browser di **http://127.0.0.1:8765**. Selama terminal server berjalan, data disimpan secara lokal di `data/maliki.db` (SQLite). Mematikan dan menjalankan kembali server tidak menghapus data.

**Empat akun contoh** (seluruh nama dan bisnis fiktif):

| Peran | Email | Password |
| --- | --- | --- |
| Pengurus/admin | `admin@demo.local` | `DemoMaliki2026!` |
| Alumni/pemilik usaha | `alumni@demo.local` | `DemoMaliki2026!` |
| Alumni/mitra | `mitra@demo.local` | `DemoMaliki2026!` |
| Mentor | `mentor@demo.local` | `DemoMaliki2026!` |

Data contoh sengaja berlabel `DEMO` dan **tidak boleh dianggap data alumni atau usaha sesungguhnya**. Jangan memasukkan data pribadi sungguhan ketika menguji aplikasi.

### Memulai dengan database baru / tanpa data contoh

Jangan sertakan `--demo`. Pertama kali menyalakan server, set administrator awal di lingkungan terminal:

```bash
export ADMIN_EMAIL='pengurus@example.org'
export ADMIN_PASSWORD='GantiDenganSandiKuatMinimal12Karakter2026!'
python3 app.py
```

Untuk Windows PowerShell:

```powershell
$env:ADMIN_EMAIL="pengurus@example.org"
$env:ADMIN_PASSWORD="GantiDenganSandiKuatMinimal12Karakter2026!"
py -3 app.py
```

### Konfigurasi

- `HOST` (default `127.0.0.1`): IP pengikat. Server publik harus di belakang reverse proxy dan HTTPS.
- `PORT` (default `8765`): port TCP.
- `MALIKI_DB_PATH`: lokasi berkas database SQLite.
- `COOKIE_SECURE=1`: wajib diset ketika dipakai melalui HTTPS.
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`: kredensial admin pertama untuk database yang belum punya admin.
- `MALIKI_DEMO=1` atau `--demo`: aktifkan database contoh dan banner simulasi.

### Struktur berkas

```text
maliki-alumni-connect/
├── app.py                       # Python HTTP + REST API + SQLite
├── static/
│   ├── index.html               # Antarmuka portal
│   ├── style.css                # Desain responsif
│   ├── app.js                   # Interaksi, form, dashboard
│   └── favicon.svg              # Logo emblem
├── tests/test_workflows.py      # Pengujian alur end-to-end
├── data/                        # Database lokal otomatis terbentuk
├── Jalankan-Demo.bat
├── Jalankan-Demo.command
└── README.md
```

Uji otomatis:

```bash
python3 -m unittest discover -s tests -v
```
