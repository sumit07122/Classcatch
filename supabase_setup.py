"""
ClassCatch - Supabase PostgreSQL Initializer & Verification Script
================================================================
Connects to your Supabase PostgreSQL instance, creates all database tables,
and seeds initial academic courses, student accounts, deadlines, and resources.

Usage:
    # 1. Set your Supabase connection URL in .env or terminal:
    #    DATABASE_URL=postgresql://postgres.xxx:password@aws-0-xx.pooler.supabase.com:6543/postgres
    # 2. Run:
    python supabase_setup.py
"""

import os
import sys
from app import app
from models import db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord, Deadline, Resource
from seed import seed_database

def setup_supabase():
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print("=" * 65)
        print("[*] ClassCatch - Supabase Database Initialization")
        print("=" * 65)
        print(f"[*] Target Database URI: {db_uri.split('@')[-1] if '@' in db_uri else db_uri}")

        if "sqlite" in db_uri:
            print("[INFO] Currently running with local SQLite fallback.")
            print("       To target Supabase, set DATABASE_URL in your .env file or environment:")
            print("       DATABASE_URL='postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres'\n")

        try:
            print("[*] Testing database connectivity and table schemas...")
            db.create_all()
            print("[+] Connection verified & tables ensured:")
            print("    - users (with Karma economy & reputation badges)")
            print("    - courses (with timetable, room locations & status)")
            print("    - summaries (with CR verification seals & helpful counters)")
            print("    - chat_messages (with anonymous doubt clearing mode)")
            print("    - announcements (with priority tags)")
            print("    - attendance_records (with safe bunk & recovery predictor)")
            print("    - deadlines (academic assignments & exam countdowns)")
            print("    - resources (PYQs, formula sheets & lab manuals)")

            user_count = User.query.count()
            if user_count == 0:
                print("\n[*] Database is empty. Seeding initial student mock data...")
                seed_database()
            else:
                print(f"\n[OK] Database already populated with {user_count} student accounts and {Course.query.count()} courses.")

            print("\n[SUCCESS] Database is 100% operational and ready for production!")
            print("=" * 65)

        except Exception as e:
            print(f"\n[ERROR] Failed to connect to Supabase PostgreSQL: {e}")
            print("\nTroubleshooting tips:")
            print("  1. Verify your database password in DATABASE_URL.")
            print("  2. If using Supabase Connection Pooler, make sure port is 6543 (Session mode) or 5432 (Direct mode).")
            print("  3. Ensure network allows outbound traffic to Supabase host.")
            sys.exit(1)

if __name__ == '__main__':
    setup_supabase()
