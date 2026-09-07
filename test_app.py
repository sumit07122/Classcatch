from app import app, db
from models import User, Course, Summary, AttendanceRecord, ChatMessage, Announcement

def test_classcatch():
    client = app.test_client()
    app.config['WTF_CSRF_ENABLED'] = False  # disable CSRF for automated test client

    print("[*] Testing Public Routes...")
    # 1. Home Page
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200 on /, got {res.status_code}"
    assert b"ClassCatch" in res.data
    assert b"College Class Catch-up Notes" in res.data
    print("   [+] GET / -> 200 OK")

    # 2. Course Details
    res = client.get('/course/1')
    assert res.status_code == 200
    assert b"CSE-301" in res.data
    assert b"Class Doubts & Questions" in res.data
    print("   [+] GET /course/1 -> 200 OK")

    # 3. Attendance Calculator
    res = client.get('/attendance')
    assert res.status_code == 200
    assert b"Attendance Calculator" in res.data
    print("   [+] GET /attendance -> 200 OK")

    # 4. Campus Lounge
    res = client.get('/lounge')
    assert res.status_code == 200
    assert b"Campus Lounge" in res.data
    print("   [+] GET /lounge -> 200 OK")

    # 5. Summary Detail View
    res = client.get('/summary/1')
    assert res.status_code == 200
    assert b"B+ Tree Indexing vs Hash Indexing" in res.data
    print("   [+] GET /summary/1 -> 200 OK")

    # 6. Test Authentication Flow
    print("[*] Testing Authentication & Protected Routes...")
    # Login
    login_res = client.post('/login', data={
        'email': 'alex@classcatch.edu',
        'password': 'password123'
    }, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Welcome back, Alex Rivera" in login_res.data
    print("   [+] POST /login (Alex Rivera) -> Success")

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

    # Test Attendance Math
    with app.app_context():
        rec = AttendanceRecord.query.first()
        pct = rec.current_percentage
        bunks = rec.bunks_available
        needed = rec.classes_needed
        print(f"   [+] Attendance Model Check: {rec.attended_classes}/{rec.total_classes} = {pct}% (Target: {rec.target_percentage}%, Bunks Available: {bunks}, Recovery Needed: {needed})")
        assert pct > 0

    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

if __name__ == '__main__':
    test_classcatch()
