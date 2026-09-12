"""
ClassCatch - Clean Slate Database Utility
=========================================
Resets the Neon Cloud PostgreSQL database to a clean, production-ready state.

Usage:
    # 1. Clean all test activity (leaves courses intact so students have their timetable ready):
    python clean_slate.py --activity-only

    # 2. Complete 100% factory reset (wipes everything including courses):
    python clean_slate.py --full-reset
"""

import sys
import argparse
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv(override=True)

from app import app
from models import db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord, Deadline, Resource

def clean_database(mode="activity-only"):
    with app.app_context():
        print("=" * 65)
        print("[*] ClassCatch - Production Database Cleaner")
        print("=" * 65)
        print(f"[*] Mode: {mode.upper()}")
        print(f"[*] Target Database: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")

        if mode == "full-reset":
            print("\n[*] Performing FULL factory wipe...")
            # Drop and re-create all fresh empty tables
            db.drop_all()
            db.create_all()
            print("[+] All tables dropped and re-created completely fresh and empty.")
            print("[+] Ready for your real college launch!")
            print("    - Students can register fresh accounts at /register")
            print("    - You can add real subjects at /course/new")

        elif mode == "activity-only":
            print("\n[*] Clearing mock test activity while preserving course timetable...")
            # Clear test users, summaries, chats, deadlines, resources
            Summary.query.delete()
            ChatMessage.query.delete()
            Announcement.query.delete()
            AttendanceRecord.query.delete()
            Deadline.query.delete()
            Resource.query.delete()
            User.query.delete()
            db.session.commit()
            print("[+] Cleared all mock users, notes, chat messages, and deadlines.")
            print(f"[+] Preserved {Course.query.count()} courses for your students:")
            for c in Course.query.all():
                print(f"    - {c.code}: {c.name} ({c.schedule})")
            print("\n[+] Ready for your real students to sign up and start posting!")

        print("=" * 65)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reset ClassCatch to clean production state.")
    parser.add_argument("--full-reset", action="store_true", help="Wipe all data and courses completely")
    parser.add_argument("--activity-only", action="store_true", help="Wipe mock users & notes but keep course schedule")
    args = parser.parse_args()

    if args.full_reset:
        clean_database("full-reset")
    elif args.activity_only:
        clean_database("activity-only")
    else:
        print("Please choose a clean mode:")
        print("  python clean_slate.py --activity-only   (Clears dummy students/notes, keeps courses)")
        print("  python clean_slate.py --full-reset       (Clears EVERYTHING completely empty)")
