import unittest
import sqlite3
import tempfile
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app


class TestMalikiWorkflows(unittest.TestCase):
    def setUp(self):
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        app.DB_PATH = Path(self.temp_db.name)
        app.SESSIONS.clear()
        app.init_db()

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass

    def test_password_hashing(self):
        pwd = "SecretPassword123!"
        h, salt = app.hash_password(pwd)
        self.assertTrue(app.verify_password(pwd, h, salt))
        self.assertFalse(app.verify_password("WrongPassword", h, salt))

    def test_demo_seeding(self):
        app.seed_demo_data()
        conn = app.get_db()
        cursor = conn.cursor()

        # Check users count
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        user_count = cursor.fetchone()["cnt"]
        self.assertGreaterEqual(user_count, 4)

        # Check demo admin
        cursor.execute("SELECT * FROM users WHERE email = 'admin@demo.local'")
        admin = cursor.fetchone()
        self.assertIsNotNone(admin)
        self.assertEqual(admin["role"], "admin")

        # Check demo businesses
        cursor.execute("SELECT COUNT(*) as cnt FROM businesses WHERE is_curated = 1")
        biz_count = cursor.fetchone()["cnt"]
        self.assertGreaterEqual(biz_count, 2)

        # Check demo products
        cursor.execute("SELECT COUNT(*) as cnt FROM products WHERE is_curated = 1")
        prod_count = cursor.fetchone()["cnt"]
        self.assertGreaterEqual(prod_count, 3)

        # Check demo mentor
        cursor.execute("SELECT COUNT(*) as cnt FROM mentors WHERE status = 'approved'")
        mentor_count = cursor.fetchone()["cnt"]
        self.assertGreaterEqual(mentor_count, 1)

        # Check demo class & enrollment
        cursor.execute("SELECT COUNT(*) as cnt FROM classes")
        class_count = cursor.fetchone()["cnt"]
        self.assertGreaterEqual(class_count, 2)

        cursor.execute("SELECT COUNT(*) as cnt FROM class_enrollments")
        enroll_count = cursor.fetchone()["cnt"]
        self.assertGreaterEqual(enroll_count, 2)

        # Check demo PKS
        cursor.execute("SELECT * FROM pks_agreements WHERE status = 'finalized'")
        pks = cursor.fetchone()
        self.assertIsNotNone(pks)
        self.assertEqual(pks["is_public_summary"], 1)

        # Check PKS audit logs
        cursor.execute("SELECT COUNT(*) as cnt FROM pks_audit_logs WHERE pks_id = ?", (pks["id"],))
        logs_count = cursor.fetchone()["cnt"]
        self.assertGreaterEqual(logs_count, 3)

        conn.close()

    def test_pks_lifecycle_workflow(self):
        # Create 2 users: proposer and partner
        conn = app.get_db()
        cursor = conn.cursor()

        h1, s1 = app.hash_password("Pass123!")
        cursor.execute("""
        INSERT INTO users (email, password_hash, salt, role, full_name, status)
        VALUES ('p1@test.local', ?, ?, 'alumni', 'Alumni Satu', 'approved')
        """, (h1, s1))
        u1_id = cursor.lastrowid

        h2, s2 = app.hash_password("Pass123!")
        cursor.execute("""
        INSERT INTO users (email, password_hash, salt, role, full_name, status)
        VALUES ('p2@test.local', ?, ?, 'alumni', 'Alumni Dua', 'approved')
        """, (h2, s2))
        u2_id = cursor.lastrowid

        # 1. Proposer creates draft PKS
        cursor.execute("""
        INSERT INTO pks_agreements (proposer_id, partner_id, title, scope, content, proposer_agreed, partner_agreed, status)
        VALUES (?, ?, 'PKS Kerjasama Logistik', 'Distribusi Barang', 'Pasal 1 Ketentuan Umum...', 1, 0, 'draft')
        """, (u1_id, u2_id))
        pks_id = cursor.lastrowid

        cursor.execute("INSERT INTO pks_audit_logs (pks_id, actor_id, action) VALUES (?, ?, 'DRAFT_CREATED')", (pks_id, u1_id))

        # Check draft status
        cursor.execute("SELECT status, partner_agreed FROM pks_agreements WHERE id = ?", (pks_id,))
        pks = cursor.fetchone()
        self.assertEqual(pks["status"], "draft")
        self.assertEqual(pks["partner_agreed"], 0)

        # 2. Partner agrees to draft
        cursor.execute("""
        UPDATE pks_agreements SET partner_agreed = 1, status = 'partner_agreed' WHERE id = ?
        """, (pks_id,))
        cursor.execute("INSERT INTO pks_audit_logs (pks_id, actor_id, action) VALUES (?, ?, 'PARTNER_AGREED')", (pks_id, u2_id))

        # Check partner agreed
        cursor.execute("SELECT status, partner_agreed FROM pks_agreements WHERE id = ?", (pks_id,))
        pks = cursor.fetchone()
        self.assertEqual(pks["status"], "partner_agreed")
        self.assertEqual(pks["partner_agreed"], 1)

        # 3. Admin review and finalize with physical document reference
        admin_doc_ref = "ARSIP-IKA-PKS-TEST-001"
        cursor.execute("""
        UPDATE pks_agreements
        SET admin_reviewed = 1, final_doc_ref = ?, is_public_summary = 1, status = 'finalized'
        WHERE id = ?
        """, (admin_doc_ref, pks_id))

        cursor.execute("SELECT status, final_doc_ref, is_public_summary FROM pks_agreements WHERE id = ?", (pks_id,))
        pks = cursor.fetchone()
        self.assertEqual(pks["status"], "finalized")
        self.assertEqual(pks["final_doc_ref"], admin_doc_ref)
        self.assertEqual(pks["is_public_summary"], 1)

        conn.commit()
        conn.close()

    def test_incubation_and_journal_workflow(self):
        conn = app.get_db()
        cursor = conn.cursor()

        h, s = app.hash_password("Pass123!")
        cursor.execute("INSERT INTO users (email, password_hash, salt, role, full_name) VALUES ('founder@test.local', ?, ?, 'alumni', 'Founder')", (h, s))
        founder_id = cursor.lastrowid

        # Submit incubation
        cursor.execute("""
        INSERT INTO incubation_tenants (user_id, business_idea, stage, need_desc, status)
        VALUES (?, 'Startup EduTech AI', 'ideation', 'Perlu mentor bisnis', 'submitted')
        """, (founder_id,))
        tenant_id = cursor.lastrowid
        self.assertIsNotNone(tenant_id)

        # Admin approves tenant
        cursor.execute("UPDATE incubation_tenants SET status = 'accepted' WHERE id = ?", (tenant_id,))

        # Add journal entry
        cursor.execute("""
        INSERT INTO incubation_journals (tenant_id, author_id, note_type, notes)
        VALUES (?, ?, 'progress', 'Telah menyelesaikan riset pasar kepada 50 calon pengguna.')
        """, (tenant_id, founder_id))

        cursor.execute("SELECT COUNT(*) as cnt FROM incubation_journals WHERE tenant_id = ?", (tenant_id,))
        self.assertEqual(cursor.fetchone()["cnt"], 1)

        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
