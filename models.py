from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User model representing students or instructors.
    Inherits UserMixin for Flask-Login session management.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)
    avatar_color = db.Column(db.String(20), default='indigo', nullable=False)
    karma = db.Column(db.Integer, default=50, nullable=False)

    # Relationships
    summaries = db.relationship('Summary', backref='author', lazy=True, cascade='all, delete-orphan')
    chats = db.relationship('ChatMessage', backref='author', lazy=True, cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', backref='author', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True, cascade='all, delete-orphan')
    deadlines = db.relationship('Deadline', backref='author', lazy=True, cascade='all, delete-orphan')
    resources = db.relationship('Resource', backref='author', lazy=True, cascade='all, delete-orphan')

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

    def set_password(self, password):
        """Hash and set the user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.name})>'


class Course(db.Model):
    """
    Course model representing academic subjects, schedule, room, and section.
    """
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), nullable=False, index=True)
    section = db.Column(db.String(10), default='A', nullable=False)
    semester = db.Column(db.Integer, default=1, nullable=False)
    instructor = db.Column(db.String(120), default='Prof. TBD', nullable=False)
    room = db.Column(db.String(60), default='Lecture Hall 101', nullable=False)
    schedule = db.Column(db.String(150), default='Mon, Wed 10:00 AM - 11:30 AM', nullable=False)
    status = db.Column(db.String(40), default='Scheduled', nullable=False)  # Scheduled, Cancelled, Extra Class

    # Relationships
    summaries = db.relationship('Summary', backref='course', lazy=True, cascade='all, delete-orphan')
    chats = db.relationship('ChatMessage', backref='course', lazy=True, cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', backref='course', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('AttendanceRecord', backref='course', lazy=True, cascade='all, delete-orphan')
    deadlines = db.relationship('Deadline', backref='course', lazy=True, cascade='all, delete-orphan')
    resources = db.relationship('Resource', backref='course', lazy=True, cascade='all, delete-orphan')

    @property
    def full_title(self):
        """Helper property to display formatted course code and title."""
        return f"{self.code} - {self.name} (Sec {self.section})"

    def __repr__(self):
        return f'<Course {self.code} - {self.name}>'


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
    Class announcements (exams, quizzes, assignment deadlines, room changes).
    """
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(30), default='General', nullable=False)  # Exam, Quiz, Assignment, Room Change, Urgent
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
        Formula: floor((Attended / (Target / 100)) - Total)
        """
        if self.total_classes == 0 or self.attended_classes == 0:
            return 0
        target = self.target_percentage / 100.0
        # (attended / (total + x)) >= target  =>  attended >= target * total + target * x
        # target * x <= attended - (target * total) => x <= (attended - target * total) / target
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
        # (attended + y) / (total + y) >= target
        # attended + y >= target * total + target * y
        # y * (1 - target) >= target * total - attended
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Resource {self.title} ({self.category})>'
