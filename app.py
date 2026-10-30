import http.server
import urllib.parse
import sqlite3
import hashlib
import hmac
import json
import os
import sys
import time
import datetime
import uuid
import mimetypes
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

# Default configuration from environment
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))
DB_PATH = Path(os.environ.get("MALIKI_DB_PATH", DATA_DIR / "maliki.db"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "pengurus@example.org")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "GantiDenganSandiKuatMinimal12Karakter2026!")
IS_DEMO = "--demo" in sys.argv or os.environ.get("MALIKI_DEMO", "0") == "1"

# In-memory sessions table: session_token -> {user_id, role, email, full_name, expires_at}
SESSIONS = {}
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if not salt:
        salt = uuid.uuid4().hex
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()
    return pwd_hash, salt


def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, pwd_hash)


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'alumni', -- admin, alumni, mitra, mentor
            full_name TEXT NOT NULL,
            nim TEXT,
            faculty TEXT,
            graduation_year INTEGER,
            profession TEXT,
            company TEXT,
            province TEXT,
            city TEXT,
            phone TEXT,
            linkedin TEXT,
            bio TEXT,
            consent_data INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            description TEXT,
            province TEXT,
            city TEXT,
            address TEXT,
            website TEXT,
            contact_wa TEXT,
            is_curated INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            price REAL DEFAULT 0,
            photo_url TEXT,
            ref_link TEXT,
            is_curated INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS mentors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            expertise TEXT NOT NULL,
            years_experience INTEGER DEFAULT 1,
            bio TEXT,
            portfolio_url TEXT,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            instructor TEXT NOT NULL,
            schedule TEXT,
            location TEXT,
            quota INTEGER DEFAULT 50,
            is_open INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS class_enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_graduated INTEGER DEFAULT 0,
            graduated_at TIMESTAMP,
            certificate_num TEXT,
            UNIQUE(class_id, user_id),
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS incubation_tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_id INTEGER,
            business_idea TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'ideation', -- ideation, mvp, traction, scaling
            need_desc TEXT,
            status TEXT DEFAULT 'submitted', -- submitted, under_review, accepted, rejected
            mentor_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE SET NULL,
            FOREIGN KEY (mentor_id) REFERENCES mentors(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS incubation_journals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            note_type TEXT DEFAULT 'progress', -- progress, mentor_feedback, milestone
            notes TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES incubation_tenants(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS business_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_business_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'new', -- new, in_progress, deal, declined
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (recipient_business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS lead_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES business_leads(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS pks_agreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposer_id INTEGER NOT NULL,
            partner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            scope TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            content TEXT NOT NULL,
            proposer_agreed INTEGER DEFAULT 1,
            partner_agreed INTEGER DEFAULT 0,
            admin_reviewed INTEGER DEFAULT 0,
            admin_notes TEXT,
            final_doc_ref TEXT,
            is_public_summary INTEGER DEFAULT 0,
            status TEXT DEFAULT 'draft', -- draft, partner_agreed, admin_reviewed, finalized, rejected
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (proposer_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (partner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS pks_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pks_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pks_id) REFERENCES pks_agreements(id) ON DELETE CASCADE,
            FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS data_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            request_type TEXT NOT NULL, -- access, correction, withdraw_consent, deletion
            details TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, processed, rejected
            admin_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'info',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
    conn.close()


def seed_demo_data():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    if cursor.fetchone()["cnt"] > 0:
        conn.close()
        return

    print("=> Seeding DEMO data for Maliki Alumni Connect...")

    # Default demo users
    demo_pass = "DemoMaliki2026!"
    demo_users = [
        {
            "email": "admin@demo.local",
            "role": "admin",
            "full_name": "Pengurus Pusat IKA UIN Malang (DEMO)",
            "nim": "DEMO-ADM-001",
            "faculty": "Ekonomi",
            "graduation_year": 2015,
            "profession": "Pengurus Divisi Ekonomi & Kewirausahaan",
            "company": "IKA UIN Maulana Malik Ibrahim Malang",
            "province": "Jawa Timur",
            "city": "Kota Malang",
            "phone": "081234567890",
            "linkedin": "https://linkedin.com/in/demo-admin",
            "bio": "Administrator dan kurator platform Maliki Alumni Connect.",
            "status": "approved"
        },
        {
            "email": "alumni@demo.local",
            "role": "alumni",
            "full_name": "Ahmad Fauzi, S.E. (DEMO)",
            "nim": "15510023",
            "faculty": "Ekonomi",
            "graduation_year": 2019,
            "profession": "Founder & CEO",
            "company": "Maliki Tech Solusindo",
            "province": "Jawa Timur",
            "city": "Kota Malang",
            "phone": "081298765432",
            "linkedin": "https://linkedin.com/in/ahmad-fauzi-demo",
            "bio": "Alumni Jurusan Manajemen FEB UIN Malang bergerak di bidang IT Solution & Software House.",
            "status": "approved"
        },
        {
            "email": "mitra@demo.local",
            "role": "mitra",
            "full_name": "Siti Aminah, S.Kom. (DEMO)",
            "nim": "16520045",
            "faculty": "Sains dan Teknologi",
            "graduation_year": 2020,
            "profession": "Co-Founder & COO",
            "company": "Karya Santri Digital & Halal Hub",
            "province": "Jawa Timur",
            "city": "Surabaya",
            "phone": "081377889900",
            "linkedin": "https://linkedin.com/in/siti-aminah-demo",
            "bio": "Alumni Teknik Informatika yang fokus pada agregasi produk halal dan logistik pesantren.",
            "status": "approved"
        },
        {
            "email": "mentor@demo.local",
            "role": "mentor",
            "full_name": "Dr. Irfan Hakim, M.M. (DEMO)",
            "nim": "08510012",
            "faculty": "Ekonomi",
            "graduation_year": 2012,
            "profession": "Senior Business Consultant & Angel Investor",
            "company": "Nusantara Venture Partner",
            "province": "DKI Jakarta",
            "city": "Jakarta Selatan",
            "phone": "081122334455",
            "linkedin": "https://linkedin.com/in/dr-irfan-hakim-demo",
            "bio": "Mentor inkubator bisnis dengan pengalaman 12 tahun pendampingan startup dan UKM nasional.",
            "status": "approved"
        },
        {
            "email": "zainal@demo.local",
            "role": "alumni",
            "full_name": "Zainal Abidin, S.Ag. (DEMO)",
            "nim": "17110034",
            "faculty": "Syariah",
            "graduation_year": 2021,
            "profession": "Konsultan Halal & Regulasi",
            "company": "Lembaga Advokasi Halal Malang",
            "province": "Jawa Timur",
            "city": "Kabupaten Malang",
            "phone": "081999888777",
            "linkedin": "https://linkedin.com/in/zainal-halal",
            "bio": "Praktisi pendampingan sertifikasi halal dan perizinan NIB untuk UMKM alumni.",
            "status": "approved"
        }
    ]

    user_ids = {}
    for u in demo_users:
        pwd_hash, salt = hash_password(demo_pass)
        cursor.execute("""
        INSERT INTO users (email, password_hash, salt, role, full_name, nim, faculty, graduation_year,
                           profession, company, province, city, phone, linkedin, bio, status, consent_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            u["email"], pwd_hash, salt, u["role"], u["full_name"], u["nim"], u["faculty"],
            u["graduation_year"], u["profession"], u["company"], u["province"], u["city"],
            u["phone"], u["linkedin"], u["bio"], u["status"]
        ))
        user_ids[u["email"]] = cursor.lastrowid

    # Seed Businesses
    businesses = [
        {
            "user_id": user_ids["alumni@demo.local"],
            "name": "Maliki Tech Solusindo (DEMO)",
            "sector": "Teknologi & Digital",
            "description": "Layanan pengembangan perangkat lunak ERP, website portal, dan sistem integrasi kampus.",
            "province": "Jawa Timur",
            "city": "Kota Malang",
            "address": "Jl. Gajayana No. 50, Lowokwaru, Malang",
            "website": "https://malikitech.demo.local",
            "contact_wa": "081298765432",
            "is_curated": 1
        },
        {
            "user_id": user_ids["mitra@demo.local"],
            "name": "Karya Santri Halal Food & Supply (DEMO)",
            "sector": "Makanan & Minuman Halal",
            "description": "Distribusi bahan makanan kering, kopi bubuk khas Malang, dan produk bersertifikat halal binaan alumni.",
            "province": "Jawa Timur",
            "city": "Surabaya",
            "address": "Rungkut Industri No. 12, Surabaya",
            "website": "https://karyasantri.demo.local",
            "contact_wa": "081377889900",
            "is_curated": 1
        },
        {
            "user_id": user_ids["zainal@demo.local"],
            "name": "Pusat Pendampingan Halal & Legalitas (DEMO)",
            "sector": "Jasa Konsultasi & Hukum",
            "description": "Bimbingan teknis SJPH, pendaftaran sertifikasi halal BPJPH, pendaftaran merk HKI dan NIB RBA.",
            "province": "Jawa Timur",
            "city": "Kabupaten Malang",
            "address": "Jl. Raya Dau No. 88, Malang",
            "website": "https://halalcenter.demo.local",
            "contact_wa": "081999888777",
            "is_curated": 1
        }
    ]

    biz_ids = []
    for b in businesses:
        cursor.execute("""
        INSERT INTO businesses (user_id, name, sector, description, province, city, address, website, contact_wa, is_curated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (b["user_id"], b["name"], b["sector"], b["description"], b["province"], b["city"], b["address"], b["website"], b["contact_wa"], b["is_curated"]))
        biz_ids.append(cursor.lastrowid)

    # Seed Products
    products = [
        {
            "business_id": biz_ids[0],
            "name": "Sistem Informasi Manajemen Madrasah & Pesantren (SIMMA)",
            "category": "Software & SaaS",
            "description": "Aplikasi berbasis web untuk tata kelola santri, absensi, spp virtual account, dan rapor online.",
            "price": 3500000,
            "photo_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=500",
            "ref_link": "https://malikitech.demo.local/simma",
            "is_curated": 1
        },
        {
            "business_id": biz_ids[0],
            "name": "Jasa Pembuatan Landing Page & Toko Online UKM",
            "category": "Jasa IT",
            "description": "Paket hemat pembuatan website responsif untuk alumni baru merintis usaha lengkap dengan optimasi SEO.",
            "price": 950000,
            "photo_url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=500",
            "ref_link": "https://malikitech.demo.local/web-umkm",
            "is_curated": 1
        },
        {
            "business_id": biz_ids[1],
            "name": "Kopi Robusta Dampit Malang Premium 250gr",
            "category": "Kuliner & Kopi",
            "description": "Biji kopi petik merah olahan petani lereng Semeru, aroma pekat dark chocolate dan karamel.",
            "price": 45000,
            "photo_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500",
            "ref_link": "https://karyasantri.demo.local/kopi",
            "is_curated": 1
        },
        {
            "business_id": biz_ids[2],
            "name": "Paket Pendampingan Self-Declare Sertifikasi Halal",
            "category": "Jasa Sertifikasi",
            "description": "Layanan kurasi bahan baku dan input aplikasi SIHALAL BPJPH sampai sertifikat terbit.",
            "price": 300000,
            "photo_url": "https://images.unsplash.com/photo-1450133064473-71024230f91b?w=500",
            "ref_link": "https://halalcenter.demo.local/paket-halal",
            "is_curated": 1
        }
    ]

    for p in products:
        cursor.execute("""
        INSERT INTO products (business_id, name, category, description, price, photo_url, ref_link, is_curated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (p["business_id"], p["name"], p["category"], p["description"], p["price"], p["photo_url"], p["ref_link"], p["is_curated"]))

    # Seed Mentor
    cursor.execute("""
    INSERT INTO mentors (user_id, expertise, years_experience, bio, portfolio_url, status, is_active)
    VALUES (?, ?, ?, ?, ?, 'approved', 1)
    """, (
        user_ids["mentor@demo.local"],
        "Scale-up Startup, Business Modeling & Financial Projection",
        12,
        "Berpengalaman mendampingi lebih dari 40 startup tahap seed hingga pre-series A di Jawa Timur & Jakarta.",
        "https://drirfanhakim.demo.local"
    ))
    mentor_row_id = cursor.lastrowid

    # Seed Classes
    classes = [
        {
            "title": "Bootcamp Kewirausahaan Digital: Dari Ide ke Pasar (Batch I 2027)",
            "description": "Program intensif 4 pekan membedah validasi pasar, pembuatan MVP hemat biaya, dan strategi go-to-market untuk alumni.",
            "instructor": "Dr. Irfan Hakim, M.M. & Tim Praktisi",
            "schedule": "Setiap Sabtu, 09.00 - 12.00 WIB (Zoom + Rekaman)",
            "location": "Daring (Zoom) & Co-Working Space IKA UIN Malang",
            "quota": 100,
            "is_open": 1
        },
        {
            "title": "Masterclass Sertifikasi Halal BPJPH & Kesiapan Ekspor Produk Mamin",
            "description": "Panduan tuntas standar SJPH, kurasi bahan, audit halal, dan peluang buyer luar negeri.",
            "instructor": "Zainal Abidin, S.Ag. & BPJPH",
            "schedule": "Rabu, 19.30 - 21.30 WIB",
            "location": "Webinar Daring",
            "quota": 150,
            "is_open": 1
        }
    ]

    class_ids = []
    for c in classes:
        cursor.execute("""
        INSERT INTO classes (title, description, instructor, schedule, location, quota, is_open)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (c["title"], c["description"], c["instructor"], c["schedule"], c["location"], c["quota"], c["is_open"]))
        class_ids.append(cursor.lastrowid)

    # Seed Class Enrollments
    cursor.execute("""
    INSERT INTO class_enrollments (class_id, user_id, is_graduated, certificate_num)
    VALUES (?, ?, 1, 'CERT-IKA-2027-001')
    """, (class_ids[0], user_ids["alumni@demo.local"]))

    cursor.execute("""
    INSERT INTO class_enrollments (class_id, user_id, is_graduated)
    VALUES (?, ?, 0)
    """, (class_ids[0], user_ids["mitra@demo.local"]))

    # Seed Incubation Tenant & Journals
    cursor.execute("""
    INSERT INTO incubation_tenants (user_id, business_id, business_idea, stage, need_desc, status, mentor_id)
    VALUES (?, ?, ?, 'traction', ?, 'accepted', ?)
    """, (
        user_ids["alumni@demo.local"],
        biz_ids[0],
        "Platform Manajemen Pesantren Terpadu Berbasis Cloud dan Mobile Apps",
        "Membutuhkan pendampingan penetapan model langganan tahunan (B2B SaaS) serta integrasi payment gateway perbankan syariah.",
        mentor_row_id
    ))
    tenant_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO incubation_journals (tenant_id, author_id, note_type, notes)
    VALUES (?, ?, 'mentor_feedback', ?)
    """, (
        tenant_id,
        user_ids["mentor@demo.local"],
        "Sesi pendampingan ke-1: Struktur pricing SaaS telah disesuaikan dengan kapasitas pesantren medium (300-1000 santri). Target validasi 10 pesantren pertama di Malang Raya dalam 60 hari."
    ))

    cursor.execute("""
    INSERT INTO incubation_journals (tenant_id, author_id, note_type, notes)
    VALUES (?, ?, 'progress', ?)
    """, (
        tenant_id,
        user_ids["alumni@demo.local"],
        "Progress mingguan: Prototipe modul presensi sidik jari telah terhubung dengan API Telegram wali santri. 3 pesantren telah bersedia uji coba gratis."
    ))

    # Seed Business Lead & Message
    cursor.execute("""
    INSERT INTO business_leads (sender_id, recipient_business_id, title, message, status)
    VALUES (?, ?, ?, ?, 'in_progress')
    """, (
        user_ids["mitra@demo.local"],
        biz_ids[0],
        "Permintaan Integrasi Web Store & Otomasi Order Kopi Halal",
        "Halo Mas Fauzi, kami dari Karya Santri berminat memakai jasa IT Maliki Tech untuk menghubungkan marketplace lokal kami dengan WhatsApp order gateway.",
    ))
    lead_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO lead_messages (lead_id, sender_id, message)
    VALUES (?, ?, ?)
    """, (
        lead_id,
        user_ids["mitra@demo.local"],
        "Halo Mas Fauzi, kami dari Karya Santri berminat memakai jasa IT Maliki Tech untuk menghubungkan marketplace lokal kami dengan WhatsApp order gateway."
    ))

    cursor.execute("""
    INSERT INTO lead_messages (lead_id, sender_id, message)
    VALUES (?, ?, ?)
    """, (
        lead_id,
        user_ids["alumni@demo.local"],
        "Alhamdulillah Mbak Siti, siap sekali! Kebutuhan integrasinya bisa kita diskusikan spesifikasinya, kebetulan modul API WhatsApp gateway kami sudah siap produksi."
    ))

    # Seed PKS (Kerja Sama Bisnis Antaralumni)
    pks_content = """PERJANJIAN KERJA SAMA (PKS) JASA PENGEMBANGAN TEKNOLOGI SISTEM E-COMMERCE HALAL
Nomor Referensi Draf: PKS/MALIKI-CONNECT/2027/001

Pada hari ini, disepakati nota kesepahaman antara:
1. Pihak Pertama: Maliki Tech Solusindo (Ahmad Fauzi, S.E. - Alumni FEB UIN Malang)
2. Pihak Kedua: Karya Santri Digital (Siti Aminah, S.Kom. - Alumni FST UIN Malang)

Pasal 1 - Ruang Lingkup:
Pihak Pertama menyediakan arsitektur perangkat lunak dan hosting terkelola untuk sistem rantai pasok produk halal Pihak Kedua.

Pasal 2 - Hak & Kewajiban:
Pihak Pertama menjamin uptime 99.5% dan dukungan teknis selama masa kontrak. Pihak Kedua menyediakan materi data produk terverifikasi halal dan tepat waktu dalam pembayaran termin.

Pasal 3 - Status Hukum & Non-Elektronik:
Persetujuan dalam platform platform Maliki Alumni Connect ini merupakan pengesahan draf rancangan kerja sama internal alumni dan direview oleh Pengurus IKA UIN Malang. Dokumen fisik bertanda tangan basah atau tersertifikasi disimpan secara terpisah di arsip resmi kedua pihak."""

    cursor.execute("""
    INSERT INTO pks_agreements (proposer_id, partner_id, title, scope, start_date, end_date, content,
                                proposer_agreed, partner_agreed, admin_reviewed, admin_notes, final_doc_ref,
                                is_public_summary, status)
    VALUES (?, ?, ?, ?, '2027-01-01', '2027-12-31', ?, 1, 1, 1, 'Telah dikurasi pengurus IKA bidang Ekonomi Digital. Memenuhi kriteria kolaborasi alumni.', 'ARSIP-IKA-PKS-2027-009', 1, 'finalized')
    """, (
        user_ids["alumni@demo.local"],
        user_ids["mitra@demo.local"],
        "Pengembangan Platform Rantai Pasok Halal Terintegrasi",
        "Kolaborasi IT & Distribusi Komoditas Santri Halal",
        pks_content
    ))
    pks_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO pks_audit_logs (pks_id, actor_id, action, notes)
    VALUES (?, ?, 'DRAFT_CREATED', 'Alumni mengajukan draf kerja sama PKS.')
    """, (pks_id, user_ids["alumni@demo.local"]))

    cursor.execute("""
    INSERT INTO pks_audit_logs (pks_id, actor_id, action, notes)
    VALUES (?, ?, 'PARTNER_AGREED', 'Mitra kerja sama menyetujui draf kerja sama.')
    """, (pks_id, user_ids["mitra@demo.local"]))

    cursor.execute("""
    INSERT INTO pks_audit_logs (pks_id, actor_id, action, notes)
    VALUES (?, ?, 'ADMIN_REVIEWED', 'Pengurus memverifikasi kesesuaian draf dan menandai status valid.')
    """, (pks_id, user_ids["admin@demo.local"]))

    cursor.execute("""
    INSERT INTO pks_audit_logs (pks_id, actor_id, action, notes)
    VALUES (?, ?, 'FINALIZED', 'Nomor arsip dokumen fisik ARSIP-IKA-PKS-2027-009 dicatat. Ringkasan diizinkan tampil di publik.')
    """, (pks_id, user_ids["admin@demo.local"]))

    # Seed Announcements
    announcements = [
        ("Sosialisasi Program Kerja 2027 Divisi Ekonomi Digital & Kewirausahaan", "Pengurus IKA mengundang seluruh alumni pengusaha & profesional untuk mendaftarkan usaha dan profil ke platform Maliki Alumni Connect guna kurasi direktori dan inkubator 2027.", "event"),
        ("Pendaftaran Tenant Batch I Inkubator Bisnis Dibuka", "Alumni yang memiliki ide startup atau UMKM yang membutuhkan pendampingan legalitas, branding, dan permodalan dipersilakan mengajukan proposal melalui menu Inkubasi.", "info")
    ]
    for title, content, cat in announcements:
        cursor.execute("INSERT INTO announcements (title, content, category) VALUES (?, ?, ?)", (title, content, cat))

    # Seed Sample Data Request
    cursor.execute("""
    INSERT INTO data_requests (user_id, request_type, details, status, admin_response)
    VALUES (?, 'correction', 'Mohon pembaruan nama perusahaan dan nomor kontak bisnis yang baru.', 'processed', 'Data kontak telah diperbarui oleh administrator.')
    """, (user_ids["alumni@demo.local"],))

    conn.commit()
    conn.close()
    print("=> DEMO data seeded successfully!")


def ensure_bootstrap_admin():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'admin'")
    if cursor.fetchone()["cnt"] == 0:
        pwd_hash, salt = hash_password(ADMIN_PASSWORD)
        cursor.execute("""
        INSERT INTO users (email, password_hash, salt, role, full_name, faculty, graduation_year, profession, status, consent_data)
        VALUES (?, ?, ?, 'admin', 'Administrator Utama IKA', 'Ekonomi', 2010, 'Pengurus Pusat', 'approved', 1)
        """, (ADMIN_EMAIL, pwd_hash, salt))
        conn.commit()
        print(f"=> Initial admin created: {ADMIN_EMAIL}")
    conn.close()


class MalikiRequestHandler(http.server.BaseHTTPRequestHandler):
    server_version = "MalikiAlumniServer/1.0"

    def send_json(self, data, status_code=200, extra_headers=None):
        payload = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, message, status_code=400):
        self.send_json({"error": True, "message": message}, status_code=status_code)

    def parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw_body)
        except Exception:
            return urllib.parse.parse_qs(raw_body)

    def get_cookies(self):
        cookie_header = self.headers.get("Cookie", "")
        cookies = {}
        for item in cookie_header.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()
        return cookies

    def get_current_user(self):
        cookies = self.get_cookies()
        token = cookies.get("maliki_session")
        if not token or token not in SESSIONS:
            return None
        sess = SESSIONS[token]
        if sess["expires_at"] < time.time():
            del SESSIONS[token]
            return None
        return sess

    def require_auth(self):
        user = self.get_current_user()
        if not user:
            self.send_error_json("Autentikasi diperlukan. Silakan masuk.", status_code=401)
            return None
        return user

    def require_admin(self):
        user = self.require_auth()
        if not user:
            return None
        if user["role"] != "admin":
            self.send_error_json("Hak akses ditolak. Khusus pengurus/admin.", status_code=403)
            return None
        return user

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            return self.handle_api_get(path, query)

        # Serve static files
        if path == "/" or path == "":
            file_path = STATIC_DIR / "index.html"
        else:
            rel_path = path.lstrip("/")
            file_path = STATIC_DIR / rel_path

        if file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "application/octet-stream"
            try:
                content = file_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error reading static file: {e}")
        else:
            # Fallback to index.html for SPA-like routes
            index_file = STATIC_DIR / "index.html"
            if index_file.is_file():
                content = index_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")

    def handle_api_get(self, path, query):
        conn = get_db()
        cursor = conn.cursor()

        # Auth state
        if path == "/api/auth/me":
            user = self.get_current_user()
            if not user:
                conn.close()
                return self.send_json({"logged_in": False, "user": None, "is_demo": IS_DEMO})
            cursor.execute("SELECT id, email, role, full_name, faculty, graduation_year, profession, company, province, city, phone, linkedin, bio, status FROM users WHERE id = ?", (user["id"],))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return self.send_json({"logged_in": False, "user": None, "is_demo": IS_DEMO})
            return self.send_json({"logged_in": True, "user": dict(row), "is_demo": IS_DEMO})

        # Alumni Directory
        if path == "/api/alumni":
            q = query.get("q", [""])[0].strip()
            faculty = query.get("faculty", [""])[0].strip()
            city = query.get("city", [""])[0].strip()

            sql = "SELECT id, full_name, faculty, graduation_year, profession, company, province, city, linkedin, bio, status FROM users WHERE role != 'admin'"
            params = []
            # Only approved alumni visible to public, unless admin is requesting all
            current_user = self.get_current_user()
            if not current_user or current_user["role"] != "admin":
                sql += " AND status = 'approved'"

            if q:
                sql += " AND (full_name LIKE ? OR profession LIKE ? OR company LIKE ?)"
                wild = f"%{q}%"
                params.extend([wild, wild, wild])
            if faculty:
                sql += " AND faculty = ?"
                params.append(faculty)
            if city:
                sql += " AND (city LIKE ? OR province LIKE ?)"
                params.extend([f"%{city}%", f"%{city}%"])

            sql += " ORDER BY graduation_year DESC, full_name ASC"
            cursor.execute(sql, params)
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"alumni": rows})

        # Businesses Directory
        if path == "/api/businesses":
            sector = query.get("sector", [""])[0].strip()
            city = query.get("city", [""])[0].strip()
            q = query.get("q", [""])[0].strip()

            current_user = self.get_current_user()
            is_admin = current_user and current_user["role"] == "admin"

            sql = """
            SELECT b.*, u.full_name as owner_name, u.email as owner_email, u.phone as owner_phone
            FROM businesses b
            JOIN users u ON b.user_id = u.id
            WHERE 1=1
            """
            params = []
            if not is_admin:
                sql += " AND b.is_curated = 1"

            if sector:
                sql += " AND b.sector = ?"
                params.append(sector)
            if city:
                sql += " AND (b.city LIKE ? OR b.province LIKE ?)"
                params.extend([f"%{city}%", f"%{city}%"])
            if q:
                sql += " AND (b.name LIKE ? OR b.description LIKE ?)"
                wild = f"%{q}%"
                params.extend([wild, wild])

            sql += " ORDER BY b.id DESC"
            cursor.execute(sql, params)
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"businesses": rows})

        # Products Catalog
        if path == "/api/products":
            category = query.get("category", [""])[0].strip()
            q = query.get("q", [""])[0].strip()
            biz_id = query.get("business_id", [""])[0].strip()

            current_user = self.get_current_user()
            is_admin = current_user and current_user["role"] == "admin"

            sql = """
            SELECT p.*, b.user_id as owner_id, b.name as business_name, b.city as business_city, b.contact_wa, u.full_name as owner_name
            FROM products p
            JOIN businesses b ON p.business_id = b.id
            JOIN users u ON b.user_id = u.id
            WHERE 1=1
            """
            params = []
            if not is_admin:
                sql += " AND p.is_curated = 1"

            if biz_id:
                sql += " AND p.business_id = ?"
                params.append(biz_id)
            if category:
                sql += " AND p.category = ?"
                params.append(category)
            if q:
                sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
                wild = f"%{q}%"
                params.extend([wild, wild])

            sql += " ORDER BY p.id DESC"
            cursor.execute(sql, params)
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"products": rows})

        # Mentors Directory
        if path == "/api/mentors":
            current_user = self.get_current_user()
            is_admin = current_user and current_user["role"] == "admin"

            sql = """
            SELECT m.*, u.full_name, u.faculty, u.graduation_year, u.profession, u.company, u.city, u.email, u.linkedin
            FROM mentors m
            JOIN users u ON m.user_id = u.id
            WHERE 1=1
            """
            if not is_admin:
                sql += " AND m.status = 'approved' AND m.is_active = 1"
            sql += " ORDER BY m.years_experience DESC"

            cursor.execute(sql)
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"mentors": rows})

        # Classes
        if path == "/api/classes":
            current_user = self.get_current_user()
            user_id = current_user["id"] if current_user else None

            cursor.execute("""
            SELECT c.*,
                   (SELECT COUNT(*) FROM class_enrollments ce WHERE ce.class_id = c.id) as enrolled_count
            FROM classes c
            ORDER BY c.id DESC
            """)
            classes = [dict(r) for r in cursor.fetchall()]

            # Fetch my enrollments if logged in
            my_enrollments = {}
            if user_id:
                cursor.execute("SELECT class_id, is_graduated, certificate_num FROM class_enrollments WHERE user_id = ?", (user_id,))
                for row in cursor.fetchall():
                    my_enrollments[row["class_id"]] = dict(row)

            for c in classes:
                c["is_enrolled"] = c["id"] in my_enrollments
                c["enrollment_info"] = my_enrollments.get(c["id"])

            conn.close()
            return self.send_json({"classes": classes})

        # Class enrollments detail (for admin)
        if path == "/api/class-enrollments":
            if not self.require_admin():
                conn.close()
                return
            class_id = query.get("class_id", [""])[0].strip()
            if not class_id:
                conn.close()
                return self.send_error_json("class_id diperlukan.")
            cursor.execute("""
            SELECT ce.*, u.full_name, u.email, u.phone, u.faculty, u.graduation_year
            FROM class_enrollments ce
            JOIN users u ON ce.user_id = u.id
            WHERE ce.class_id = ?
            ORDER BY ce.enrolled_at ASC
            """, (class_id,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"enrollments": rows})

        # Incubation Tenants
        if path == "/api/incubation":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            if current_user["role"] == "admin":
                sql = """
                SELECT t.*, u.full_name as founder_name, u.email as founder_email, u.phone as founder_phone,
                       b.name as business_name, m_u.full_name as mentor_name
                FROM incubation_tenants t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN businesses b ON t.business_id = b.id
                LEFT JOIN mentors m ON t.mentor_id = m.id
                LEFT JOIN users m_u ON m.user_id = m_u.id
                ORDER BY t.id DESC
                """
                cursor.execute(sql)
            elif current_user["role"] == "mentor":
                # Tenants where user is mentor OR own tenant
                cursor.execute("SELECT id FROM mentors WHERE user_id = ?", (current_user["id"],))
                m_row = cursor.fetchone()
                mentor_id = m_row["id"] if m_row else -1

                sql = """
                SELECT t.*, u.full_name as founder_name, u.email as founder_email, u.phone as founder_phone,
                       b.name as business_name, m_u.full_name as mentor_name
                FROM incubation_tenants t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN businesses b ON t.business_id = b.id
                LEFT JOIN mentors m ON t.mentor_id = m.id
                LEFT JOIN users m_u ON m.user_id = m_u.id
                WHERE t.mentor_id = ? OR t.user_id = ?
                ORDER BY t.id DESC
                """
                cursor.execute(sql, (mentor_id, current_user["id"]))
            else:
                # Own tenants only
                sql = """
                SELECT t.*, u.full_name as founder_name, u.email as founder_email, u.phone as founder_phone,
                       b.name as business_name, m_u.full_name as mentor_name
                FROM incubation_tenants t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN businesses b ON t.business_id = b.id
                LEFT JOIN mentors m ON t.mentor_id = m.id
                LEFT JOIN users m_u ON m.user_id = m_u.id
                WHERE t.user_id = ?
                ORDER BY t.id DESC
                """
                cursor.execute(sql, (current_user["id"],))

            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"tenants": rows})

        # Incubation Journals for a tenant
        if path == "/api/incubation/journals":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            tenant_id = query.get("tenant_id", [""])[0].strip()
            if not tenant_id:
                conn.close()
                return self.send_error_json("tenant_id diperlukan.")

            cursor.execute("""
            SELECT j.*, u.full_name as author_name, u.role as author_role
            FROM incubation_journals j
            JOIN users u ON j.author_id = u.id
            WHERE j.tenant_id = ?
            ORDER BY j.created_at ASC
            """, (tenant_id,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"journals": rows})

        # Business Leads
        if path == "/api/leads":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            user_id = current_user["id"]
            if current_user["role"] == "admin":
                sql = """
                SELECT l.*, s.full_name as sender_name, s.email as sender_email,
                       b.name as business_name, o.full_name as owner_name
                FROM business_leads l
                JOIN users s ON l.sender_id = s.id
                JOIN businesses b ON l.recipient_business_id = b.id
                JOIN users o ON b.user_id = o.id
                ORDER BY l.id DESC
                """
                cursor.execute(sql)
            else:
                # Leads sent by user OR leads received by businesses owned by user
                sql = """
                SELECT l.*, s.full_name as sender_name, s.email as sender_email,
                       b.name as business_name, o.full_name as owner_name
                FROM business_leads l
                JOIN users s ON l.sender_id = s.id
                JOIN businesses b ON l.recipient_business_id = b.id
                JOIN users o ON b.user_id = o.id
                WHERE l.sender_id = ? OR b.user_id = ?
                ORDER BY l.id DESC
                """
                cursor.execute(sql, (user_id, user_id))

            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"leads": rows})

        # Lead messages
        if path == "/api/leads/messages":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            lead_id = query.get("lead_id", [""])[0].strip()
            if not lead_id:
                conn.close()
                return self.send_error_json("lead_id diperlukan.")

            cursor.execute("""
            SELECT lm.*, u.full_name as sender_name, u.role as sender_role
            FROM lead_messages lm
            JOIN users u ON lm.sender_id = u.id
            WHERE lm.lead_id = ?
            ORDER BY lm.created_at ASC
            """, (lead_id,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"messages": rows})

        # PKS Agreements
        if path == "/api/pks":
            current_user = self.get_current_user()
            is_admin = current_user and current_user["role"] == "admin"
            user_id = current_user["id"] if current_user else None

            if not current_user:
                # Public only sees finalized PKS with public summary permission
                sql = """
                SELECT p.id, p.title, p.scope, p.start_date, p.end_date, p.status, p.final_doc_ref,
                       p1.full_name as proposer_name, p2.full_name as partner_name,
                       b1.name as proposer_business, b2.name as partner_business
                FROM pks_agreements p
                JOIN users p1 ON p.proposer_id = p1.id
                JOIN users p2 ON p.partner_id = p2.id
                LEFT JOIN businesses b1 ON b1.user_id = p1.id
                LEFT JOIN businesses b2 ON b2.user_id = p2.id
                WHERE p.is_public_summary = 1 AND p.status = 'finalized'
                ORDER BY p.id DESC
                """
                cursor.execute(sql)
            elif is_admin:
                sql = """
                SELECT p.*, p1.full_name as proposer_name, p2.full_name as partner_name,
                       p1.email as proposer_email, p2.email as partner_email
                FROM pks_agreements p
                JOIN users p1 ON p.proposer_id = p1.id
                JOIN users p2 ON p.partner_id = p2.id
                ORDER BY p.id DESC
                """
                cursor.execute(sql)
            else:
                # User's own agreements + public finalized
                sql = """
                SELECT p.*, p1.full_name as proposer_name, p2.full_name as partner_name,
                       p1.email as proposer_email, p2.email as partner_email
                FROM pks_agreements p
                JOIN users p1 ON p.proposer_id = p1.id
                JOIN users p2 ON p.partner_id = p2.id
                WHERE p.proposer_id = ? OR p.partner_id = ? OR (p.is_public_summary = 1 AND p.status = 'finalized')
                ORDER BY p.id DESC
                """
                cursor.execute(sql, (user_id, user_id))

            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"agreements": rows})

        # PKS single detail with audit log
        if path.startswith("/api/pks/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                pks_id = int(parts[2])
                cursor.execute("""
                SELECT p.*, p1.full_name as proposer_name, p2.full_name as partner_name,
                       p1.email as proposer_email, p2.email as partner_email,
                       p1.profession as proposer_profession, p2.profession as partner_profession
                FROM pks_agreements p
                JOIN users p1 ON p.proposer_id = p1.id
                JOIN users p2 ON p.partner_id = p2.id
                WHERE p.id = ?
                """, (pks_id,))
                pks = cursor.fetchone()
                if not pks:
                    conn.close()
                    return self.send_error_json("PKS tidak ditemukan.", status_code=404)

                cursor.execute("""
                SELECT l.*, u.full_name as actor_name, u.role as actor_role
                FROM pks_audit_logs l
                JOIN users u ON l.actor_id = u.id
                WHERE l.pks_id = ?
                ORDER BY l.created_at ASC
                """, (pks_id,))
                logs = [dict(r) for r in cursor.fetchall()]
                conn.close()

                data = dict(pks)
                data["audit_logs"] = logs
                return self.send_json({"agreement": data})

        # KPI Dashboard Statistics (Target 2027 vs Actual DB)
        if path == "/api/kpi":
            # 2027 Target numbers from Strategic Plan document
            targets_2027 = {
                "validated_alumni": 500,
                "businesses": 100,
                "unique_class_participants": 200,
                "assisted_businesses": 60,
                "tenants": 20,
                "realized_pks": 8,
                "catalog_products": 80,
                "active_mentors": 25,
            }

            cursor.execute("SELECT COUNT(*) as c FROM users WHERE status = 'approved' AND role != 'admin'")
            actual_alumni = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM businesses WHERE is_curated = 1")
            actual_businesses = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(DISTINCT user_id) as c FROM class_enrollments")
            actual_class_participants = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM incubation_tenants WHERE status IN ('accepted', 'traction', 'scaling')")
            actual_assisted_businesses = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM incubation_tenants WHERE status = 'accepted'")
            actual_tenants = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM pks_agreements WHERE status = 'finalized'")
            actual_pks = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM products WHERE is_curated = 1")
            actual_catalog_products = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM mentors WHERE status = 'approved' AND is_active = 1")
            actual_mentors = cursor.fetchone()["c"]

            conn.close()
            return self.send_json({
                "targets_2027": targets_2027,
                "actuals": {
                    "validated_alumni": actual_alumni,
                    "businesses": actual_businesses,
                    "unique_class_participants": actual_class_participants,
                    "assisted_businesses": actual_assisted_businesses,
                    "tenants": actual_tenants,
                    "realized_pks": actual_pks,
                    "catalog_products": actual_catalog_products,
                    "active_mentors": actual_mentors,
                }
            })

        # Announcements
        if path == "/api/announcements":
            cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"announcements": rows})

        # Data Requests (PDP)
        if path == "/api/data-requests":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            if current_user["role"] == "admin":
                sql = """
                SELECT dr.*, u.full_name, u.email, u.phone
                FROM data_requests dr
                JOIN users u ON dr.user_id = u.id
                ORDER BY dr.id DESC
                """
                cursor.execute(sql)
            else:
                sql = """
                SELECT dr.*, u.full_name, u.email, u.phone
                FROM data_requests dr
                JOIN users u ON dr.user_id = u.id
                WHERE dr.user_id = ?
                ORDER BY dr.id DESC
                """
                cursor.execute(sql, (current_user["id"],))

            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return self.send_json({"requests": rows})

        conn.close()
        return self.send_error_json("API endpoint tidak ditemukan.", status_code=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_body()

        conn = get_db()
        cursor = conn.cursor()

        # Login
        if path == "/api/auth/login":
            email = body.get("email", "").strip().lower()
            password = body.get("password", "").strip()

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            if not user or not verify_password(password, user["password_hash"], user["salt"]):
                conn.close()
                return self.send_error_json("Email atau kata sandi tidak cocok.", status_code=401)

            token = uuid.uuid4().hex
            expires_at = time.time() + SESSION_TTL_SECONDS
            SESSIONS[token] = {
                "id": user["id"],
                "role": user["role"],
                "email": user["email"],
                "full_name": user["full_name"],
                "expires_at": expires_at,
            }
            conn.close()

            cookie_val = f"maliki_session={token}; Path=/; HttpOnly; Max-Age={SESSION_TTL_SECONDS}; SameSite=Lax"
            if COOKIE_SECURE:
                cookie_val += "; Secure"

            return self.send_json({
                "message": "Login berhasil.",
                "user": {
                    "id": user["id"],
                    "email": user["email"],
                    "role": user["role"],
                    "full_name": user["full_name"],
                    "status": user["status"]
                }
            }, extra_headers={"Set-Cookie": cookie_val})

        # Register
        if path == "/api/auth/register":
            email = body.get("email", "").strip().lower()
            password = body.get("password", "").strip()
            full_name = body.get("full_name", "").strip()
            nim = body.get("nim", "").strip()
            faculty = body.get("faculty", "").strip()
            graduation_year = body.get("graduation_year", "")
            profession = body.get("profession", "").strip()
            company = body.get("company", "").strip()
            province = body.get("province", "").strip()
            city = body.get("city", "").strip()
            phone = body.get("phone", "").strip()
            linkedin = body.get("linkedin", "").strip()
            bio = body.get("bio", "").strip()
            consent_data = body.get("consent_data", 1)

            if not email or not password or not full_name:
                conn.close()
                return self.send_error_json("Email, kata sandi, dan nama lengkap wajib diisi.")

            if len(password) < 8:
                conn.close()
                return self.send_error_json("Kata sandi minimal 8 karakter.")

            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                return self.send_error_json("Email sudah terdaftar.")

            pwd_hash, salt = hash_password(password)
            try:
                cursor.execute("""
                INSERT INTO users (email, password_hash, salt, role, full_name, nim, faculty, graduation_year,
                                   profession, company, province, city, phone, linkedin, bio, consent_data, status)
                VALUES (?, ?, ?, 'alumni', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (email, pwd_hash, salt, full_name, nim, faculty, graduation_year or None,
                      profession, company, province, city, phone, linkedin, bio, 1 if consent_data else 0))
                user_id = cursor.lastrowid
                conn.commit()

                # Automatic session login after registration
                token = uuid.uuid4().hex
                expires_at = time.time() + SESSION_TTL_SECONDS
                SESSIONS[token] = {
                    "id": user_id,
                    "role": "alumni",
                    "email": email,
                    "full_name": full_name,
                    "expires_at": expires_at,
                }
                conn.close()

                cookie_val = f"maliki_session={token}; Path=/; HttpOnly; Max-Age={SESSION_TTL_SECONDS}; SameSite=Lax"
                if COOKIE_SECURE:
                    cookie_val += "; Secure"

                return self.send_json({
                    "message": "Pendaftaran berhasil! Akun menunggu verifikasi pengurus.",
                    "user": {"id": user_id, "email": email, "role": "alumni", "full_name": full_name, "status": "pending"}
                }, extra_headers={"Set-Cookie": cookie_val})
            except Exception as e:
                conn.close()
                return self.send_error_json(f"Gagal mendaftar: {e}", status_code=500)

        # Logout
        if path == "/api/auth/logout":
            cookies = self.get_cookies()
            token = cookies.get("maliki_session")
            if token and token in SESSIONS:
                del SESSIONS[token]
            conn.close()
            return self.send_json({"message": "Berhasil keluar."}, extra_headers={
                "Set-Cookie": "maliki_session=; Path=/; Max-Age=0; HttpOnly"
            })

        # Register Business
        if path == "/api/businesses":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            name = body.get("name", "").strip()
            sector = body.get("sector", "").strip()
            description = body.get("description", "").strip()
            province = body.get("province", "").strip()
            city = body.get("city", "").strip()
            address = body.get("address", "").strip()
            website = body.get("website", "").strip()
            contact_wa = body.get("contact_wa", "").strip()

            if not name or not sector:
                conn.close()
                return self.send_error_json("Nama usaha dan sektor bisnis wajib diisi.")

            cursor.execute("""
            INSERT INTO businesses (user_id, name, sector, description, province, city, address, website, contact_wa, is_curated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (current_user["id"], name, sector, description, province, city, address, website, contact_wa))
            conn.commit()
            biz_id = cursor.lastrowid
            conn.close()
            return self.send_json({"message": "Usaha berhasil didaftarkan dan menunggu kurasi pengurus.", "id": biz_id})

        # Add Product
        if path == "/api/products":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            business_id = body.get("business_id")
            name = body.get("name", "").strip()
            category = body.get("category", "").strip()
            description = body.get("description", "").strip()
            price = float(body.get("price", 0) or 0)
            photo_url = body.get("photo_url", "").strip()
            ref_link = body.get("ref_link", "").strip()

            if not business_id or not name or not category:
                conn.close()
                return self.send_error_json("Pilih usaha, nama produk, dan kategori.")

            # Ensure business belongs to user or admin
            cursor.execute("SELECT user_id FROM businesses WHERE id = ?", (business_id,))
            biz = cursor.fetchone()
            if not biz or (biz["user_id"] != current_user["id"] and current_user["role"] != "admin"):
                conn.close()
                return self.send_error_json("Anda tidak memiliki akses ke usaha ini.", status_code=403)

            cursor.execute("""
            INSERT INTO products (business_id, name, category, description, price, photo_url, ref_link, is_curated)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (business_id, name, category, description, price, photo_url, ref_link))
            conn.commit()
            prod_id = cursor.lastrowid
            conn.close()
            return self.send_json({"message": "Produk/jasa berhasil ditambahkan dan menunggu kurasi.", "id": prod_id})

        # Delete Product
        if path == "/api/products/delete":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            prod_id = body.get("product_id")
            if not prod_id:
                conn.close()
                return self.send_error_json("product_id diperlukan.")

            cursor.execute("""
            SELECT p.id, b.user_id as owner_id
            FROM products p
            JOIN businesses b ON p.business_id = b.id
            WHERE p.id = ?
            """, (prod_id,))
            prod = cursor.fetchone()
            if not prod:
                conn.close()
                return self.send_error_json("Produk tidak ditemukan.", status_code=404)

            if current_user["role"] != "admin" and prod["owner_id"] != current_user["id"]:
                conn.close()
                return self.send_error_json("Anda tidak memiliki izin menghapus produk ini.", status_code=403)

            cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Produk/jasa berhasil dihapus dari katalog."})

        # Apply as Mentor
        if path == "/api/mentors/apply":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            expertise = body.get("expertise", "").strip()
            years_experience = int(body.get("years_experience", 1) or 1)
            bio = body.get("bio", "").strip()
            portfolio_url = body.get("portfolio_url", "").strip()

            if not expertise:
                conn.close()
                return self.send_error_json("Bidang keahlian wajib diisi.")

            cursor.execute("""
            INSERT INTO mentors (user_id, expertise, years_experience, bio, portfolio_url, status, is_active)
            VALUES (?, ?, ?, ?, ?, 'pending', 1)
            ON CONFLICT(user_id) DO UPDATE SET
                expertise=excluded.expertise,
                years_experience=excluded.years_experience,
                bio=excluded.bio,
                portfolio_url=excluded.portfolio_url,
                status='pending'
            """, (current_user["id"], expertise, years_experience, bio, portfolio_url))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Pengajuan mentor berhasil dikirim dan menunggu review pengurus."})

        # Create Class (Admin Only)
        if path == "/api/classes":
            if not self.require_admin():
                conn.close()
                return

            title = body.get("title", "").strip()
            description = body.get("description", "").strip()
            instructor = body.get("instructor", "").strip()
            schedule = body.get("schedule", "").strip()
            location = body.get("location", "").strip()
            quota = int(body.get("quota", 50) or 50)

            if not title or not instructor:
                conn.close()
                return self.send_error_json("Judul kelas dan nama pemateri wajib diisi.")

            cursor.execute("""
            INSERT INTO classes (title, description, instructor, schedule, location, quota, is_open)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (title, description, instructor, schedule, location, quota))
            conn.commit()
            cls_id = cursor.lastrowid
            conn.close()
            return self.send_json({"message": "Kelas alumni berhasil dibuat.", "id": cls_id})

        # Enroll in Class
        if path == "/api/classes/enroll":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            class_id = body.get("class_id")
            if not class_id:
                conn.close()
                return self.send_error_json("class_id diperlukan.")

            # Check class quota & availability
            cursor.execute("SELECT quota, is_open, (SELECT COUNT(*) FROM class_enrollments WHERE class_id = ?) as cnt FROM classes WHERE id = ?", (class_id, class_id))
            cls = cursor.fetchone()
            if not cls:
                conn.close()
                return self.send_error_json("Kelas tidak ditemukan.", status_code=404)
            if not cls["is_open"]:
                conn.close()
                return self.send_error_json("Pendaftaran untuk kelas ini telah ditutup.")
            if cls["cnt"] >= cls["quota"]:
                conn.close()
                return self.send_error_json("Kuota kelas telah penuh.")

            try:
                cursor.execute("""
                INSERT INTO class_enrollments (class_id, user_id, is_graduated)
                VALUES (?, ?, 0)
                """, (class_id, current_user["id"]))
                conn.commit()
                conn.close()
                return self.send_json({"message": "Pendaftaran kelas berhasil!"})
            except sqlite3.IntegrityError:
                conn.close()
                return self.send_error_json("Anda sudah terdaftar di kelas ini.")

        # Apply for Incubation
        if path == "/api/incubation/apply":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            business_id = body.get("business_id") or None
            business_idea = body.get("business_idea", "").strip()
            stage = body.get("stage", "ideation").strip()
            need_desc = body.get("need_desc", "").strip()

            if not business_idea:
                conn.close()
                return self.send_error_json("Deskripsi ide atau profil usaha wajib diisi.")

            cursor.execute("""
            INSERT INTO incubation_tenants (user_id, business_id, business_idea, stage, need_desc, status)
            VALUES (?, ?, ?, ?, ?, 'submitted')
            """, (current_user["id"], business_id, business_idea, stage, need_desc))
            conn.commit()
            t_id = cursor.lastrowid
            conn.close()
            return self.send_json({"message": "Pengajuan tenant inkubasi berhasil didaftarkan.", "id": t_id})

        # Add Incubation Journal
        if path == "/api/incubation/journal":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            tenant_id = body.get("tenant_id")
            note_type = body.get("note_type", "progress").strip()
            notes = body.get("notes", "").strip()

            if not tenant_id or not notes:
                conn.close()
                return self.send_error_json("tenant_id dan catatan wajib diisi.")

            cursor.execute("""
            INSERT INTO incubation_journals (tenant_id, author_id, note_type, notes)
            VALUES (?, ?, ?, ?)
            """, (tenant_id, current_user["id"], note_type, notes))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Catatan jurnal berhasil ditambahkan."})

        # Send Business Lead
        if path == "/api/leads":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            recipient_business_id = body.get("business_id")
            title = body.get("title", "").strip()
            message = body.get("message", "").strip()

            if not recipient_business_id or not title or not message:
                conn.close()
                return self.send_error_json("Usaha tujuan, judul peluang, dan pesan wajib diisi.")

            cursor.execute("""
            INSERT INTO business_leads (sender_id, recipient_business_id, title, message, status)
            VALUES (?, ?, ?, ?, 'new')
            """, (current_user["id"], recipient_business_id, title, message))
            lead_id = cursor.lastrowid

            cursor.execute("""
            INSERT INTO lead_messages (lead_id, sender_id, message)
            VALUES (?, ?, ?)
            """, (lead_id, current_user["id"], message))

            conn.commit()
            conn.close()
            return self.send_json({"message": "Peluang kerja sama (lead) berhasil dikirim.", "id": lead_id})

        # Reply in Lead Message Chat
        if path == "/api/leads/messages":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            lead_id = body.get("lead_id")
            message = body.get("message", "").strip()

            if not lead_id or not message:
                conn.close()
                return self.send_error_json("lead_id dan isi pesan wajib diisi.")

            cursor.execute("""
            INSERT INTO lead_messages (lead_id, sender_id, message)
            VALUES (?, ?, ?)
            """, (lead_id, current_user["id"], message))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Pesan berhasil dikirim."})

        # Propose PKS
        if path == "/api/pks":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            partner_id = body.get("partner_id")
            title = body.get("title", "").strip()
            scope = body.get("scope", "").strip()
            start_date = body.get("start_date", "").strip()
            end_date = body.get("end_date", "").strip()
            content = body.get("content", "").strip()

            if not partner_id or not title or not content:
                conn.close()
                return self.send_error_json("Mitra kerja sama, judul PKS, dan klausul rancangan perjanjian wajib diisi.")

            if int(partner_id) == current_user["id"]:
                conn.close()
                return self.send_error_json("PKS tidak bisa ditujukan kepada diri sendiri.")

            cursor.execute("""
            INSERT INTO pks_agreements (proposer_id, partner_id, title, scope, start_date, end_date, content,
                                        proposer_agreed, partner_agreed, admin_reviewed, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, 0, 'draft')
            """, (current_user["id"], partner_id, title, scope, start_date, end_date, content))
            pks_id = cursor.lastrowid

            cursor.execute("""
            INSERT INTO pks_audit_logs (pks_id, actor_id, action, notes)
            VALUES (?, ?, 'DRAFT_CREATED', 'Alumni mengajukan rancangan draf PKS kepada mitra.')
            """, (pks_id, current_user["id"]))

            conn.commit()
            conn.close()
            return self.send_json({"message": "Rancangan PKS berhasil diajukan kepada mitra.", "id": pks_id})

        # Submit Data Privacy Request
        if path == "/api/data-requests":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            req_type = body.get("request_type", "access").strip()
            details = body.get("details", "").strip()

            if not details:
                conn.close()
                return self.send_error_json("Keterangan permintaan data pribadi wajib diisi.")

            cursor.execute("""
            INSERT INTO data_requests (user_id, request_type, details, status)
            VALUES (?, ?, ?, 'pending')
            """, (current_user["id"], req_type, details))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Permintaan hak data pribadi telah diterima dan akan diproses secara administratif."})

        # Create Announcement (Admin Only)
        if path == "/api/announcements":
            if not self.require_admin():
                conn.close()
                return

            title = body.get("title", "").strip()
            content = body.get("content", "").strip()
            cat = body.get("category", "info").strip()

            if not title or not content:
                conn.close()
                return self.send_error_json("Judul dan konten pengumuman wajib diisi.")

            cursor.execute("INSERT INTO announcements (title, content, category) VALUES (?, ?, ?)", (title, content, cat))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Pengumuman berhasil diterbitkan."})

        conn.close()
        return self.send_error_json("API endpoint POST tidak ditemukan.", status_code=404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_body()

        conn = get_db()
        cursor = conn.cursor()

        # Update Current User Profile
        if path == "/api/auth/profile":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            full_name = body.get("full_name", "").strip()
            profession = body.get("profession", "").strip()
            company = body.get("company", "").strip()
            province = body.get("province", "").strip()
            city = body.get("city", "").strip()
            phone = body.get("phone", "").strip()
            linkedin = body.get("linkedin", "").strip()
            bio = body.get("bio", "").strip()

            cursor.execute("""
            UPDATE users SET full_name = ?, profession = ?, company = ?, province = ?, city = ?, phone = ?, linkedin = ?, bio = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (full_name, profession, company, province, city, phone, linkedin, bio, current_user["id"]))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Profil berhasil diperbarui."})

        # Admin: Verify / Reject Alumni
        if path == "/api/alumni/verify":
            if not self.require_admin():
                conn.close()
                return

            user_id = body.get("user_id")
            status = body.get("status", "approved")
            if not user_id:
                conn.close()
                return self.send_error_json("user_id diperlukan.")

            cursor.execute("UPDATE users SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, user_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": f"Status verifikasi alumni diubah menjadi '{status}'."})

        # Admin: Curate Business
        if path == "/api/businesses/curate":
            if not self.require_admin():
                conn.close()
                return

            business_id = body.get("business_id")
            is_curated = 1 if body.get("is_curated") else 0
            if not business_id:
                conn.close()
                return self.send_error_json("business_id diperlukan.")

            cursor.execute("UPDATE businesses SET is_curated = ? WHERE id = ?", (is_curated, business_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Status kurasi usaha berhasil diperbarui."})

        # Admin: Curate Product
        if path == "/api/products/curate":
            if not self.require_admin():
                conn.close()
                return

            product_id = body.get("product_id")
            is_curated = 1 if body.get("is_curated") else 0
            if not product_id:
                conn.close()
                return self.send_error_json("product_id diperlukan.")

            cursor.execute("UPDATE products SET is_curated = ? WHERE id = ?", (is_curated, product_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Status kurasi produk berhasil diperbarui."})

        # Admin: Review Mentor Application
        if path == "/api/mentors/review":
            if not self.require_admin():
                conn.close()
                return

            mentor_id = body.get("mentor_id")
            status = body.get("status", "approved")
            if not mentor_id:
                conn.close()
                return self.send_error_json("mentor_id diperlukan.")

            cursor.execute("UPDATE mentors SET status = ? WHERE id = ?", (status, mentor_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": f"Status mentor diperbarui menjadi '{status}'."})

        # Admin: Review Incubation Tenant & Assign Mentor
        if path == "/api/incubation/review":
            if not self.require_admin():
                conn.close()
                return

            tenant_id = body.get("tenant_id")
            status = body.get("status", "accepted")
            mentor_id = body.get("mentor_id") or None

            if not tenant_id:
                conn.close()
                return self.send_error_json("tenant_id diperlukan.")

            cursor.execute("""
            UPDATE incubation_tenants SET status = ?, mentor_id = ?
            WHERE id = ?
            """, (status, mentor_id, tenant_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Status tenant dan penugasan mentor berhasil diperbarui."})

        # Admin: Mark Class Graduation
        if path == "/api/classes/graduate":
            if not self.require_admin():
                conn.close()
                return

            enrollment_id = body.get("enrollment_id")
            is_graduated = 1 if body.get("is_graduated") else 0
            cert_num = body.get("certificate_num", f"CERT-MALIKI-{int(time.time())}")

            cursor.execute("""
            UPDATE class_enrollments
            SET is_graduated = ?, graduated_at = CURRENT_TIMESTAMP, certificate_num = ?
            WHERE id = ?
            """, (is_graduated, cert_num if is_graduated else None, enrollment_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Status kelulusan peserta kelas berhasil diperbarui."})

        # Partner: Agree on PKS Draft
        if path == "/api/pks/agree":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            pks_id = body.get("pks_id")
            cursor.execute("SELECT * FROM pks_agreements WHERE id = ?", (pks_id,))
            pks = cursor.fetchone()
            if not pks:
                conn.close()
                return self.send_error_json("PKS tidak ditemukan.", status_code=404)

            if pks["partner_id"] != current_user["id"]:
                conn.close()
                return self.send_error_json("Hanya mitra yang ditunjuk yang dapat menyetujui draf ini.", status_code=403)

            cursor.execute("""
            UPDATE pks_agreements
            SET partner_agreed = 1, status = 'partner_agreed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (pks_id,))

            cursor.execute("""
            INSERT INTO pks_audit_logs (pks_id, actor_id, action, notes)
            VALUES (?, ?, 'PARTNER_AGREED', 'Mitra telah menyetujui draf kesepakatan.')
            """, (pks_id, current_user["id"]))

            conn.commit()
            conn.close()
            return self.send_json({"message": "Draf PKS telah disetujui. Siap direview oleh pengurus IKA."})

        # Admin: Review PKS & Set Final Document Reference
        if path == "/api/pks/admin-review":
            admin = self.require_admin()
            if not admin:
                conn.close()
                return

            pks_id = body.get("pks_id")
            status = body.get("status", "finalized")  # finalized, admin_reviewed, rejected
            admin_notes = body.get("admin_notes", "").strip()
            final_doc_ref = body.get("final_doc_ref", "").strip()
            is_public_summary = 1 if body.get("is_public_summary") else 0

            cursor.execute("""
            UPDATE pks_agreements
            SET admin_reviewed = 1, admin_notes = ?, final_doc_ref = ?, is_public_summary = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (admin_notes, final_doc_ref, is_public_summary, status, pks_id))

            cursor.execute("""
            INSERT INTO pks_audit_logs (pks_id, actor_id, action, notes)
            VALUES (?, ?, ?, ?)
            """, (pks_id, admin["id"], f"ADMIN_{status.upper()}", f"Review pengurus: {admin_notes}. Ref arsip: {final_doc_ref or '-'}; Izin tampil publik: {is_public_summary}"))

            conn.commit()
            conn.close()
            return self.send_json({"message": "Review PKS oleh pengurus berhasil disimpan."})

        # Admin: Respond to Data Privacy Request
        if path == "/api/data-requests/respond":
            admin = self.require_admin()
            if not admin:
                conn.close()
                return

            req_id = body.get("request_id")
            status = body.get("status", "processed")
            response_text = body.get("admin_response", "").strip()

            cursor.execute("""
            UPDATE data_requests
            SET status = ?, admin_response = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (status, response_text, req_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Tanggapan permohonan data pribadi berhasil disimpan."})

        # Update Lead Status
        if path == "/api/leads/status":
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            lead_id = body.get("lead_id")
            status = body.get("status", "in_progress")

            cursor.execute("UPDATE business_leads SET status = ? WHERE id = ?", (status, lead_id))
            conn.commit()
            conn.close()
            return self.send_json({"message": "Status lead berhasil diperbarui."})

        conn.close()
        return self.send_error_json("API endpoint PUT tidak ditemukan.", status_code=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        conn = get_db()
        cursor = conn.cursor()

        if path.startswith("/api/products/"):
            current_user = self.require_auth()
            if not current_user:
                conn.close()
                return

            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2].isdigit():
                prod_id = int(parts[2])
                cursor.execute("""
                SELECT p.id, b.user_id as owner_id
                FROM products p
                JOIN businesses b ON p.business_id = b.id
                WHERE p.id = ?
                """, (prod_id,))
                prod = cursor.fetchone()
                if not prod:
                    conn.close()
                    return self.send_error_json("Produk tidak ditemukan.", status_code=404)

                if current_user["role"] != "admin" and prod["owner_id"] != current_user["id"]:
                    conn.close()
                    return self.send_error_json("Anda tidak memiliki izin menghapus produk ini.", status_code=403)

                cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
                conn.commit()
                conn.close()
                return self.send_json({"message": "Produk/jasa berhasil dihapus dari katalog."})

        conn.close()
        return self.send_error_json("API endpoint DELETE tidak ditemukan.", status_code=404)


def run_server():
    init_db()
    if IS_DEMO:
        seed_demo_data()
    else:
        ensure_bootstrap_admin()

    server_address = (HOST, PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, MalikiRequestHandler)

    mode_label = "DEMO SIMULATION" if IS_DEMO else "PRODUCTION / STANDARD"
    print("=" * 65)
    print("  MALIKI ALUMNI CONNECT - PORTAL JEJARING & EKONOMI ALUMNI")
    print(f"  Mode Server : {mode_label}")
    print(f"  Akses Web   : http://{HOST}:{PORT}")
    print(f"  Database    : {DB_PATH}")
    if IS_DEMO:
        print("  Akun Demo:")
        print("    - Admin/Pengurus : admin@demo.local / DemoMaliki2026!")
        print("    - Alumni/Usaha   : alumni@demo.local / DemoMaliki2026!")
        print("    - Alumni/Mitra   : mitra@demo.local / DemoMaliki2026!")
        print("    - Mentor         : mentor@demo.local / DemoMaliki2026!")
    print("=" * 65)
    print("Tekan Ctrl+C di terminal ini untuk mematikan server.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n=> Server dimatikan.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
