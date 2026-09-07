import os
from datetime import date, datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord
from forms import RegistrationForm, LoginForm, SummaryForm, ChatMessageForm, AnnouncementForm, AttendanceForm

# Initialize Flask application
app = Flask(__name__)

# Application Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'classcatch-secret-key-2026-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///classcatch.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to participate in ClassCatch discussions.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader."""
    return User.query.get(int(user_id))


@app.context_processor
def inject_globals():
    """Inject common utility data into all Jinja templates."""
    all_courses = Course.query.order_by(Course.code).all() if Course.query else []
    return {
        'today': date.today(),
        'current_year': datetime.now().year,
        'global_courses': all_courses
    }


# ==========================================
# Authentication Routes
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new student registration."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role='student'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('🎉 Welcome to ClassCatch! Your account is created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', title='Join ClassCatch', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle student login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f'👋 Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('Invalid email or password. Please verify your credentials.', 'danger')

    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
@login_required
def logout():
    """Handle student logout."""
    logout_user()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('index'))


# ==========================================
# Home & Feed Routes
# ==========================================

@app.route('/')
def index():
    """
    Home page:
    - Lists enrolled courses with summary count, chat count, and schedule status.
    - Shows today's catch-up summaries.
    - Displays urgent university/class announcements.
    """
    courses = Course.query.order_by(Course.code).all()
    today_summaries = Summary.query.filter_by(date=date.today()).order_by(Summary.created_at.desc()).all()
    recent_summaries = Summary.query.order_by(Summary.date.desc(), Summary.created_at.desc()).limit(6).all()
    urgent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()

    # User attendance overview if logged in
    user_attendance = []
    if current_user.is_authenticated:
        user_attendance = AttendanceRecord.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'index.html',
        title='ClassCatch - Peer-Powered College Catch-up',
        courses=courses,
        today_summaries=today_summaries,
        recent_summaries=recent_summaries,
        urgent_announcements=urgent_announcements,
        user_attendance=user_attendance
    )


# ==========================================
# Course Hub (Tabs: Summaries, Chat, Announcements, Schedule)
# ==========================================

@app.route('/course/<int:course_id>', methods=['GET'])
def course_detail(course_id):
    """
    Unified course hub featuring:
    - Tab 1: Summaries (with date filter)
    - Tab 2: Unofficial Peer Chat
    - Tab 3: Announcements
    - Tab 4: Timetable & Room Availability
    """
    course = Course.query.get_or_404(course_id)
    active_tab = request.args.get('tab', 'summaries')
    date_filter = request.args.get('date')

    # Summaries with optional date filter
    query = Summary.query.filter_by(course_id=course.id)
    if date_filter:
        try:
            filter_date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(date=filter_date_obj)
        except ValueError:
            flash('Invalid date filter provided. Showing all dates.', 'warning')
    summaries = query.order_by(Summary.date.desc(), Summary.created_at.desc()).all()

    # Unofficial chat messages for this course
    chats = ChatMessage.query.filter_by(course_id=course.id).order_by(ChatMessage.created_at.asc()).all()

    # Announcements for this course
    announcements = Announcement.query.filter_by(course_id=course.id).order_by(Announcement.created_at.desc()).all()

    # Forms for tab interactions
    summary_form = SummaryForm()
    summary_form.course_id.choices = [(course.id, course.full_title)]
    summary_form.course_id.data = course.id
    summary_form.date.data = date.today()

    chat_form = ChatMessageForm()
    announcement_form = AnnouncementForm()

    return render_template(
        'course.html',
        title=f"{course.code} Hub",
        course=course,
        active_tab=active_tab,
        summaries=summaries,
        chats=chats,
        announcements=announcements,
        summary_form=summary_form,
        chat_form=chat_form,
        announcement_form=announcement_form,
        date_filter=date_filter
    )


@app.route('/course/<int:course_id>/summary', methods=['POST'])
@login_required
def post_course_summary(course_id):
    """Post a summary directly from the course page."""
    course = Course.query.get_or_404(course_id)
    form = SummaryForm()
    form.course_id.choices = [(course.id, course.full_title)]

    if form.validate_on_submit():
        summary = Summary(
            course_id=course.id,
            user_id=current_user.id,
            date=form.date.data,
            topic=form.topic.data.strip() if form.topic.data else None,
            category=form.category.data,
            content=form.content.data.strip()
        )
        db.session.add(summary)
        db.session.commit()
        flash(f'✅ Catch-up note for {course.code} on {summary.date} published!', 'success')
    else:
        for err in form.errors.values():
            flash(err[0], 'danger')

    return redirect(url_for('course_detail', course_id=course.id, tab='summaries'))


@app.route('/course/<int:course_id>/chat', methods=['POST'])
@login_required
def post_course_chat(course_id):
    """Post a message in the unofficial course chat."""
    course = Course.query.get_or_404(course_id)
    form = ChatMessageForm()

    if form.validate_on_submit():
        chat = ChatMessage(
            course_id=course.id,
            user_id=current_user.id,
            message=form.message.data.strip(),
            category=form.category.data
        )
        db.session.add(chat)
        db.session.commit()
        flash('Message sent to class chat!', 'info')
    else:
        flash('Message cannot be empty.', 'danger')

    return redirect(url_for('course_detail', course_id=course.id, tab='chat'))


@app.route('/course/<int:course_id>/announcement', methods=['POST'])
@login_required
def post_course_announcement(course_id):
    """Post an announcement for the class."""
    course = Course.query.get_or_404(course_id)
    form = AnnouncementForm()

    if form.validate_on_submit():
        announcement = Announcement(
            course_id=course.id,
            user_id=current_user.id,
            title=form.title.data.strip(),
            tag=form.tag.data,
            content=form.content.data.strip()
        )
        db.session.add(announcement)
        db.session.commit()
        flash('📢 Announcement published to class board!', 'success')
    else:
        flash('Please fill in valid announcement details.', 'danger')

    return redirect(url_for('course_detail', course_id=course.id, tab='announcements'))


# ==========================================
# Dedicated Summary & Helpful Actions
# ==========================================

@app.route('/summary/new', methods=['GET', 'POST'])
@login_required
def post_summary():
    """Standalone page to post a class summary."""
    courses = Course.query.order_by(Course.code).all()
    if not courses:
        flash('No courses exist in the system yet.', 'warning')
        return redirect(url_for('index'))

    form = SummaryForm()
    form.course_id.choices = [(c.id, f"{c.code} - {c.name} (Sec {c.section})") for c in courses]

    if request.method == 'GET':
        pre_course_id = request.args.get('course_id', type=int)
        if pre_course_id and any(c.id == pre_course_id for c in courses):
            form.course_id.data = pre_course_id
        form.date.data = date.today()

    if form.validate_on_submit():
        summary = Summary(
            course_id=form.course_id.data,
            user_id=current_user.id,
            date=form.date.data,
            topic=form.topic.data.strip() if form.topic.data else None,
            category=form.category.data,
            content=form.content.data.strip()
        )
        db.session.add(summary)
        db.session.commit()

        flash('✅ Catch-up summary submitted successfully!', 'success')
        return redirect(url_for('course_detail', course_id=summary.course_id, tab='summaries'))

    return render_template('post_summary.html', title='Post Class Catch-up', form=form)


@app.route('/summary/<int:summary_id>')
def summary_detail(summary_id):
    """Detailed standalone view of an individual catch-up note."""
    summary = Summary.query.get_or_404(summary_id)
    return render_template('summary_detail.html', title=f"Note: {summary.course.code}", summary=summary)


@app.route('/summary/<int:summary_id>/helpful', methods=['POST'])
def mark_helpful(summary_id):
    """Upvote / mark a summary as helpful."""
    summary = Summary.query.get_or_404(summary_id)
    summary.helpful_count += 1
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'helpful_count': summary.helpful_count})

    flash('Marked as helpful! Thank you for supporting your peer.', 'success')
    return redirect(request.referrer or url_for('summary_detail', summary_id=summary.id))


# ==========================================
# Campus Lounge / Unofficial General Chat
# ==========================================

@app.route('/lounge', methods=['GET', 'POST'])
def lounge():
    """
    Campus-wide unofficial discussion lounge.
    Students can post requirements, ask for previous question papers,
    lab manuals, project partners, etc.
    """
    form = ChatMessageForm()
    category_filter = request.args.get('category')

    query = ChatMessage.query.filter_by(course_id=None)
    if category_filter and category_filter != 'All':
        query = query.filter_by(category=category_filter)

    messages = query.order_by(ChatMessage.created_at.desc()).limit(50).all()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please log in to chat in the Campus Lounge.', 'warning')
            return redirect(url_for('login', next=url_for('lounge')))

        chat = ChatMessage(
            course_id=None,
            user_id=current_user.id,
            message=form.message.data.strip(),
            category=form.category.data
        )
        db.session.add(chat)
        db.session.commit()
        flash('Requirement / message posted to Campus Lounge!', 'success')
        return redirect(url_for('lounge'))

    return render_template('lounge.html', title='Campus Lounge & Requirements', form=form, messages=messages, category_filter=category_filter)


# ==========================================
# Smart Attendance Calculator & Course Tracker
# ==========================================

@app.route('/attendance', methods=['GET', 'POST'])
def attendance_calculator():
    """
    Interactive college attendance calculator and per-course tracker:
    - Dynamic calculator: Enter total & attended to calculate percentage,
      safe bunks available, or recovery classes required.
    - Course-wise tracker: Logged-in students can record their ongoing course attendance.
    """
    form = AttendanceForm()
    courses = Course.query.order_by(Course.code).all()
    form.course_id.choices = [(c.id, f"{c.code} - {c.name}") for c in courses]

    user_records = []
    if current_user.is_authenticated:
        user_records = AttendanceRecord.query.filter_by(user_id=current_user.id).all()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Log in to save attendance records to your personal dashboard.', 'info')
            return redirect(url_for('login', next=url_for('attendance_calculator')))

        # Check if record already exists for this course
        existing = AttendanceRecord.query.filter_by(
            user_id=current_user.id,
            course_id=form.course_id.data
        ).first()

        if existing:
            existing.total_classes = form.total_classes.data
            existing.attended_classes = form.attended_classes.data
            existing.target_percentage = form.target_percentage.data
            flash('Attendance updated for this course!', 'success')
        else:
            record = AttendanceRecord(
                user_id=current_user.id,
                course_id=form.course_id.data,
                total_classes=form.total_classes.data,
                attended_classes=form.attended_classes.data,
                target_percentage=form.target_percentage.data
            )
            db.session.add(record)
            flash('New course attendance tracked successfully!', 'success')

        db.session.commit()
        return redirect(url_for('attendance_calculator'))

    return render_template(
        'attendance.html',
        title='College Attendance & Bunk Calculator',
        form=form,
        user_records=user_records,
        courses=courses
    )


@app.route('/attendance/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_attendance(record_id):
    """Delete an attendance record."""
    record = AttendanceRecord.query.get_or_404(record_id)
    if record.user_id != current_user.id:
        abort(403)
    db.session.delete(record)
    db.session.commit()
    flash('Attendance record removed.', 'info')
    return redirect(url_for('attendance_calculator'))


# ==========================================
# Database Auto-seed & App Runner
# ==========================================

def init_db():
    """Ensure database schema is created and populated with demo courses."""
    with app.app_context():
        db.create_all()
        if Course.query.count() == 0:
            sample_courses = [
                Course(
                    name="Database Management Systems",
                    code="CSE-301",
                    section="A",
                    semester=5,
                    instructor="Dr. R. Sharma",
                    room="Room 304 (Block B)",
                    schedule="Mon, Wed, Fri (10:00 AM - 11:00 AM)",
                    status="Scheduled"
                ),
                Course(
                    name="Operating Systems",
                    code="CSE-302",
                    section="A",
                    semester=5,
                    instructor="Prof. Anjali Verma",
                    room="Lecture Theater 2",
                    schedule="Tue, Thu (11:30 AM - 1:00 PM)",
                    status="Scheduled"
                ),
                Course(
                    name="Data Structures & Algorithms",
                    code="CSE-201",
                    section="B",
                    semester=3,
                    instructor="Dr. Vikram Patel",
                    room="Computer Lab 1",
                    schedule="Mon, Wed (02:00 PM - 03:30 PM)",
                    status="Scheduled"
                ),
                Course(
                    name="Computer Networks",
                    code="CSE-303",
                    section="A",
                    semester=5,
                    instructor="Prof. Sneha Kulkarni",
                    room="Room 201 (Block A)",
                    schedule="Tue, Fri (09:00 AM - 10:30 AM)",
                    status="Scheduled"
                ),
                Course(
                    name="Software Engineering",
                    code="CSE-401",
                    section="C",
                    semester=7,
                    instructor="Dr. Arvind Gupta",
                    room="Seminar Hall 3",
                    schedule="Thu, Fri (03:30 PM - 05:00 PM)",
                    status="Scheduled"
                )
            ]
            db.session.add_all(sample_courses)
            db.session.commit()
            print("Auto-seeded default courses.")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
