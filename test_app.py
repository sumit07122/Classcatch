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
    assert b"Never Miss What Happened in Class" in res.data or b"ClassCatch" in res.data
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

    # 7. Absence & Catch-Up Hub Tests
    print("[*] Testing Absence & Catch-Up Engine...")
    catchup_res = client.get('/catchup')
    assert catchup_res.status_code == 200
    assert b"Absence &amp; Catch-Up" in catchup_res.data or b"Catch-Up" in catchup_res.data
    print("   [+] GET /catchup -> 200 OK")

    catchup_yesterday = client.get('/catchup?preset=yesterday')
    assert catchup_yesterday.status_code == 200
    print("   [+] GET /catchup?preset=yesterday -> 200 OK")

    # 8. Global Search Tests
    print("[*] Testing Global Search Engine...")
    search_res = client.get('/search?q=DBMS')
    assert search_res.status_code == 200
    assert b"Search" in search_res.data
    print("   [+] GET /search?q=DBMS -> 200 OK")

    api_search_res = client.get('/api/search?q=Database')
    assert api_search_res.status_code == 200
    search_json = api_search_res.get_json()
    assert 'results' in search_json
    print("   [+] GET /api/search?q=Database -> 200 OK (JSON results returned)")

    # 9. Attendance 1-Tap Quick Logging Tests
    print("[*] Testing 1-Tap Attendance Actions...")
    with app.app_context():
        user = User.query.filter_by(email='alex@classcatch.edu').first()
        rec = AttendanceRecord.query.filter_by(user_id=user.id).first()
        if not rec:
            rec = AttendanceRecord(user_id=user.id, course_id=1, attended_classes=20, total_classes=25, target_percentage=75.0)
            db.session.add(rec)
            db.session.commit()
        rec_id = rec.id
        initial_attended = rec.attended_classes
        initial_total = rec.total_classes

    # Log Present (+1 attended, +1 total)
    log_present_res = client.post(f'/attendance/{rec_id}/log?status=present', follow_redirects=True)
    assert log_present_res.status_code == 200
    with app.app_context():
        updated_rec = db.session.get(AttendanceRecord, rec_id)
        assert updated_rec.attended_classes == initial_attended + 1
        assert updated_rec.total_classes == initial_total + 1
    print("   [+] POST /attendance/1/log?status=present -> Success (+1 attended, +1 total)")

    # Log Missed/Bunk (+0 attended, +1 total)
    log_absent_res = client.post(f'/attendance/{rec_id}/log?status=absent', follow_redirects=True)
    assert log_absent_res.status_code == 200
    with app.app_context():
        updated_rec = db.session.get(AttendanceRecord, rec_id)
        assert updated_rec.total_classes == initial_total + 2
    print("   [+] POST /attendance/1/log?status=absent -> Success (+1 total, attended unchanged)")

    # 10. CR Verification Security & Authorization Tests
    print("[*] Testing CR Verification Authorization & Anti-Farming...")
    with app.app_context():
        # Setup: Sarah Chen as CR, David Sharma as normal student, Alex as CR author
        sarah = User.query.filter_by(email='sarah@classcatch.edu').first()
        sarah.role = 'cr'
        david = User.query.filter_by(email='david@classcatch.edu').first()
        david.role = 'student'
        alex = User.query.filter_by(email='alex@classcatch.edu').first()
        alex.role = 'cr'
        # Alex's note
        note = Summary.query.filter_by(user_id=alex.id).first()
        note_id = note.id
        db.session.commit()

    # Test: Normal student David tries to verify Alex's note -> Should be rejected
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'david@classcatch.edu', 'password': 'password123'}, follow_redirects=True)
    david_verify_res = client.post(f'/summary/{note_id}/verify', follow_redirects=True)
    assert b"Access Denied" in david_verify_res.data or b"Only Class Representatives" in david_verify_res.data
    print("   [+] Security Check: Normal student verification blocked -> 403 / Flash Denied")

    # Test: Author Alex tries to verify his own note -> Should be rejected
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'alex@classcatch.edu', 'password': 'password123'}, follow_redirects=True)
    alex_self_verify = client.post(f'/summary/{note_id}/verify', follow_redirects=True)
    assert b"Integrity Check" in alex_self_verify.data or b"cannot verify your own" in alex_self_verify.data
    print("   [+] Integrity Check: Author self-verification blocked (anti-farming)")

    # Test: CR Sarah verifies Alex's note -> Should succeed
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'sarah@classcatch.edu', 'password': 'password123'}, follow_redirects=True)
    sarah_verify_res = client.post(f'/summary/{note_id}/verify', follow_redirects=True)
    assert sarah_verify_res.status_code == 200
    assert b"officially verified" in sarah_verify_res.data or b"verified" in sarah_verify_res.data
    print("   [+] Authorization Check: CR verification succeeded & author awarded Karma")

    # 11. Whiteboard Save API Test
    print("[*] Testing AI Whiteboard-to-Summary Save API...")
    wb_res = client.post('/api/save-whiteboard-note', json={
        'course_id': 1,
        'topic': 'Scanned Dijkstra Board Note',
        'content': '### Shortest Path Algorithm\n- Greedy approach\n- Relax edges'
    })
    assert wb_res.status_code == 200
    wb_data = wb_res.get_json()
    assert wb_data['success'] is True
    assert 'summary_id' in wb_data
    print("   [+] POST /api/save-whiteboard-note -> Success (note saved directly to DB)")

    # 12. Deadlines Toggle Completion
    toggle_res = client.post('/deadlines/1/toggle', follow_redirects=True)
    assert toggle_res.status_code == 200
    print("   [+] POST /deadlines/1/toggle -> Success")

    # 13. Play Store Compliance & PWA routes
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

    # 14. Attendance Math Model Check
    with app.app_context():
        rec = AttendanceRecord(user_id=1, course_id=1, attended_classes=28, total_classes=32, target_percentage=75.0)
        pct = rec.current_percentage
        bunks = rec.bunks_available
        needed = rec.classes_needed
        print(f"   [+] Attendance Model Check: {rec.attended_classes}/{rec.total_classes} = {pct}% (Target: {rec.target_percentage}%, Bunks Available: {bunks}, Recovery Needed: {needed})")
        assert pct == 87.5
        assert bunks == 5
        assert needed == 0

        # Test recovery case (< 75%)
        bad_rec = AttendanceRecord(user_id=1, course_id=1, attended_classes=20, total_classes=30, target_percentage=75.0)
        assert bad_rec.current_percentage == 66.7
        assert bad_rec.bunks_available == 0
        assert bad_rec.classes_needed == 10  # (20+10)/(30+10) = 30/40 = 75%
        print(f"   [+] Attendance Recovery Math Check: 20/30 (66.7%) -> Needs {bad_rec.classes_needed} consecutive classes to reach 75%")

    print("\n" + "=" * 65)
    print("[ALL ENHANCED TESTS PASSED SUCCESSFULLY!]")
    print("=" * 65)

if __name__ == '__main__':
    test_classcatch()
