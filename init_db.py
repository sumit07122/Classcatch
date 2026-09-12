"""
ClassCatch - Universal Database Initializer & Verification Script
=================================================================
Works with any PostgreSQL database (Neon.tech [100% Free], Supabase, Render, etc.)
or local SQLite fallback.

Usage:
    # Set your DATABASE_URL in .env, then run:
    python init_db.py
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file with override
load_dotenv(override=True)

from app import app
from models import db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord, Deadline, Resource
from seed import seed_database

def setup_database():
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print("=" * 65)
        print("[*] ClassCatch - Cloud Database Initialization")
        print("=" * 65)
        
        # Mask credentials in display
        if "@" in db_uri:
            masked_uri = db_uri.split("@")[-1]
            print(f"[*] Target Host: {masked_uri}")
        else:
            print(f"[*] Target Database URI: {db_uri}")

        if "sqlite" in db_uri:
            print("\n[INFO] Currently running with local SQLite fallback.")
            print("       To connect your 100% Free Neon.tech cloud Postgres database:")
            print("       1. Go to https://neon.tech and sign in with GitHub (0 cost, no card).")
            print("       2. Copy your Connection String from the dashboard.")
            print("       3. Put it in .env: DATABASE_URL=postgresql://...\n")

        try:
            print("[*] Connecting to database and creating tables...")
            db.create_all()
            print("[+] Tables successfully created and verified:")
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
                print("[+] Seeding completed successfully!")
            else:
                course_count = Course.query.count()
                print(f"\n[OK] Database already populated ({user_count} users, {course_count} courses).")

            print("\n" + "=" * 65)
            print("[SUCCESS] Database is 100% ready and connected!")
            print("=" * 65)

        except Exception as e:
            print(f"\n[ERROR] Database connection failed: {e}")
            print("\nTroubleshooting tips:")
            print("  1. Verify your DATABASE_URL in the .env file.")
            print("  2. Ensure your password is typed correctly.")
            print("  3. For Neon.tech, ensure '?sslmode=require' is included at the end of the URL.")
            sys.exit(1)

if __name__ == '__main__':
    setup_database()
