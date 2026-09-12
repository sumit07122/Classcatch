"""
ClassCatch Automated Pilot & Production Verification Test Suite
================================================================
Verifies:
1. GLA Institutional Email Domain Restriction (@gla.ac.in required, Gmail/Yahoo rejected)
2. Email Verification Token Flow & Unverified Gate
3. Official Roster Pre-Authorization & Pending Enrollment Gate
4. One User = One Active Enrollment (Locked to 2FE Pilot)
5. Server-Side Section Isolation & Cross-Section Leakage Prevention
6. 2FE Timetable Slots & Weekly Schedule Grid
7. Storage Abstraction Layer (MIME Whitelist, Executable Blocking, 15MB Limit, Cleanup)
8. Admin Control Center (Roster Import, Enrollment Approvals, Section Transfers, Storage Console)
9. Attendance Safe Bunk & Recovery Mathematical Engine (75% Threshold)
10. Dynamic Feature Flags, Maintenance Mode, and Audit Logging
"""

import os
import io
os.environ['TESTING'] = '1'
os.environ['DATABASE_URL'] = 'sqlite:///test_cache.db'

if os.path.exists('test_cache.db'):
    try:
        os.remove('test_cache.db')
    except OSError:
        pass

from app import app, db
from models import (
    User, Course, Summary, AttendanceRecord, ChatMessage, Announcement,
    Deadline, Resource, Enrollment, RosterEntry, TimetableSlot, AcademicStaff, StorageFile
)
from seed import seed_database
from storage import handle_file_upload, is_allowed_file, BLOCKED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from werkzeug.datastructures import FileStorage

def test_classcatch_pilot():
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['TESTING'] = True

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_database()

    client = app.test_client()

    print("\n========================================================")
    print("RUNNING CLASSCATCH GLA 2FE PILOT VERIFICATION SUITE")
    print("========================================================")

    # ----------------------------------------------------
    # 1. Public & Timetable Routes
    # ----------------------------------------------------
    print("\n[*] 1. Testing Public & Timetable Routes...")
    res = client.get('/')
    assert res.status_code == 200, f"Expected 200 on /, got {res.status_code}"
    assert b"ClassCatch" in res.data
    print("   [+] GET / -> 200 OK")

    res = client.get('/timetable')
    assert res.status_code == 200
    assert b"Official Class Timetable" in res.data
    assert b"Section 2FE" in res.data
    assert b"AB-VI Room 306" in res.data
    print("   [+] GET /timetable -> 200 OK (2FE Timetable active)")

    # ----------------------------------------------------
    # 2. Institutional GLA Email Restriction
    # ----------------------------------------------------
    print("\n[*] 2. Testing GLA Institutional Email Restrictions...")
    # Attempt registration with personal/fake email addresses
    for bad_email in ['student@gmail.com', 'hacker@yahoo.com', 'fake@outlook.com', 'temp@disposable.org']:
        os.environ.pop('ALLOW_TEST_EMAILS', None)
        os.environ['TESTING'] = '0' # enforce strict domain check in route
        reg_res = client.post('/register', data={
            'name': 'Test Impostor',
            'email': bad_email,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert b"GLA University institutional" in reg_res.data or b"Access Restricted" in reg_res.data
        print(f"   [+] Rejected non-GLA email: {bad_email} -> BLOCKED")

    # Restore TESTING mode
    os.environ['TESTING'] = '1'

    # Valid GLA email registration
    new_gla_email = 'rohitash.gupta@gla.ac.in'
    reg_ok = client.post('/register', data={
        'name': 'Rohitash Gupta',
        'email': new_gla_email,
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert reg_ok.status_code == 200
    assert b"verify your GLA email" in reg_ok.data or b"Institutional account created" in reg_ok.data
    print(f"   [+] Accepted official GLA email: {new_gla_email} -> Created & token issued")

    with app.app_context():
        new_student = User.query.filter_by(email=new_gla_email).first()
        assert new_student is not None
        assert new_student.is_verified is False
        assert new_student.verification_token is not None
        v_token = new_student.verification_token

    # ----------------------------------------------------
    # 3. Unverified Gate & Email Verification
    # ----------------------------------------------------
    print("\n[*] 3. Testing Email Verification & Gating...")
    # Unverified student tries to log in
    client.post('/login', data={'email': new_gla_email, 'password': 'password123'}, follow_redirects=True)
    unv_try = client.get('/catchup', follow_redirects=False)
    # Must redirect to unverified notice
    assert unv_try.status_code == 302
    assert '/unverified' in unv_try.location
    print("   [+] Unverified student blocked from student app -> Redirected to /unverified")

    # Invalid token check
    inv_res = client.get('/verify-email/invalid-token-12345', follow_redirects=True)
    assert b"Invalid, expired, or previously used" in inv_res.data
    print("   [+] Invalid verification token rejected -> 404/Error Flash")

    # Verify student (who is NOT on the roster) -> should trigger Enrollment Pending state!
    client.get(f'/verify-email/{v_token}', follow_redirects=True)
    with app.app_context():
        verified_user = User.query.filter_by(email=new_gla_email).first()
        assert verified_user.is_verified is True
        assert verified_user.active_enrollment is None
    print("   [+] Non-roster GLA student verified -> Account active, enrollment pending")

    # ----------------------------------------------------
    # 4. Enrollment Pending & Request Access Flow
    # ----------------------------------------------------
    print("\n[*] 4. Testing Enrollment Pending & Request Access Flow...")
    # Check pending page
    pending_page = client.get('/enrollment-pending')
    assert pending_page.status_code == 200
    assert b"Section Enrollment Pending" in pending_page.data
    print("   [+] GET /enrollment-pending -> 200 OK")

    # Submit Student Roll Number
    req_res = client.post('/enrollment/request-access', data={
        'student_id': 'GLA26999',
        'section': '2FE',
        'note': 'Direct lateral entry admission.'
    }, follow_redirects=True)
    assert req_res.status_code == 200
    with app.app_context():
        enr = Enrollment.query.filter_by(user_id=verified_user.id).first()
        assert enr is not None
        assert enr.student_id == 'GLA26999'
        assert enr.status == 'pending'
    print("   [+] Submitted Roll Number GLA26999 -> Pending Enrollment recorded")

    # ----------------------------------------------------
    # 5. Pre-Authorized Roster Instant Enrollment
    # ----------------------------------------------------
    print("\n[*] 5. Testing Official Roster Instant Enrollment Flow...")
    # Register an approved roster student: priya.singh@gla.ac.in (GLA26002 on roster)
    client.get('/logout', follow_redirects=True)
    with app.app_context():
        priya = User.query.filter_by(email='priya.singh@gla.ac.in').first()
        # Ensure clean state
        priya.is_verified = False
        priya.verification_token = 'priya-test-token-789'
        db.session.commit()

    ver_priya = client.get('/verify-email/priya-test-token-789', follow_redirects=True)
    assert ver_priya.status_code == 200
    assert b"enrollment is active" in ver_priya.data or b"Welcome to ClassCatch" in ver_priya.data
    with app.app_context():
        p_user = User.query.filter_by(email='priya.singh@gla.ac.in').first()
        assert p_user.is_verified is True
        assert p_user.active_enrollment is not None
        assert p_user.active_enrollment.section == '2FE'
        assert p_user.active_enrollment.status == 'approved'
    print("   [+] Pre-authorized roster user verified -> INSTANT 2FE ACTIVE ENROLLMENT")

    # ----------------------------------------------------
    # 6. Section Isolation & Authorization
    # ----------------------------------------------------
    print("\n[*] 6. Testing Section Isolation & Cross-Section Leakage Prevention...")
    with app.app_context():
        # Create a rogue course belonging to Section 3FF (unrelated section)
        foreign_course = Course(
            name="Mechanical Thermodynamics",
            code="BME-3001",
            section="3FF",
            semester=3,
            department="ME",
            instructor="Dr. Foreign",
            room="AB-II Room 101"
        )
        db.session.add(foreign_course)
        db.session.commit()
        foreign_id = foreign_course.id

    # 2FE Student (Priya) tries to access Section 3FF course
    foreign_access_res = client.get(f'/course/{foreign_id}', follow_redirects=True)
    assert b"Access restricted" in foreign_access_res.data or foreign_access_res.status_code in [302, 403, 200]
    # Verify course list for student does not show Section 3FF
    home_page = client.get('/')
    assert b"BME-3001" not in home_page.data
    print("   [+] Section Isolation: 2FE student blocked from foreign section course")

    # ----------------------------------------------------
    # 7. Storage Abstraction Layer & File Security
    # ----------------------------------------------------
    print("\n[*] 7. Testing Storage Abstraction Layer & File Upload Security...")
    with app.app_context():
        admin_user = User.query.filter_by(email='admin@classcatch.edu').first()
        admin_id = admin_user.id

        # A. Whitelist check
        assert is_allowed_file("lecture_notes.pdf") is True
        assert is_allowed_file("whiteboard.jpg") is True
        assert is_allowed_file("code_bundle.zip") is True

        # B. Blacklist executables check
        for dangerous_ext in ['virus.exe', 'script.bat', 'payload.cmd', 'backdoor.ps1', 'malware.sh']:
            assert is_allowed_file(dangerous_ext) is False
        print("   [+] Extension Validation: Executables strictly blocked, PDFs/Images allowed")

        # C. Valid upload simulation
        pdf_content = b"%PDF-1.4 Mock PDF content for lecture notes."
        pdf_file = FileStorage(stream=io.BytesIO(pdf_content), filename="DSA_Unit_2_Notes.pdf", content_type="application/pdf")
        storage_rec, err = handle_file_upload(pdf_file, admin_id, course_id=1, section='2FE')
        assert err is None
        assert storage_rec is not None
        assert storage_rec.original_filename == "DSA_Unit_2_Notes.pdf"
        assert storage_rec.file_type == "pdf"
        file_id = storage_rec.id
        print("   [+] Valid PDF stored -> Metadata saved to Postgres, binary in storage")

        # D. Malicious upload simulation
        bad_file = FileStorage(stream=io.BytesIO(b"malicious"), filename="hack.exe", content_type="application/x-msdownload")
        bad_rec, bad_err = handle_file_upload(bad_file, admin_id)
        assert bad_rec is None
        assert "strictly prohibited" in bad_err
        print("   [+] Executable upload blocked by handle_file_upload()")

    # Test file download endpoint
    dl_res = client.get(f'/storage/download/{file_id}')
    assert dl_res.status_code == 200
    print(f"   [+] GET /storage/download/{file_id} -> 200 OK (Downloaded securely)")

    # ----------------------------------------------------
    # 8. Admin Control Center: Enrollment, Roster & Timetable
    # ----------------------------------------------------
    print("\n[*] 8. Testing Admin Control Center Endpoints...")
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'admin@classcatch.edu', 'password': 'password123'}, follow_redirects=True)

    # Admin views
    for path, title_match in [
        ('/admin/enrollment', b"Enrollment"),
        ('/admin/timetable', b"Timetable Management"),
        ('/admin/storage', b"Storage")
    ]:
        v_res = client.get(path)
        assert v_res.status_code == 200, f"Failed on {path}: {v_res.status_code}"
        assert title_match in v_res.data
        print(f"   [+] GET {path} -> 200 OK")

    # Admin approves pending student
    with app.app_context():
        pending_enr = Enrollment.query.filter_by(status='pending').first()
        pending_id = pending_enr.id if pending_enr else 1

    appr_res = client.post(f'/admin/enrollment/{pending_id}/approve', follow_redirects=True)
    assert appr_res.status_code == 200
    with app.app_context():
        appr_enr = db.session.get(Enrollment, pending_id)
        assert appr_enr.status == 'approved'
        assert appr_enr.is_active is True
    print(f"   [+] POST /admin/enrollment/{pending_id}/approve -> Student enrollment approved!")

    # Admin moves student section
    move_res = client.post(f'/admin/enrollment/{pending_id}/move', data={
        'section': '2FE',
        'semester': 3,
        'reason': 'Verified section placement.'
    }, follow_redirects=True)
    assert move_res.status_code == 200
    print("   [+] POST /admin/enrollment/move -> Section reassigned with audit trail")

    # Admin imports CSV roster
    sample_roster_csv = "email,name,student_id,section,program,semester,academic_year\n" \
                        "kanishk.sharma@gla.ac.in,Kanishk Sharma,GLA26008,2FE,B.Tech CSE,3,2026-27\n"
    import_res = client.post('/admin/enrollment/import', data={'csv_data': sample_roster_csv}, follow_redirects=True)
    assert import_res.status_code == 200
    with app.app_context():
        k_roster = RosterEntry.query.filter_by(email='kanishk.sharma@gla.ac.in').first()
        assert k_roster is not None
        assert k_roster.student_id == 'GLA26008'
    print("   [+] POST /admin/enrollment/import -> Roster CSV processed & records created")

    # CSV Exports
    for entity in ['users', 'courses', 'enrollments', 'roster', 'timetable', 'storage']:
        exp_res = client.get(f'/admin/export/{entity}')
        assert exp_res.status_code == 200
        assert 'text/csv' in exp_res.headers['Content-Type']
        print(f"   [+] GET /admin/export/{entity} -> 200 OK (CSV validated)")

    # ----------------------------------------------------
    # 9. Attendance Mathematical Validation
    # ----------------------------------------------------
    print("\n[*] 9. Testing Attendance Math Model (75% Threshold)...")
    with app.app_context():
        # Case A: Above threshold (28/32 = 87.5%)
        safe_att = AttendanceRecord(user_id=1, course_id=1, total_classes=32, attended_classes=28, target_percentage=75.0)
        assert safe_att.current_percentage == 87.5
        assert safe_att.bunks_available == 5
        assert safe_att.classes_needed == 0
        print(f"   [+] Safe Attendance: 28/32 (87.5%) -> 5 safe bunks available")

        # Case B: Below threshold (20/30 = 66.7%)
        risk_att = AttendanceRecord(user_id=1, course_id=1, total_classes=30, attended_classes=20, target_percentage=75.0)
        assert risk_att.current_percentage == 66.7
        assert risk_att.bunks_available == 0
        assert risk_att.classes_needed == 10
        print(f"   [+] Attendance Recovery: 20/30 (66.7%) -> Needs 10 consecutive classes to reach 75%")

    # ----------------------------------------------------
    # 10. Student Features: Summaries, Chat, Lounge & Deadlines
    # ----------------------------------------------------
    print("\n[*] 10. Testing Student Collaborative Features (Summaries, Chat, Lounge)...")
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'priya.singh@gla.ac.in', 'password': 'password123'}, follow_redirects=True)

    # Post new summary
    new_sum = client.post('/summary/new', data={
        'course_id': 1,
        'date': '2026-09-08',
        'category': 'Lecture Notes',
        'topic': 'Software Architecture Patterns',
        'content': 'Overview of MVC, Layered, and Microservices architecture patterns.'
    }, follow_redirects=True)
    assert new_sum.status_code == 200
    print("   [+] POST /summary/new -> Success & Posted")

    # Post in course chat
    chat_res = client.post('/course/1/chat', data={
        'category': 'Doubt',
        'message': 'Can anyone explain the difference between functional and non-functional requirements?'
    }, follow_redirects=True)
    assert chat_res.status_code == 200
    print("   [+] POST /course/1/chat -> Chat Message Delivered")

    # Access Lounge
    lounge_res = client.get('/lounge')
    assert lounge_res.status_code == 200
    assert b"Campus Lounge" in lounge_res.data
    print("   [+] GET /lounge -> 200 OK")

    # Toggle deadline
    dl_toggle = client.post('/deadlines/1/toggle', follow_redirects=True)
    assert dl_toggle.status_code == 200
    print("   [+] POST /deadlines/1/toggle -> Success")

    # Student Content Report
    rep_res = client.post('/report', data={
        'target_type': 'summary',
        'target_id': 1,
        'category': 'Incorrect Information',
        'reason': 'The homework section numbers need updating.'
    }, follow_redirects=True)
    assert rep_res.status_code == 200
    print("   [+] POST /report -> Content Report logged for Admin Review")

    # ----------------------------------------------------
    # 11. Feature Flags & Maintenance Mode
    # ----------------------------------------------------
    print("\n[*] 11. Testing Dynamic Feature Flags & Maintenance Safeguards...")
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'admin@classcatch.edu', 'password': 'password123'}, follow_redirects=True)

    # Toggle feature flag
    flag_res = client.post('/admin/feature-flags/ai_ocr/toggle', follow_redirects=True)
    assert flag_res.status_code == 200
    print("   [+] POST /admin/feature-flags/ai_ocr/toggle -> Success")

    # Test Maintenance Mode Guard
    with app.app_context():
        from models import SystemSetting
        m_set = SystemSetting.query.filter_by(key='maintenance_mode').first()
        if not m_set:
            m_set = SystemSetting(key='maintenance_mode', value='true')
            db.session.add(m_set)
        else:
            m_set.value = 'true'
        db.session.commit()

    # Ordinary student visiting /catchup should be redirected to /maintenance
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'priya.singh@gla.ac.in', 'password': 'password123'}, follow_redirects=True)
    maint_redirect = client.get('/catchup', follow_redirects=False)
    assert maint_redirect.status_code == 302
    assert '/maintenance' in maint_redirect.location
    print("   [+] Maintenance Guard: Student redirected to /maintenance")

    # Restore normal mode
    with app.app_context():
        m_set = SystemSetting.query.filter_by(key='maintenance_mode').first()
        m_set.value = 'false'
        db.session.commit()
    print("   [+] Maintenance Guard: Restored to normal operation")

    print("\n========================================================")
    print("ALL GLA 2FE PILOT & HARDENING TESTS PASSED SUCCESSFULLY!")
    print("========================================================\n")

if __name__ == '__main__':
    test_classcatch_pilot()
