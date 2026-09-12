"""
ClassCatch - Clean Slate Database Utility
=========================================
Resets the Neon Cloud PostgreSQL database to a clean, production-ready state.

Usage:
    # 1. Clean all test activity (leaves courses, feature flags, settings intact):
    python clean_slate.py --activity-only

    # 2. Complete factory reset (wipes tables, restores default settings & feature flags):
    python clean_slate.py --full-reset

    # 3. Create or promote a SuperAdmin account directly from CLI:
    python clean_slate.py --create-admin --name "Admin Name" --email "admin@college.edu" --password "securepass123"
"""

import sys
import argparse
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv(override=True)

from app import app
from models import (
    db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord,
    Deadline, Resource, CRAssignment, Report, AuditLog, FeatureFlag, SystemSetting
)

def clean_database(mode="activity-only"):
    with app.app_context():
        print("=" * 65)
        print("[*] ClassCatch - Production Database Cleaner")
        print("=" * 65)
        print(f"[*] Mode: {mode.upper()}")
        print(f"[*] Target Database: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]}")

        if mode == "full-reset":
            print("\n[*] Performing FULL factory wipe...")
            db.drop_all()
            db.create_all()

            # Seed default system settings
            settings = [
                SystemSetting(key="attendance_threshold", value="75.0", description="Institutional minimum attendance target percentage"),
                SystemSetting(key="maintenance_mode", value="false", description="Restricts student access for scheduled maintenance"),
                SystemSetting(key="registration_enabled", value="true", description="Allow new student registrations"),
                SystemSetting(key="default_semester", value="5", description="Default active academic semester")
            ]
            db.session.add_all(settings)

            # Seed default feature flags
            flags = [
                FeatureFlag(key="catchup_feed", name="Missed Class Catch-up Engine", description="Aggregated multi-course lecture catch-up feed", is_enabled=True),
                FeatureFlag(key="attendance_tracker", name="Attendance & Safe Bunk Predictor", description="Safe bunk and recovery math calculator", is_enabled=True),
                FeatureFlag(key="academic_vault", name="Academic Resource & PYQ Vault", description="Student-shared previous exam questions and notes", is_enabled=True),
                FeatureFlag(key="campus_chat", name="Unofficial Peer & Course Chat", description="Peer discussion and requirements exchange", is_enabled=True),
                FeatureFlag(key="anonymous_doubts", name="Anonymous Doubt Clearing Mode", description="Masks student identity for honest doubts", is_enabled=True),
                FeatureFlag(key="ai_ocr", name="AI Whiteboard-to-Notes OCR Engine", description="Transcribes classroom board photos into notes", is_enabled=True),
                FeatureFlag(key="morning_dispatch", name="Morning Timetable & WhatsApp Digest", description="Daily academic briefing simulation", is_enabled=True),
                FeatureFlag(key="karma_rewards", name="Peer Contribution & Karma System", description="Rewards students for quality lecture summaries", is_enabled=True)
            ]
            db.session.add_all(flags)
            db.session.commit()

            print("[+] All tables dropped and re-created completely fresh.")
            print("[+] Default feature flags and institutional settings restored.")
            print("[+] Ready for your real college launch!")

        elif mode == "activity-only":
            print("\n[*] Clearing mock test activity while preserving courses and configurations...")
            Report.query.delete()
            CRAssignment.query.delete()
            AuditLog.query.delete()
            Summary.query.delete()
            ChatMessage.query.delete()
            Announcement.query.delete()
            AttendanceRecord.query.delete()
            Deadline.query.delete()
            Resource.query.delete()
            User.query.delete()
            db.session.commit()
            print("[+] Cleared all mock users, notes, chat messages, reports, and deadlines.")
            print(f"[+] Preserved {Course.query.count()} courses for your students:")
            for c in Course.query.all():
                print(f"    - {c.code}: {c.name} ({c.schedule})")
            print("\n[+] Ready for your real students to sign up and start posting!")

        print("=" * 65)


def create_superadmin(name, email, password):
    """Create or elevate a user to SuperAdmin via CLI."""
    with app.app_context():
        user = User.query.filter_by(email=email.strip().lower()).first()
        if user:
            user.role = 'superadmin'
            user.name = name.strip()
            user.set_password(password)
            db.session.commit()
            print(f"[+] Existing user '{email}' elevated to SuperAdmin!")
        else:
            user = User(
                name=name.strip(),
                email=email.strip().lower(),
                role='superadmin',
                karma=1000,
                is_onboarded=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"[+] Created new SuperAdmin account: {email}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reset ClassCatch or manage administrator credentials.")
    parser.add_argument("--full-reset", action="store_true", help="Wipe all data and courses completely")
    parser.add_argument("--activity-only", action="store_true", help="Wipe mock users & notes but keep course schedule")
    parser.add_argument("--create-admin", action="store_true", help="Create or elevate a SuperAdmin account")
    parser.add_argument("--name", type=str, default="Platform SuperAdmin", help="Admin display name")
    parser.add_argument("--email", type=str, help="Admin email address")
    parser.add_argument("--password", type=str, help="Admin password")
    args = parser.parse_args()

    if args.create_admin:
        if not args.email or not args.password:
            print("Error: --email and --password are required when using --create-admin")
            sys.exit(1)
        create_superadmin(args.name, args.email, args.password)
    elif args.full_reset:
        clean_database("full-reset")
    elif args.activity_only:
        clean_database("activity-only")
    else:
        print("Please choose a command:")
        print("  python clean_slate.py --activity-only   (Clears dummy students/notes, keeps courses)")
        print("  python clean_slate.py --full-reset       (Clears EVERYTHING completely fresh)")
        print("  python clean_slate.py --create-admin --email admin@college.edu --password pass123")
