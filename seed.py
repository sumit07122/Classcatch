"""
ClassCatch Database Seeding Script — GLA University 2FE Pilot
============================================================
Pre-populates the database with:
- 10 Real GLA 2FE Academic Courses & Faculty
- Complete Monday–Friday 2FE Timetable Slots (AB-VI Room 306, AB-I Room 425, AB-V Room 218C)
- GLA Academic Leadership Records (HOD, Program Coordinator, Class Advisor)
- Official 2FE Student Roster Entries (@gla.ac.in)
- Verified GLA Student Accounts with Active 2FE Enrollments
- Course Summaries, Academic Deadlines, Attendance Records, and Announcements
- System Feature Flags and Institutional Settings

Usage:
    python seed.py
"""

import os
from datetime import date, timedelta
from app import app
from models import (
    db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord,
    Deadline, Resource, CRAssignment, Report, AuditLog, FeatureFlag, SystemSetting,
    Enrollment, RosterEntry, TimetableSlot, AcademicStaff, StorageFile
)

def seed_database():
    with app.app_context():
        print("[*] Initializing database schema...")
        db.create_all()

        # Clean existing data safely
        for model in [
            AuditLog, Report, CRAssignment, Resource, StorageFile, Deadline,
            AttendanceRecord, Announcement, ChatMessage, Summary, TimetableSlot,
            AcademicStaff, Enrollment, RosterEntry, Course, User, FeatureFlag, SystemSetting
        ]:
            try:
                db.session.query(model).delete()
            except Exception:
                pass
        db.session.commit()

        print("[*] Seeding Global Feature Flags and Institutional Settings...")
        feature_flags = [
            FeatureFlag(key="catchup_feed", name="Missed Class Catch-up Engine", description="Multi-course lecture catch-up feed", is_enabled=True),
            FeatureFlag(key="attendance_tracker", name="Attendance & Safe Bunk Predictor", description="Safe bunk and recovery calculator", is_enabled=True),
            FeatureFlag(key="academic_vault", name="Academic Resource & PYQ Vault", description="Student-shared previous exam questions and notes", is_enabled=True),
            FeatureFlag(key="campus_chat", name="Unofficial Peer & Course Chat", description="Peer discussion and requirements exchange", is_enabled=True),
            FeatureFlag(key="anonymous_doubts", name="Anonymous Doubt Clearing Mode", description="Masks student identity for honest doubts", is_enabled=True),
            FeatureFlag(key="ai_ocr", name="AI Whiteboard-to-Notes OCR Engine", description="Transcribes classroom board photos into notes", is_enabled=True),
            FeatureFlag(key="morning_dispatch", name="Morning Timetable & WhatsApp Digest", description="Daily academic briefing simulation", is_enabled=True),
            FeatureFlag(key="karma_rewards", name="Peer Contribution & Karma System", description="Rewards students for quality lecture summaries", is_enabled=True)
        ]
        db.session.add_all(feature_flags)

        system_settings = [
            SystemSetting(key="attendance_threshold", value="75.0", description="GLA University mandatory attendance percentage target"),
            SystemSetting(key="maintenance_mode", value="false", description="Restricts student access for scheduled maintenance"),
            SystemSetting(key="registration_enabled", value="true", description="Allow new student registrations"),
            SystemSetting(key="default_semester", value="3", description="Default active academic semester"),
            SystemSetting(key="college_name", value="GLA University, Mathura Campus", description="Active pilot university campus"),
            SystemSetting(key="active_pilot_section", value="2FE", description="Strictly restricted active pilot section")
        ]
        db.session.add_all(system_settings)
        db.session.commit()

        print("[*] Seeding GLA Academic Leadership Records...")
        staff_records = [
            AcademicStaff(
                name="Dr. Sandeep Kumar Rathore",
                employee_id="GLA107230",
                designation="Head of Department",
                department="CSE",
                email="hod.cse@gla.ac.in"
            ),
            AcademicStaff(
                name="Dr. Juginder Pal Singh",
                employee_id="GLA106249",
                designation="Program Co-Ordinator",
                department="CSE",
                email="pc.btech@gla.ac.in"
            ),
            AcademicStaff(
                name="Dr. Amit Kumar",
                employee_id="GLA123261",
                designation="Class Advisor",
                department="CSE",
                section="2FE",
                email="amit.kumar@gla.ac.in"
            )
        ]
        db.session.add_all(staff_records)
        db.session.commit()

        print("[*] Seeding Official 2FE Approved Student Roster (GLA University)...")
        roster_entries = [
            RosterEntry(email="aarav.patel@gla.ac.in", name="Aarav Patel", student_id="GLA26001", section="2FE", program="B.Tech CSE", semester=3, academic_year="2026-27"),
            RosterEntry(email="priya.singh@gla.ac.in", name="Priya Singh", student_id="GLA26002", section="2FE", program="B.Tech CSE", semester=3, academic_year="2026-27"),
            RosterEntry(email="rohit.verma@gla.ac.in", name="Rohit Verma", student_id="GLA26003", section="2FE", program="B.Tech CSE", semester=3, academic_year="2026-27"),
            RosterEntry(email="ananya.sharma@gla.ac.in", name="Ananya Sharma", student_id="GLA26004", section="2FE", program="B.Tech CSE", semester=3, academic_year="2026-27"),
            RosterEntry(email="vikram.aditya@gla.ac.in", name="Vikram Aditya", student_id="GLA26005", section="2FE", program="B.Tech CSE", semester=3, academic_year="2026-27"),
            RosterEntry(email="neha.gupta@gla.ac.in", name="Neha Gupta", student_id="GLA26006", section="2FE", program="B.Tech CSE", semester=3, academic_year="2026-27"),
            RosterEntry(email="rahul.mehta@gla.ac.in", name="Rahul Mehta", student_id="GLA26007", section="2FE", program="B.Tech CSE", semester=3, academic_year="2026-27")
        ]
        db.session.add_all(roster_entries)
        db.session.commit()

        print("[*] Seeding Accounts (Admins & Verified GLA 2FE Students)...")
        # System Admins
        superadmin = User(name="Platform SuperAdmin", email="superadmin@classcatch.edu", role="superadmin", karma=1000, is_verified=True, is_onboarded=True)
        superadmin.set_password("password123")

        admin = User(name="GLA CSE Admin", email="admin@classcatch.edu", role="admin", karma=500, is_verified=True, is_onboarded=True)
        admin.set_password("password123")

        # Verified 2FE Students with Official @gla.ac.in Institutional Accounts
        aarav = User(
            name="Aarav Patel",
            email="aarav.patel@gla.ac.in",
            student_id="GLA26001",
            role="cr",
            karma=340,
            college="GLA University, Mathura Campus",
            department="CSE",
            program="B.Tech CSE",
            semester=3,
            section="2FE",
            is_verified=True,
            is_onboarded=True
        )
        aarav.set_password("password123")

        priya = User(
            name="Priya Singh",
            email="priya.singh@gla.ac.in",
            student_id="GLA26002",
            role="student",
            karma=195,
            college="GLA University, Mathura Campus",
            department="CSE",
            program="B.Tech CSE",
            semester=3,
            section="2FE",
            is_verified=True,
            is_onboarded=True
        )
        priya.set_password("password123")

        rohit = User(
            name="Rohit Verma",
            email="rohit.verma@gla.ac.in",
            student_id="GLA26003",
            role="student",
            karma=85,
            college="GLA University, Mathura Campus",
            department="CSE",
            program="B.Tech CSE",
            semester=3,
            section="2FE",
            is_verified=True,
            is_onboarded=True
        )
        rohit.set_password("password123")

        ananya = User(
            name="Ananya Sharma",
            email="ananya.sharma@gla.ac.in",
            student_id="GLA26004",
            role="student",
            karma=60,
            college="GLA University, Mathura Campus",
            department="CSE",
            program="B.Tech CSE",
            semester=3,
            section="2FE",
            is_verified=True,
            is_onboarded=True
        )
        ananya.set_password("password123")

        db.session.add_all([superadmin, admin, aarav, priya, rohit, ananya])
        db.session.commit()

        # Mark roster entries registered
        for u in [aarav, priya, rohit, ananya]:
            re = RosterEntry.query.filter_by(email=u.email).first()
            if re:
                re.is_registered = True
        db.session.commit()

        print("[*] Creating Active 2FE Enrollments for Students...")
        for student in [aarav, priya, rohit, ananya]:
            enr = Enrollment(
                user_id=student.id,
                student_id=student.student_id,
                college="GLA University, Mathura Campus",
                department="CSE",
                program="B.Tech CSE",
                academic_year="2026-27",
                semester=3,
                section="2FE",
                is_lateral=True,
                status="approved",
                is_active=True,
                approved_by_id=admin.id
            )
            db.session.add(enr)
        db.session.commit()

        print("[*] Seeding 10 Real 2FE Courses (GLA B.Tech CSE Semester 3)...")
        c1 = Course(code="BCSC 0009", name="Software Engineering", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Ruby Singh", room="AB-VI Room 306", schedule="Mon 4:00 PM, Tue 2:00 PM, Thu 11:00 AM")
        c2 = Course(code="BCSC 1003", name="Database Management System", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Amit Kumar", room="AB-VI Room 306", schedule="Wed 1:00 PM, Thu 12:00 PM, Fri 11:00 AM")
        c3 = Course(code="BCSC 1006", name="Data Structure And Algorithms", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Vikas Kumar", room="AB-VI Room 306", schedule="Mon 5:00 PM, Tue 11:00 AM, Fri 12:00 PM")
        c4 = Course(code="BCSC 1802", name="Database Management Systems Lab", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Abhishek Sharma", room="AB-V Room 218C", schedule="Thu 4:00 PM - 6:00 PM")
        c5 = Course(code="BCSC 1805", name="Data Structure And Algorithms Lab", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Vikas Kumar", room="AB-VI Room 306", schedule="Tue 4:00 PM - 6:00 PM, Fri 2:00 PM - 4:00 PM")
        c6 = Course(code="BCSE 0031", name="Introduction To Frontend Engineering", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Shivam Kumar", room="AB-VI Room 306", schedule="Tue 10:00 AM, Wed 2:00 PM, Thu 3:00 PM")
        c7 = Course(code="BCSE 0813", name="Introduction To Frontend Engineering Lab", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Shivam Kumar", room="AB-VI Room 306", schedule="Mon 10:00 AM - 12:00 PM")
        c8 = Course(code="BELH 0020", name="English For Professional Purposes I", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Kiran Das", room="AB-VI Room 306", schedule="Mon 3:00 PM, Tue 3:00 PM, Wed 10:00 AM, Thu 10:00 AM")
        c9 = Course(code="BMAS 0108", name="Probability And Statistics", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Ankita Dubey", room="AB-VI Room 306", schedule="Mon 2:00 PM, Wed 11:00 AM, Thu 2:00 PM, Fri 10:00 AM")
        c10 = Course(code="BCSM 0001", name="Introduction To Cyber Security", section="2FE", semester=3, department="CSE", academic_year="2026-27", is_lateral=True, instructor="Shamsher Khan", room="AB-I Room 425", schedule="Thu 8:00 AM, Fri 8:00 AM")

        courses = [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10]
        db.session.add_all(courses)
        db.session.commit()

        # CR Assignment
        cr_assign = CRAssignment(user_id=aarav.id, course_id=c1.id, section="2FE", assigned_by_id=admin.id)
        db.session.add(cr_assign)
        db.session.commit()

        print("[*] Seeding Official 2FE Timetable Slots (Monday - Friday)...")
        # Monday
        slots = [
            TimetableSlot(course_id=c7.id, day_of_week="Monday", start_time="10:00 AM", end_time="11:00 AM", slot_type="Lab", building="AB-VI", room="306", faculty="Shivam Kumar", section="2FE"),
            TimetableSlot(course_id=c7.id, day_of_week="Monday", start_time="11:00 AM", end_time="12:00 PM", slot_type="Lab", building="AB-VI", room="306", faculty="Shivam Kumar", section="2FE"),
            TimetableSlot(course_id=c9.id, day_of_week="Monday", start_time="2:00 PM", end_time="3:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Ankita Dubey", section="2FE"),
            TimetableSlot(course_id=c8.id, day_of_week="Monday", start_time="3:00 PM", end_time="4:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Kiran Das", section="2FE"),
            TimetableSlot(course_id=c1.id, day_of_week="Monday", start_time="4:00 PM", end_time="5:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Ruby Singh", section="2FE"),
            TimetableSlot(course_id=c3.id, day_of_week="Monday", start_time="5:00 PM", end_time="6:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Vikas Kumar", section="2FE"),

            # Tuesday
            TimetableSlot(course_id=c6.id, day_of_week="Tuesday", start_time="10:00 AM", end_time="11:00 AM", slot_type="Lecture", building="AB-VI", room="306", faculty="Shivam Kumar", section="2FE"),
            TimetableSlot(course_id=c3.id, day_of_week="Tuesday", start_time="11:00 AM", end_time="12:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Vikas Kumar", section="2FE"),
            TimetableSlot(course_id=c1.id, day_of_week="Tuesday", start_time="2:00 PM", end_time="3:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Ruby Singh", section="2FE"),
            TimetableSlot(course_id=c8.id, day_of_week="Tuesday", start_time="3:00 PM", end_time="4:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Kiran Das", section="2FE"),
            TimetableSlot(course_id=c5.id, day_of_week="Tuesday", start_time="4:00 PM", end_time="5:00 PM", slot_type="Lab", building="AB-VI", room="306", faculty="Vikas Kumar", section="2FE"),
            TimetableSlot(course_id=c5.id, day_of_week="Tuesday", start_time="5:00 PM", end_time="6:00 PM", slot_type="Lab", building="AB-VI", room="306", faculty="Vikas Kumar", section="2FE"),

            # Wednesday
            TimetableSlot(course_id=c8.id, day_of_week="Wednesday", start_time="10:00 AM", end_time="11:00 AM", slot_type="Lecture", building="AB-VI", room="306", faculty="Kiran Das", section="2FE"),
            TimetableSlot(course_id=c9.id, day_of_week="Wednesday", start_time="11:00 AM", end_time="12:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Ankita Dubey", section="2FE"),
            TimetableSlot(course_id=c2.id, day_of_week="Wednesday", start_time="1:00 PM", end_time="2:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Amit Kumar", section="2FE"),
            TimetableSlot(course_id=c6.id, day_of_week="Wednesday", start_time="2:00 PM", end_time="3:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Shivam Kumar", section="2FE"),

            # Thursday
            TimetableSlot(course_id=c10.id, day_of_week="Thursday", start_time="8:00 AM", end_time="9:00 AM", slot_type="Lecture", building="AB-I", room="425", faculty="Shamsher Khan", section="2FE"),
            TimetableSlot(course_id=c8.id, day_of_week="Thursday", start_time="10:00 AM", end_time="11:00 AM", slot_type="Lecture", building="AB-VI", room="306", faculty="Kiran Das", section="2FE"),
            TimetableSlot(course_id=c1.id, day_of_week="Thursday", start_time="11:00 AM", end_time="12:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Ruby Singh", section="2FE"),
            TimetableSlot(course_id=c2.id, day_of_week="Thursday", start_time="12:00 PM", end_time="1:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Amit Kumar", section="2FE"),
            TimetableSlot(course_id=c9.id, day_of_week="Thursday", start_time="2:00 PM", end_time="3:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Ankita Dubey", section="2FE"),
            TimetableSlot(course_id=c6.id, day_of_week="Thursday", start_time="3:00 PM", end_time="4:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Shivam Kumar", section="2FE"),
            TimetableSlot(course_id=c4.id, day_of_week="Thursday", start_time="4:00 PM", end_time="5:00 PM", slot_type="Lab", building="AB-V", room="218C", faculty="Abhishek Sharma", section="2FE"),
            TimetableSlot(course_id=c4.id, day_of_week="Thursday", start_time="5:00 PM", end_time="6:00 PM", slot_type="Lab", building="AB-V", room="218C", faculty="Abhishek Sharma", section="2FE"),

            # Friday
            TimetableSlot(course_id=c10.id, day_of_week="Friday", start_time="8:00 AM", end_time="9:00 AM", slot_type="Lecture", building="AB-I", room="425", faculty="Shamsher Khan", section="2FE"),
            TimetableSlot(course_id=c9.id, day_of_week="Friday", start_time="10:00 AM", end_time="11:00 AM", slot_type="Lecture", building="AB-VI", room="306", faculty="Ankita Dubey", section="2FE"),
            TimetableSlot(course_id=c2.id, day_of_week="Friday", start_time="11:00 AM", end_time="12:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Amit Kumar", section="2FE"),
            TimetableSlot(course_id=c3.id, day_of_week="Friday", start_time="12:00 PM", end_time="1:00 PM", slot_type="Lecture", building="AB-VI", room="306", faculty="Vikas Kumar", section="2FE"),
            TimetableSlot(course_id=c5.id, day_of_week="Friday", start_time="2:00 PM", end_time="3:00 PM", slot_type="Lab", building="AB-VI", room="306", faculty="Vikas Kumar", section="2FE"),
            TimetableSlot(course_id=c5.id, day_of_week="Friday", start_time="3:00 PM", end_time="4:00 PM", slot_type="Lab", building="AB-VI", room="306", faculty="Vikas Kumar", section="2FE")
        ]
        db.session.add_all(slots)
        db.session.commit()

        print("[*] Seeding Realistic 2FE Catch-up Lecture Summaries...")
        today = date.today()
        yesterday = today - timedelta(days=1)

        summaries = [
            Summary(
                course_id=c3.id,
                user_id=aarav.id,
                date=today,
                topic="Red-Black Trees Insertion & Color Invariants",
                category="Lecture Notes",
                content="Prof. Vikas Kumar covered Red-Black Tree rotation cases today.\nKey Takeaways:\n1. Root is always black.\n2. No two consecutive red nodes (Red property).\n3. Every simple path from a node to descendant leaves contains the same number of black nodes.\nHomework: Exercise 13.3 from Cormen (Cases 1, 2, and 3).",
                helpful_count=18,
                is_verified=True,
                verified_by="Aarav Patel (CR)"
            ),
            Summary(
                course_id=c2.id,
                user_id=priya.id,
                date=today,
                topic="BCNF vs 3NF Decomposition & Lossless Join Tests",
                category="Lecture Notes",
                content="Dr. Amit Kumar discussed Boyec-Codd Normal Form decomposition algorithms.\nKey points:\n- Tested functional dependencies using closure attribute algorithm.\n- Covered dependency preservation tradeoff between 3NF and BCNF.\nMidterm alert: Questions from normalization algorithm will be on the 25-mark quiz.",
                helpful_count=14,
                is_verified=True,
                verified_by="Aarav Patel (CR)"
            ),
            Summary(
                course_id=c1.id,
                user_id=rohit.id,
                date=yesterday,
                topic="Agile Scrum Framework & User Story Estimation",
                category="Assignment",
                content="Ruby Singh reviewed Sprint backlog planning and Planning Poker estimation technique.\nAssignment Assigned: In your 4-member teams, prepare the Sprint Backlog for Project Milestone 1 in Jira or Markdown by Friday 5 PM.",
                helpful_count=9,
                is_verified=False
            ),
            Summary(
                course_id=c9.id,
                user_id=ananya.id,
                date=yesterday,
                topic="Poisson Distribution & Central Limit Theorem Proofs",
                category="Exam Prep",
                content="Prof. Ankita Dubey solved 4 PYQ problems on Poisson approximations.\nFormula sheet notes uploaded in Academic Vault. Focus on λ = np derivations.",
                helpful_count=12,
                is_verified=True,
                verified_by="Aarav Patel (CR)"
            )
        ]
        db.session.add_all(summaries)
        db.session.commit()

        print("[*] Seeding Official Announcements for Section 2FE...")
        announcements = [
            Announcement(
                course_id=c1.id,
                user_id=admin.id,
                title="📢 2FE Software Engineering Sprint 1 Submission Guidelines",
                content="All Section 2FE teams must submit their Milestone 1 SRS document by Friday 5:00 PM via ClassCatch Academic Vault.",
                target_scope="section",
                target_section="2FE",
                is_pinned=True
            ),
            Announcement(
                course_id=c4.id,
                user_id=admin.id,
                title="🏢 DBMS Lab Room Change: Thursday Slot in AB-V Room 218C",
                content="Please note that DBMS Lab (BCSC 1802) will take place in Block AB-V Computer Lab 218C as scheduled.",
                target_scope="section",
                target_section="2FE",
                is_pinned=True
            ),
            Announcement(
                user_id=admin.id,
                title="🎓 GLA University: Midterm Examination Schedule 2026-27",
                content="The 3rd Semester Mid-Term evaluations commence next month. Ensure your attendance meets the 75% institutional threshold.",
                target_scope="college",
                target_section="ALL",
                is_pinned=False
            )
        ]
        db.session.add_all(announcements)
        db.session.commit()

        print("[*] Seeding Academic Deadlines & Exam Calendar...")
        deadlines = [
            Deadline(
                course_id=c1.id,
                user_id=aarav.id,
                title="Software Engineering Milestone 1 SRS",
                due_date=today + timedelta(days=5),
                category="Assignment",
                priority=3,
                description="Team submission of IEEE 830 compliant SRS document.",
                is_official=True
            ),
            Deadline(
                course_id=c3.id,
                user_id=aarav.id,
                title="DSA Lab Problem Set 3 (Trees & Graphs)",
                due_date=today + timedelta(days=3),
                category="Lab Submission",
                priority=2,
                description="Submit verified LeetCode solution links on portal.",
                is_official=True
            ),
            Deadline(
                course_id=c9.id,
                user_id=admin.id,
                title="Probability & Statistics Midterm Quiz",
                due_date=today + timedelta(days=10),
                category="Midterm Exam",
                priority=3,
                description="25 Marks written quiz on Units 1 and 2.",
                is_official=True
            )
        ]
        db.session.add_all(deadlines)
        db.session.commit()

        print("[*] Seeding Student Attendance Records (75% Threshold Calculations)...")
        # Aarav has safe attendance (87.5%)
        att1 = AttendanceRecord(user_id=aarav.id, course_id=c3.id, total_classes=32, attended_classes=28, target_percentage=75.0)
        att2 = AttendanceRecord(user_id=aarav.id, course_id=c2.id, total_classes=30, attended_classes=27, target_percentage=75.0)
        # Priya has high attendance
        att3 = AttendanceRecord(user_id=priya.id, course_id=c1.id, total_classes=25, attended_classes=24, target_percentage=75.0)
        # Rohit is at risk (66.7%, needs recovery)
        att4 = AttendanceRecord(user_id=rohit.id, course_id=c3.id, total_classes=30, attended_classes=20, target_percentage=75.0)
        db.session.add_all([att1, att2, att3, att4])
        db.session.commit()

        print("[*] Seeding Academic Vault Resources (PYQs & Notes)...")
        res1 = Resource(
            course_id=c3.id,
            user_id=aarav.id,
            title="DSA End-Sem Question Papers (2023 - 2025 Solved)",
            category="PYQ & Solutions",
            resource_url="https://drive.google.com/open?id=demo_gla_dsa_pyq",
            description="Handwritten solutions for binary search tree and dynamic programming questions from previous university examinations.",
            downloads=45,
            helpful_count=23,
            status="Approved",
            is_featured=True
        )
        res2 = Resource(
            course_id=c2.id,
            user_id=priya.id,
            title="DBMS Quick Revision Formula Sheet & Normalization Cheat Sheet",
            category="Formula Sheet",
            resource_url="https://drive.google.com/open?id=demo_gla_dbms_cheatsheet",
            description="All relational algebra symbols, SQL query syntax, and normal form conditions summarized on 4 pages.",
            downloads=38,
            helpful_count=19,
            status="Approved",
            is_featured=True
        )
        res3 = Resource(
            course_id=c9.id,
            user_id=ananya.id,
            title="Probability & Statistics Comprehensive Class Notes (Units 1-3)",
            category="Handwritten Notes",
            resource_url="https://drive.google.com/open?id=demo_gla_stats_notes",
            description="Complete lecture notes with worked examples from Dr. Ankita Dubey's classes.",
            downloads=29,
            helpful_count=15,
            status="Approved",
            is_featured=False
        )
        db.session.add_all([res1, res2, res3])
        db.session.commit()

        print("\n========================================================")
        print("[+] GLA UNIVERSITY 2FE PILOT DATABASE SUCCESSFULLY SEEDED!")
        print("========================================================")
        print("College: GLA University, Mathura Campus")
        print("Department: Computer Science & Engineering (CSE)")
        print("Section: 2FE (Lateral Entry, 3rd Semester, 2026-27)")
        print(f"Courses Seeded: {len(courses)}")
        print(f"Timetable Slots: {len(slots)}")
        print(f"Leadership Records: {len(staff_records)}")
        print(f"Approved Roster Entries: {len(roster_entries)}")
        print("--------------------------------------------------------")
        print("Demo Accounts:")
        print("  SuperAdmin: superadmin@classcatch.edu (password123)")
        print("  Admin:      admin@classcatch.edu      (password123)")
        print("  CR Student: aarav.patel@gla.ac.in     (password123)")
        print("  Student:    priya.singh@gla.ac.in     (password123)")
        print("  Student:    rohit.verma@gla.ac.in     (password123)")
        print("========================================================\n")

if __name__ == '__main__':
    seed_database()
