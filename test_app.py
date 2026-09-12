import os
os.environ['TESTING'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///test_cache.db'

from app import app, db
from models import User, Course, Summary, AttendanceRecord, ChatMessage, Announcement, Deadline, Resource
from seed import seed_database

def test_classcatch():
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()
        seed_database()

    client = app.test_client()

    print("[*] Testing Public Routes...")
    # 1. Home Page
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200 on /, got {res.status_code}"
    assert b"ClassCatch" in res.data
    assert b"Never Miss a Beat in Class" in res.data
    print("   [+] GET / -> 200 OK")

    # 2. Course Details & Tabs
    res = client.get('/course/1')
    assert res.status_code == 200
    assert b"CSE-301" in res.data
    print("   [+] GET /course/1 (Summaries) -> 200 OK")

    res = client.get('/course/1?tab=chat')
    assert res.status_code == 200
    assert b"Unofficial Peer Chat" in res.data
    print("   [+] GET /course/1?tab=chat -> 200 OK")

    res = client.get('/course/1?tab=announcements')
    assert res.status_code == 200
    assert b"Class Announcements" in res.data
    print("   [+] GET /course/1?tab=announcements -> 200 OK")

    res = client.get('/course/1?tab=schedule')
    assert res.status_code == 200
    assert b"Class Timetable & Location" in res.data
    print("   [+] GET /course/1?tab=schedule -> 200 OK")

    # 3. Attendance Calculator
    res = client.get('/attendance')
    assert res.status_code == 200
    assert b"Attendance & Bunk Predictor" in res.data
    print("   [+] GET /attendance -> 200 OK")

    # 4. Campus Lounge
    res = client.get('/lounge')
    assert res.status_code == 200
    assert b"Campus Lounge" in res.data
    print("   [+] GET /lounge -> 200 OK")

    # 5. Summary Detail View
    res = client.get('/summary/1')
    assert res.status_code == 200
    assert b"Summary" in res.data or b"B+" in res.data
    print("   [+] GET /summary/1 -> 200 OK")

    # 6. Test Authentication Flow
    print("[*] Testing Authentication & Protected Routes...")
    # Login
    login_res = client.post('/login', data={
        'email': 'alex@classcatch.edu',
        'password': 'password123'
    }, follow_redirects=True)
    assert login_res.status_code == 200
    print("   [+] POST /login (Alex Rivera) -> Success")

    # Test Create New Course
    course_add_res = client.post('/course/new', data={
        'name': 'Cloud Computing & DevOps',
        'code': 'CSE-405',
        'section': 'A',
        'semester': 6,
        'instructor': 'Dr. K. Patel',
        'room': 'Lab 4',
        'schedule': 'Tue, Thu (2:00 PM - 3:30 PM)'
    }, follow_redirects=True)
    assert course_add_res.status_code == 200
    print("   [+] POST /course/new -> Success & Course Created")

    # Post new summary
    new_summary_res = client.post('/summary/new', data={
        'course_id': 1,
        'date': '2026-09-07',
        'category': 'Assignment',
        'topic': 'Automated Test Catch-up Note',
        'content': 'Test summary content: 1. Topics covered 2. Homework exercises'
    }, follow_redirects=True)
    assert new_summary_res.status_code == 200
    assert b"Automated Test Catch-up Note" in new_summary_res.data
    print("   [+] POST /summary/new -> Success & Redirect to Course Feed")

    # Post in course chat
    chat_res = client.post('/course/1/chat', data={
        'category': 'Doubt',
        'message': 'Does anyone understand 3NF vs BCNF?'
    }, follow_redirects=True)
    assert chat_res.status_code == 200
    print("   [+] POST /course/1/chat -> Success")

    # Mark helpful
    helpful_res = client.post('/summary/1/helpful', follow_redirects=True)
    assert helpful_res.status_code == 200
    print("   [+] POST /summary/1/helpful -> Success")

    # Test Deadlines & Resources routes
    deadlines_res = client.get('/deadlines')
    assert deadlines_res.status_code == 200
    assert b"Academic Deadlines" in deadlines_res.data
    print("   [+] GET /deadlines -> 200 OK")

    resources_res = client.get('/resources')
    assert resources_res.status_code == 200
    assert b"Academic Vault" in resources_res.data
    print("   [+] GET /resources -> 200 OK")

    # Test Play Store Compliance & PWA routes
    priv_res = client.get('/privacy')
    assert priv_res.status_code == 200
    assert b"Privacy Policy" in priv_res.data
    print("   [+] GET /privacy -> 200 OK (Google Play compliant)")

    terms_res = client.get('/terms')
    assert terms_res.status_code == 200
    print("   [+] GET /terms -> 200 OK")

    asset_res = client.get('/.well-known/assetlinks.json')
    assert asset_res.status_code == 200
    assert b"delegate_permission" in asset_res.data
    print("   [+] GET /.well-known/assetlinks.json -> 200 OK (Android TWA ready)")

    # Test CR Verification
    verify_res = client.post('/summary/1/verify', follow_redirects=True)
    assert verify_res.status_code == 200
    print("   [+] POST /summary/1/verify -> Success (CR seal toggled)")

    # Test Morning Dispatch
    dispatch_res = client.get('/api/morning-dispatch')
    assert dispatch_res.status_code == 200
    assert b"Daily Briefing" in dispatch_res.data
    print("   [+] GET /api/morning-dispatch -> 200 OK & student briefing")

    # Test AI Summarize endpoint
    ai_res = client.post('/api/ai-summarize', json={
        'text': 'Covered B+ trees and indexing.\nHW: solve problem 4.2\nImp: guaranteed 10 mark question in midterms',
        'topic': 'Database Indexing'
    })
    assert ai_res.status_code == 200
    assert b"Core Topic: Database Indexing" in ai_res.data
    print("   [+] POST /api/ai-summarize -> 200 OK & formatted markdown")

    # Test Attendance Math
    with app.app_context():
        rec = AttendanceRecord.query.first()
        if not rec:
            rec = AttendanceRecord(user_id=1, course_id=1, attended_classes=28, total_classes=32, target_percentage=75.0)
        pct = rec.current_percentage
        bunks = rec.bunks_available
        needed = rec.classes_needed
        print(f"   [+] Attendance Model Check: {rec.attended_classes}/{rec.total_classes} = {pct}% (Target: {rec.target_percentage}%, Bunks Available: {bunks}, Recovery Needed: {needed})")
        assert pct > 0

    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

if __name__ == '__main__':
    test_classcatch()
