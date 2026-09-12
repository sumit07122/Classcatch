from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User model representing students, CRs, Instructors, and Platform Admins.
    Inherits UserMixin for Flask-Login session management.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)  # 'student', 'cr', 'admin', 'superadmin'
    avatar_color = db.Column(db.String(20), default='indigo', nullable=False)
    karma = db.Column(db.Integer, default=50, nullable=False)

    # Student Profile / Onboarding Details
    college = db.Column(db.String(120), default='GLA University', nullable=True)
    department = db.Column(db.String(100), default='CSE', nullable=True)
    program = db.Column(db.String(100), default='B.Tech CSE', nullable=True)
    semester = db.Column(db.Integer, default=3, nullable=False)
    section = db.Column(db.String(20), default='2FE', nullable=False)
    student_id = db.Column(db.String(50), nullable=True, index=True)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(100), nullable=True)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False)
    is_onboarded = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    summaries = db.relationship('Summary', backref='author', lazy=True, cascade='all, delete-orphan')
    chats = db.relationship('ChatMessage', backref='author', lazy=True, cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', backref='author', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True, cascade='all, delete-orphan')
    deadlines = db.relationship('Deadline', backref='author', lazy=True, cascade='all, delete-orphan')
    resources = db.relationship('Resource', backref='author', lazy=True, cascade='all, delete-orphan')
    cr_assignments = db.relationship('CRAssignment', foreign_keys='CRAssignment.user_id', backref='user', lazy=True, cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', foreign_keys='Enrollment.user_id', backref='user', lazy=True, cascade='all, delete-orphan')

    @property
    def active_enrollment(self):
        """Returns the single active approved academic enrollment record."""
        for e in self.enrollments:
            if e.is_active and e.status == 'approved':
                return e
        return None

    @property
    def active_section(self):
        """Returns the student's active section (defaults to 2FE for GLA pilot)."""
        ae = self.active_enrollment
        return ae.section if ae else (self.section or '2FE')

    @property
    def badge(self):
        """Dynamic reputation badge based on student contribution karma."""
        if self.karma >= 300:
            return {'name': 'Campus Legend', 'icon': 'fa-crown', 'color': 'warning', 'level': 4}
        elif self.karma >= 150:
            return {'name': "Dean's Scholar", 'icon': 'fa-medal', 'color': 'primary', 'level': 3}
        elif self.karma >= 75:
            return {'name': 'Class Savior', 'icon': 'fa-award', 'color': 'info', 'level': 2}
        else:
            return {'name': 'Rising Contributor', 'icon': 'fa-star', 'color': 'secondary', 'level': 1}

    def is_admin(self):
        """Check if user has administrative privileges."""
        return self.role in ['admin', 'superadmin']

    def is_superadmin(self):
        """Check if user has superadmin privileges."""
        return self.role == 'superadmin'

    def is_cr(self):
        """Check if user is a Class Representative or Admin."""
        return self.role in ['cr', 'admin', 'superadmin']

    def is_cr_for(self, course_id, section=None):
        """Check if user is authorized as CR for a specific course/section."""
        if self.is_admin():
            return True
        if self.role != 'cr':
            return False
        # Check explicit CRAssignment
        match = CRAssignment.query.filter_by(user_id=self.id, course_id=course_id).first()
        if not match:
            return False
        if section and match.section != 'ALL' and match.section != section:
            return False
        return True

    def set_password(self, password):
        """Hash and set the user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.name}) - Role: {self.role}>'


class Course(db.Model):
    """
    Course model representing academic subjects, schedule, room, and section.
    """
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), nullable=False, index=True)
    section = db.Column(db.String(10), default='2FE', nullable=False)
    semester = db.Column(db.Integer, default=3, nullable=False)
    department = db.Column(db.String(50), default='CSE', nullable=False)
    academic_year = db.Column(db.String(20), default='2026-27', nullable=False)
    is_lateral = db.Column(db.Boolean, default=True, nullable=False)
    instructor = db.Column(db.String(120), default='Prof. TBD', nullable=False)
    room = db.Column(db.String(60), default='AB-VI Room 306', nullable=False)
    schedule = db.Column(db.String(150), default='Mon, Wed 10:00 AM - 11:30 AM', nullable=False)
    status = db.Column(db.String(40), default='Scheduled', nullable=False)  # Scheduled, Cancelled, Extra Class
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    summaries = db.relationship('Summary', backref='course', lazy=True, cascade='all, delete-orphan')
    chats = db.relationship('ChatMessage', backref='course', lazy=True, cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', backref='course', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('AttendanceRecord', backref='course', lazy=True, cascade='all, delete-orphan')
    deadlines = db.relationship('Deadline', backref='course', lazy=True, cascade='all, delete-orphan')
    resources = db.relationship('Resource', backref='course', lazy=True, cascade='all, delete-orphan')
    cr_assignments = db.relationship('CRAssignment', backref='course', lazy=True, cascade='all, delete-orphan')
    timetable_slots = db.relationship('TimetableSlot', backref='course', lazy=True, cascade='all, delete-orphan')

    @property
    def full_title(self):
        """Helper property to display formatted course code and title."""
        return f"{self.code} - {self.name} (Sec {self.section})"

    def __repr__(self):
        return f'<Course {self.code} - {self.name}>'


class CRAssignment(db.Model):
    """
    Explicit assignment of Class Representative (CR) authority to a student for a course.
    """
    __tablename__ = 'cr_assignments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    section = db.Column(db.String(20), default='A', nullable=False)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<CRAssignment User:{self.user_id} Course:{self.course_id} Sec:{self.section}>'


class Summary(db.Model):
    """
    Summary model representing a peer-submitted catch-up note for a specific class.
    """
    __tablename__ = 'summaries'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    topic = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), default='Lecture Notes', nullable=False)  # Lecture Notes, Assignment, Exam Prep
    content = db.Column(db.Text, nullable=False)
    helpful_count = db.Column(db.Integer, default=0, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verified_by = db.Column(db.String(100), nullable=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Summary Course:{self.course_id} Date:{self.date} Topic:{self.topic}>'


class ChatMessage(db.Model):
    """
    Peer-to-peer unofficial discussion / requirement exchange message.
    Can be tied to a specific course, or course_id=None for the general campus lounge.
    Supports anonymous mode for honest doubt clearing.
    """
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), default='General', nullable=False)  # Requirement, Doubt, General, Notes Request
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<ChatMessage User:{self.user_id} Course:{self.course_id}>'


class Announcement(db.Model):
    """
    Class or Platform announcements (exams, quizzes, assignment deadlines, room changes).
    """
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(30), default='General', nullable=False)  # Exam, Quiz, Assignment, Room Change, Urgent
    target_scope = db.Column(db.String(30), default='course', nullable=False)  # platform, course, semester, section
    target_section = db.Column(db.String(20), default='2FE', nullable=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Announcement {self.title} ({self.tag})>'


class AttendanceRecord(db.Model):
    """
    Stores individual student's attendance statistics per course.
    """
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    total_classes = db.Column(db.Integer, default=0, nullable=False)
    attended_classes = db.Column(db.Integer, default=0, nullable=False)
    target_percentage = db.Column(db.Float, default=75.0, nullable=False)

    @property
    def current_percentage(self):
        """Calculate current attendance percentage."""
        if self.total_classes == 0:
            return 100.0
        return round((self.attended_classes / self.total_classes) * 100.0, 1)

    @property
    def bunks_available(self):
        """
        Calculate how many consecutive classes can be safely bunked/missed
        while maintaining attendance >= target_percentage.
        Formula: floor((Attended - Target * Total) / Target)
        """
        if self.total_classes == 0 or self.attended_classes == 0:
            return 0
        target = self.target_percentage / 100.0
        max_bunks = int((self.attended_classes - (target * self.total_classes)) / target)
        return max(0, max_bunks)

    @property
    def classes_needed(self):
        """
        Calculate how many consecutive classes must be attended to recover
        attendance back to target_percentage.
        Formula: ceil((Target * Total - Attended) / (1 - Target))
        """
        if self.current_percentage >= self.target_percentage:
            return 0
        target = self.target_percentage / 100.0
        if target >= 1.0:
            return 0
        needed = ((target * self.total_classes) - self.attended_classes) / (1.0 - target)
        import math
        return max(0, math.ceil(needed))

    def __repr__(self):
        return f'<Attendance User:{self.user_id} Course:{self.course_id} %:{self.current_percentage}>'


class Deadline(db.Model):
    """
    Academic deadlines, assignments, and exam countdowns.
    """
    __tablename__ = 'deadlines'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    category = db.Column(db.String(40), default='Assignment', nullable=False)  # Assignment, Quiz, Exam, Lab Submission
    priority = db.Column(db.String(20), default='Normal', nullable=False)     # High, Medium, Normal
    description = db.Column(db.Text, nullable=True)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    is_official = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def days_remaining(self):
        from datetime import date
        today = date.today()
        return (self.due_date - today).days

    @property
    def is_overdue(self):
        return self.days_remaining < 0 and not self.is_completed

    @property
    def is_urgent(self):
        return 0 <= self.days_remaining <= 2 and not self.is_completed

    def __repr__(self):
        return f'<Deadline {self.title} Due:{self.due_date}>'


class Resource(db.Model):
    """
    Shared academic resources: PYQs, formula sheets, lab manuals, and slides.
    Supports approval/moderation workflow.
    """
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='PYQ & Solutions', nullable=False)  # PYQ, Formula Sheet, Lab Manual, Handwritten Notes
    resource_url = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    downloads = db.Column(db.Integer, default=0, nullable=False)
    helpful_count = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(30), default='Approved', nullable=False)  # Approved, Pending Review, Rejected, Archived
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Resource {self.title} ({self.category}) - Status: {self.status}>'


class Report(db.Model):
    """
    Moderation report submitted by students or CRs regarding inappropriate or inaccurate content.
    """
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    target_type = db.Column(db.String(40), nullable=False)  # 'summary', 'chat', 'resource', 'user'
    target_id = db.Column(db.Integer, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)     # Spam, Incorrect Information, Inappropriate Content, Harassment, Fake Resource, Abuse, Other
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='Open', nullable=False)  # Open, Under Review, Resolved, Dismissed
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='reports_submitted')
    resolver = db.relationship('User', foreign_keys=[resolved_by_id], backref='reports_resolved')

    def __repr__(self):
        return f'<Report #{self.id} Type:{self.target_type} Status:{self.status}>'


class AuditLog(db.Model):
    """
    Immutable audit log recording critical operational and administrative actions.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)       # user.role_change, cr.assigned, course.created, etc.
    target_type = db.Column(db.String(50), nullable=True)    # user, course, resource, setting, feature_flag
    target_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f'<AuditLog {self.action} by User:{self.user_id}>'


class FeatureFlag(db.Model):
    """
    Feature flag controlling system modules dynamically without code redeployment.
    """
    __tablename__ = 'feature_flags'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<FeatureFlag {self.key}: {self.is_enabled}>'


class SystemSetting(db.Model):
    """
    Global system settings configured by administrators.
    """
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<SystemSetting {self.key}={self.value}>'


class Enrollment(db.Model):
    """
    Academic section enrollment record.
    Enforces 'One User = One Active Class Enrollment' scoped to academic session.
    """
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    student_id = db.Column(db.String(50), nullable=True, index=True)
    college = db.Column(db.String(120), default='GLA University, Mathura Campus', nullable=False)
    department = db.Column(db.String(100), default='CSE', nullable=False)
    program = db.Column(db.String(100), default='B.Tech CSE', nullable=False)
    academic_year = db.Column(db.String(20), default='2026-27', nullable=False)
    semester = db.Column(db.Integer, default=3, nullable=False)
    section = db.Column(db.String(20), default='2FE', nullable=False, index=True)
    is_lateral = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)  # 'approved', 'pending', 'rejected', 'inactive'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    rejection_reason = db.Column(db.Text, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    approver = db.relationship('User', foreign_keys=[approved_by_id])

    def __repr__(self):
        return f'<Enrollment User:{self.user_id} {self.section} Sem:{self.semester} ({self.status})>'


class RosterEntry(db.Model):
    """
    Official institutional student roster uploaded by Admin via CSV.
    Used to pre-authorize GLA email accounts upon verification.
    """
    __tablename__ = 'roster_entries'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    section = db.Column(db.String(20), default='2FE', nullable=False, index=True)
    program = db.Column(db.String(100), default='B.Tech CSE', nullable=False)
    semester = db.Column(db.Integer, default=3, nullable=False)
    academic_year = db.Column(db.String(20), default='2026-27', nullable=False)
    is_registered = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<RosterEntry {self.email} ({self.student_id}) Sec:{self.section}>'


class TimetableSlot(db.Model):
    """
    Scheduled class timetable slot for a section.
    Supports weekly Mon-Fri grids and daily cards.
    """
    __tablename__ = 'timetable_slots'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    day_of_week = db.Column(db.String(20), nullable=False, index=True)  # 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
    start_time = db.Column(db.String(20), nullable=False)               # '10:00 AM'
    end_time = db.Column(db.String(20), nullable=False)                 # '11:00 AM'
    slot_type = db.Column(db.String(20), default='Lecture', nullable=False)  # 'Lecture', 'Lab', 'Tutorial'
    building = db.Column(db.String(50), default='AB-VI', nullable=False)
    room = db.Column(db.String(50), default='306', nullable=False)
    faculty = db.Column(db.String(100), nullable=True)
    section = db.Column(db.String(20), default='2FE', nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def time_range(self):
        return f"{self.start_time} - {self.end_time}"

    @property
    def location(self):
        return f"{self.building} Room {self.room}"

    def __repr__(self):
        return f'<TimetableSlot Course:{self.course_id} {self.day_of_week} {self.time_range} ({self.section})>'


class AcademicStaff(db.Model):
    """
    Institutional academic staff / leadership record.
    E.g., Head of Department, Program Co-Ordinator, Class Advisor.
    """
    __tablename__ = 'academic_staff'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    employee_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    designation = db.Column(db.String(100), nullable=False)  # 'Head of Department', 'Program Co-Ordinator', 'Class Advisor'
    department = db.Column(db.String(100), default='CSE', nullable=False)
    section = db.Column(db.String(20), nullable=True)        # e.g., '2FE' for Class Advisor
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<AcademicStaff {self.name} ({self.designation})>'


class StorageFile(db.Model):
    """
    Metadata record for files stored via object storage or local filesystem storage.
    Files are never stored as binary BLOBs inside Postgres.
    """
    __tablename__ = 'storage_files'

    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True, index=True)
    section = db.Column(db.String(20), default='2FE', nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)        # 'pdf', 'image', 'document', 'archive', 'notes'
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)           # Size in bytes
    storage_path = db.Column(db.String(500), nullable=False)
    storage_provider = db.Column(db.String(50), default='local', nullable=False)
    status = db.Column(db.String(30), default='Active', nullable=False)  # 'Active', 'Archived', 'Deleted'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    uploader = db.relationship('User', foreign_keys=[uploader_id], backref='uploaded_files')
    course = db.relationship('Course', foreign_keys=[course_id], backref='storage_files')

    @property
    def formatted_size(self):
        kb = self.file_size / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.2f} MB"

    def __repr__(self):
        return f'<StorageFile #{self.id} {self.original_filename} ({self.formatted_size})>'
