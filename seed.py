"""
ClassCatch Database Seeding Script
===================================
Pre-populates the database with:
- Standard Computer Science courses (timings, instructors, room numbers, status)
- Demo student accounts
- Realistic lecture catch-up notes (assignments, topics, announcements)
- Unofficial class chat discussions and peer requirements
- Campus announcements
- Sample student attendance records

Usage:
    python seed.py
"""

from datetime import date, timedelta
from app import app
from models import db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord

def seed_database():
    with app.app_context():
        print("[*] Rebuilding database schema...")
        db.drop_all()
        db.create_all()

        print("[*] Creating demo student accounts...")
        # Demo Students
        alex = User(name="Alex Rivera", email="alex@classcatch.edu", role="student")
        alex.set_password("password123")

        sarah = User(name="Sarah Chen", email="sarah@classcatch.edu", role="student")
        sarah.set_password("password123")

        david = User(name="David Sharma", email="david@classcatch.edu", role="student")
        david.set_password("password123")

        db.session.add_all([alex, sarah, david])
        db.session.commit()

        print("[*] Creating college courses...")
        # Core Courses
        dbms = Course(
            name="Database Management Systems",
            code="CSE-301",
            section="A",
            semester=5,
            instructor="Dr. R. Sharma",
            room="Room 304 (Block B)",
            schedule="Mon, Wed, Fri (10:00 AM - 11:00 AM)",
            status="Scheduled"
        )
        os_course = Course(
            name="Operating Systems",
            code="CSE-302",
            section="A",
            semester=5,
            instructor="Prof. Anjali Verma",
            room="Lecture Theater 2",
            schedule="Tue, Thu (11:30 AM - 1:00 PM)",
            status="Scheduled"
        )
        dsa = Course(
            name="Data Structures & Algorithms",
            code="CSE-201",
            section="B",
            semester=3,
            instructor="Dr. Vikram Patel",
            room="Computer Lab 1",
            schedule="Mon, Wed (02:00 PM - 03:30 PM)",
            status="Scheduled"
        )
        networks = Course(
            name="Computer Networks",
            code="CSE-303",
            section="A",
            semester=5,
            instructor="Prof. Sneha Kulkarni",
            room="Room 201 (Block A)",
            schedule="Tue, Fri (09:00 AM - 10:30 AM)",
            status="Scheduled"
        )
        se = Course(
            name="Software Engineering",
            code="CSE-401",
            section="C",
            semester=7,
            instructor="Dr. Arvind Gupta",
            room="Seminar Hall 3",
            schedule="Thu, Fri (03:30 PM - 05:00 PM)",
            status="Scheduled"
        )

        db.session.add_all([dbms, os_course, dsa, networks, se])
        db.session.commit()

        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        print("[*] Seeding class catch-up summaries...")
        summaries = [
            # DBMS Summaries
            Summary(
                course_id=dbms.id,
                user_id=sarah.id,
                date=today,
                topic="B+ Tree Indexing vs Hash Indexing",
                category="Lecture Notes",
                helpful_count=5,
                content=(
                    "1. Lecture Topics: Discussed B+ tree internal vs leaf nodes, search complexity O(log N), "
                    "and why B+ trees are ideal for range queries compared to hash indexes.\n\n"
                    "2. Homework / Assignment: Exercise questions 11.4 and 11.6 from the Ramakrishnan textbook. "
                    "Submission deadline is next Monday at 11:59 PM on Google Classroom.\n\n"
                    "3. Notice: Lab 4 on Tuesday will be an evaluated practical exam on SQL triggers."
                )
            ),
            Summary(
                course_id=dbms.id,
                user_id=david.id,
                date=two_days_ago,
                topic="Relational Calculus & Tuple Calculus",
                category="Exam Prep",
                helpful_count=3,
                content=(
                    "1. Topics Covered: Tuple Relational Calculus (TRC) safe expressions and Domain Relational Calculus (DRC).\n\n"
                    "2. Practice Problems: Solved 3 query translations from English to TRC.\n\n"
                    "3. Important: Prof. Sharma mentioned these queries will definitely appear in Midterm 1!"
                )
            ),
            # OS Summaries
            Summary(
                course_id=os_course.id,
                user_id=alex.id,
                date=today,
                topic="Deadlock Avoidance & Banker's Algorithm",
                category="Lecture Notes",
                helpful_count=8,
                content=(
                    "1. Topics Covered: Safe state vs Unsafe state, Resource Allocation Graph, Banker's Safety "
                    "Algorithm and Resource Request Algorithm.\n\n"
                    "2. Assignment: Complete the 5-process allocation matrix handout by this Friday.\n\n"
                    "3. Announcement: Extra class scheduled next Wednesday for CPU scheduling doubts."
                )
            ),
            # DSA Summaries
            Summary(
                course_id=dsa.id,
                user_id=sarah.id,
                date=yesterday,
                topic="Dijkstra's Algorithm & Priority Queues",
                category="Lecture Notes",
                helpful_count=6,
                content=(
                    "1. Topics Covered: Greedy approach for single source shortest path. Proved why Dijkstra fails "
                    "with negative edge weights.\n\n"
                    "2. Lab Assignment: Implement Dijkstra using Min-Heap / std::priority_queue in C++ or Python.\n\n"
                    "3. Homework: Time complexity analysis proof."
                )
            )
        ]
        db.session.add_all(summaries)

        print("[*] Seeding unofficial class chat discussions...")
        chats = [
            ChatMessage(
                course_id=dbms.id,
                user_id=alex.id,
                category="Notes Request",
                message="Hey everyone, did anyone note down the example query Prof wrote on the whiteboard near the end of class?"
            ),
            ChatMessage(
                course_id=dbms.id,
                user_id=sarah.id,
                category="General",
                message="Yes! It was: SELECT S.sname FROM Sailors S WHERE NOT EXISTS (SELECT B.bid FROM Boats B EXCEPT SELECT R.bid FROM Reserves R WHERE R.sid = S.sid)"
            ),
            ChatMessage(
                course_id=dbms.id,
                user_id=david.id,
                category="Requirement",
                message="Looking for 1 more teammate for the semester DBMS project. Working on a hospital management portal using Flask + Postgres. DM me!"
            ),
            ChatMessage(
                course_id=os_course.id,
                user_id=david.id,
                category="Doubt",
                message="In Banker's algorithm, if Request_i <= Need_i holds but Request_i > Available, do we put the process in wait immediately?"
            ),
            ChatMessage(
                course_id=os_course.id,
                user_id=alex.id,
                category="General",
                message="Yes, process P_i must wait until resources become available."
            ),
            # Campus Lounge general chat
            ChatMessage(
                course_id=None,
                user_id=sarah.id,
                category="Requirement",
                message="Does anyone from 3rd or 4th year have the previous year mid-term question paper for Computer Networks (CSE-303)?"
            ),
            ChatMessage(
                course_id=None,
                user_id=david.id,
                category="General",
                message="Check out the campus library drive or the ClassCatch summaries tab for networks, someone uploaded the topic checklist!"
            )
        ]
        db.session.add_all(chats)

        print("[*] Seeding class announcements...")
        announcements = [
            Announcement(
                course_id=dbms.id,
                user_id=sarah.id,
                title="Midterm 1 Examination Date Finalized",
                tag="Exam",
                content="Midterm 1 will be held on September 22, 2026 from 10:00 AM to 11:30 AM in Room 304. Syllabus: Modules 1, 2, and 3."
            ),
            Announcement(
                course_id=dbms.id,
                user_id=alex.id,
                title="Lab 4 Shifted to Computer Lab 3",
                tag="Room Change",
                content="Due to maintenance in Lab 1, tomorrow's DBMS lab session will take place in Computer Lab 3 (Block C)."
            ),
            Announcement(
                course_id=os_course.id,
                user_id=david.id,
                title="Assignment #2 Submission Deadline Extended",
                tag="Assignment",
                content="Prof. Verma has extended the deadline for the Process Synchronization assignment by 48 hours until Sunday midnight."
            )
        ]
        db.session.add_all(announcements)

        print("[*] Seeding sample student attendance records...")
        attendances = [
            AttendanceRecord(
                user_id=alex.id,
                course_id=dbms.id,
                total_classes=32,
                attended_classes=28,
                target_percentage=75.0
            ),
            AttendanceRecord(
                user_id=alex.id,
                course_id=os_course.id,
                total_classes=30,
                attended_classes=22,
                target_percentage=75.0
            ),
            AttendanceRecord(
                user_id=alex.id,
                course_id=dsa.id,
                total_classes=28,
                attended_classes=25,
                target_percentage=75.0
            )
        ]
        db.session.add_all(attendances)

        db.session.commit()
        print("[OK] Database successfully seeded with rich mock data!")
        print("\n[INFO] Demo Logins:")
        print("   Email: alex@classcatch.edu    Password: password123")
        print("   Email: sarah@classcatch.edu   Password: password123")
        print("   Email: david@classcatch.edu   Password: password123")

if __name__ == '__main__':
    seed_database()
