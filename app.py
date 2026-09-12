import os
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env if present (skip if TESTING mode is set)
if not os.environ.get('TESTING'):
    load_dotenv(override=True)

from functools import wraps
import csv
import io

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort, send_from_directory, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import (
    db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord,
    Deadline, Resource, CRAssignment, Report, AuditLog, FeatureFlag, SystemSetting
)
from forms import (
    RegistrationForm, LoginForm, SummaryForm, ChatMessageForm,
    AnnouncementForm, AttendanceForm, DeadlineForm, ResourceForm, CourseForm,
    OnboardingForm, ReportForm, AdminUserEditForm, CRAssignmentForm,
    BulkCourseImportForm, SystemSettingsForm
)

# Initialize Flask application
app = Flask(__name__)

# Application Configuration (Supabase / Neon PostgreSQL / SQLite fallback)
raw_db_url = os.environ.get('DATABASE_URL', 'sqlite:///classcatch.db')
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'classcatch-secret-key-2026-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = raw_db_url
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
    return db.session.get(User, int(user_id))


# ==========================================
# Operational Helpers & Access Control
# ==========================================

def is_feature_enabled(key):
    """Check whether a system feature flag is active."""
    try:
        flag = FeatureFlag.query.filter_by(key=key).first()
        return flag.is_enabled if flag else True
    except Exception:
        return True


def get_system_setting(key, default=None):
    """Fetch global configuration setting."""
    try:
        setting = SystemSetting.query.filter_by(key=key).first()
        return setting.value if setting else default
    except Exception:
        return default


def log_audit(action, target_type=None, target_id=None, details=None):
    """Log an operational audit action for administrative tracking."""
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        entry = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[AUDIT LOG ERROR] {e}")


def admin_required(f):
    """Decorator to enforce Platform Administrator or SuperAdmin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please sign in with an administrator account.', 'warning')
            return redirect(url_for('login', next=request.path))
        if not current_user.is_admin():
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def superadmin_required(f):
    """Decorator to enforce Super Administrator privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin():
            flash('Access denied. Super Administrator privileges required.', 'danger')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def check_maintenance_and_suspension():
    """Enforce account suspensions and platform maintenance mode."""
    # Enforce suspended status
    if current_user.is_authenticated and getattr(current_user, 'is_suspended', False):
        logout_user()
        flash('Your account has been suspended by administration. Please contact campus support.', 'danger')
        return redirect(url_for('login'))

    # Check maintenance mode
    m_mode = get_system_setting('maintenance_mode', 'false')
    if m_mode == 'true':
        exempt_prefixes = ['/static', '/login', '/logout', '/maintenance', '/admin']
        if not any(request.path.startswith(p) for p in exempt_prefixes):
            if not (current_user.is_authenticated and current_user.is_admin()):
                return redirect(url_for('maintenance'))


@app.context_processor
def inject_globals():
    """Inject common utility data, features, and settings into all Jinja templates."""
    all_courses = []
    try:
        all_courses = Course.query.filter_by(is_archived=False).order_by(Course.code).all()
    except Exception:
        pass
    return {
        'today': date.today(),
        'current_year': datetime.now().year,
        'global_courses': all_courses,
        'is_feature_enabled': is_feature_enabled,
        'get_system_setting': get_system_setting
    }


# ==========================================
# Authentication Routes
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new student registration."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # Respect platform registration feature flag
    if get_system_setting('registration_enabled', 'true') == 'false':
        flash('Student registration is temporarily disabled by platform administration.', 'warning')
        return redirect(url_for('login'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role='student',
            is_onboarded=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        log_audit('user.registered', 'user', user.id, f"Registered new account: {user.email}")

        flash('🎉 Welcome to ClassCatch! Your account is created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', title='Join ClassCatch', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle student and administrator login."""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard') if current_user.is_admin() else url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            if user.is_suspended:
                flash('Your account has been suspended by administration. Please contact campus support.', 'danger')
                return render_template('login.html', title='Sign In', form=form)

            login_user(user, remember=form.remember_me.data)
            log_audit('user.login', 'user', user.id, f"Logged in from role: {user.role}")

            flash(f'👋 Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                if user.is_admin():
                    next_page = url_for('admin_dashboard')
                elif not user.is_onboarded and user.role == 'student':
                    next_page = url_for('onboarding')
                else:
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
    - Features Today's Schedule & What's Next Tracker.
    - Highlights upcoming academic deadlines & exam countdowns.
    """
    courses = Course.query.order_by(Course.code).all()
    today_summaries = Summary.query.filter_by(date=date.today()).order_by(Summary.created_at.desc()).all()
    recent_summaries = Summary.query.order_by(Summary.date.desc(), Summary.created_at.desc()).limit(6).all()
    urgent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()

    # Upcoming academic deadlines & exam countdowns
    upcoming_deadlines = Deadline.query.filter_by(is_completed=False).order_by(Deadline.due_date.asc()).limit(4).all()

    # Calculate today's scheduled classes
    today_abbr = date.today().strftime('%a')  # e.g., 'Mon', 'Wed'
    today_day_name = date.today().strftime('%A, %b %d')
    today_classes = [c for c in courses if today_abbr in c.schedule]
    if not today_classes:
        # If weekend or no match, show all active scheduled courses for quick preview
        today_classes = courses[:3]

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
        user_attendance=user_attendance,
        upcoming_deadlines=upcoming_deadlines,
        today_classes=today_classes,
        today_day_name=today_day_name
    )


# ==========================================
# Absence & Catch-Up Engine ("What Did I Miss?")
# ==========================================

@app.route('/catchup')
def catchup_hub():
    """
    Dedicated Absence & Catch-Up Hub:
    Answers the core question: 'I was absent / missed class, what did I miss?'
    Aggregates summaries, assignments, announcements, and resources for any chosen date.
    """
    req_date_str = request.args.get('date')
    req_preset = request.args.get('preset', '')

    today_obj = date.today()
    yesterday_obj = today_obj - timedelta(days=1)

    target_date = yesterday_obj if req_preset == 'yesterday' else today_obj
    if req_date_str:
        try:
            target_date = datetime.strptime(req_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = yesterday_obj

    day_abbr = target_date.strftime('%a')
    day_name = target_date.strftime('%A, %B %d, %Y')

    # 1. Scheduled courses on this day
    all_courses = Course.query.order_by(Course.code).all()
    scheduled_courses = [c for c in all_courses if day_abbr in c.schedule]
    if not scheduled_courses:
        scheduled_courses = all_courses

    # 2. Summaries posted for this target date
    summaries = Summary.query.filter_by(date=target_date).order_by(Summary.created_at.desc()).all()
    summaries_by_course = {s.course_id: s for s in summaries}

    # 3. Deadlines due or assigned
    deadlines_due = Deadline.query.filter_by(due_date=target_date).order_by(Deadline.priority.desc()).all()

    # 4. Announcements posted on this date
    announcements = Announcement.query.filter(
        db.func.date(Announcement.created_at) == target_date
    ).order_by(Announcement.created_at.desc()).all()

    # Catch-up calculation
    covered_count = len(summaries)
    total_classes = len(scheduled_courses)
    catchup_percent = round((covered_count / total_classes) * 100) if total_classes > 0 else 100

    return render_template(
        'catchup.html',
        title=f'Catch Up on {target_date.strftime("%b %d")}',
        target_date=target_date,
        today=today_obj,
        yesterday=yesterday_obj,
        day_name=day_name,
        scheduled_courses=scheduled_courses,
        summaries=summaries,
        summaries_by_course=summaries_by_course,
        deadlines_due=deadlines_due,
        announcements=announcements,
        covered_count=covered_count,
        total_classes=total_classes,
        catchup_percent=catchup_percent
    )


# ==========================================
# Global Search System ("Find Anything")
# ==========================================

@app.route('/search')
def global_search():
    """Global search across courses, topics, notes, deadlines, and resources."""
    query = request.args.get('q', '').strip()
    tab_filter = request.args.get('tab', 'all')

    results = {
        'courses': [],
        'summaries': [],
        'deadlines': [],
        'resources': [],
        'announcements': []
    }

    if query:
        like_q = f'%{query}%'
        results['courses'] = Course.query.filter(
            Course.name.ilike(like_q) |
            Course.code.ilike(like_q) |
            Course.instructor.ilike(like_q) |
            Course.room.ilike(like_q)
        ).limit(10).all()

        results['summaries'] = Summary.query.filter(
            Summary.topic.ilike(like_q) |
            Summary.content.ilike(like_q)
        ).order_by(Summary.date.desc()).limit(15).all()

        results['deadlines'] = Deadline.query.filter(
            Deadline.title.ilike(like_q) |
            Deadline.description.ilike(like_q) |
            Deadline.category.ilike(like_q)
        ).limit(10).all()

        results['resources'] = Resource.query.filter(
            Resource.title.ilike(like_q) |
            Resource.description.ilike(like_q) |
            Resource.category.ilike(like_q)
        ).limit(10).all()

        results['announcements'] = Announcement.query.filter(
            Announcement.title.ilike(like_q) |
            Announcement.content.ilike(like_q)
        ).limit(10).all()

    total_results = sum(len(v) for v in results.values())

    return render_template(
        'search.html',
        title=f"Search: '{query}'" if query else "Search ClassCatch",
        query=query,
        tab_filter=tab_filter,
        results=results,
        total_results=total_results
    )


@app.route('/api/search')
def api_search():
    """Live JSON autocomplete API for global search bar."""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'results': [], 'total': 0})

    like_q = f'%{query}%'
    courses = Course.query.filter(
        Course.name.ilike(like_q) | Course.code.ilike(like_q)
    ).limit(4).all()

    summaries = Summary.query.filter(
        Summary.topic.ilike(like_q) | Summary.content.ilike(like_q)
    ).order_by(Summary.date.desc()).limit(4).all()

    resources = Resource.query.filter(
        Resource.title.ilike(like_q)
    ).limit(4).all()

    items = []
    for c in courses:
        items.append({
            'type': 'Course',
            'title': f"{c.code} - {c.name}",
            'subtitle': f"{c.instructor} · {c.room}",
            'url': url_for('course_detail', course_id=c.id),
            'icon': 'bi-journal-bookmark'
        })
    for s in summaries:
        items.append({
            'type': 'Note',
            'title': s.topic or 'Lecture Note',
            'subtitle': f"{s.course.code} · {s.date.strftime('%b %d')}",
            'url': url_for('summary_detail', summary_id=s.id),
            'icon': 'bi-file-earmark-text'
        })
    for r in resources:
        items.append({
            'type': 'Resource',
            'title': r.title,
            'subtitle': f"{r.category} · {r.course.code}",
            'url': url_for('resources_list'),
            'icon': 'bi-file-earmark-pdf'
        })

    return jsonify({'results': items, 'total': len(items)})


# ==========================================
# Course Hub (Tabs: Summaries, Chat, Announcements, Schedule)
# ==========================================

@app.route('/course/new', methods=['GET', 'POST'])
@login_required
def create_course():
    """Create a new course/subject for the student's branch/semester."""
    form = CourseForm()
    if form.validate_on_submit():
        existing = Course.query.filter_by(code=form.code.data.strip().upper()).first()
        if existing:
            flash(f"A course with code '{existing.code}' ({existing.name}) already exists.", 'warning')
            return render_template('course_new.html', title='Add Subject / Course', form=form)

        new_course = Course(
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            section=form.section.data.strip() if form.section.data else 'A',
            semester=form.semester.data,
            instructor=form.instructor.data.strip() if form.instructor.data else 'Prof. TBA',
            room=form.room.data.strip() if form.room.data else 'Lecture Hall',
            schedule=form.schedule.data.strip() if form.schedule.data else 'Mon, Wed, Fri 10:00 AM',
            status='Scheduled'
        )
        db.session.add(new_course)
        db.session.commit()
        if hasattr(current_user, 'karma'):
            current_user.karma += 15
            db.session.commit()
        flash(f"Subject '{new_course.code} - {new_course.name}' created successfully! (+15 Karma)", 'success')
        return redirect(url_for('course_detail', course_id=new_course.id))

    return render_template('course_new.html', title='Add Subject / Course', form=form)


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
            category=form.category.data,
            is_anonymous=bool(form.is_anonymous.data)
        )
        db.session.add(chat)
        db.session.commit()
        msg_type = "Anonymous doubt/message" if chat.is_anonymous else "Message"
        flash(f'{msg_type} sent to class chat!', 'info')
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
        # Award karma to contributor (+15 Karma)
        current_user.karma = (current_user.karma or 50) + 15
        db.session.commit()

        flash('✅ Catch-up summary submitted successfully! (+15 Karma awarded)', 'success')
        return redirect(url_for('course_detail', course_id=summary.course_id, tab='summaries'))

    return render_template('post_summary.html', title='Post Class Catch-up', form=form)


@app.route('/summary/<int:summary_id>')
def summary_detail(summary_id):
    """Detailed standalone view of an individual catch-up note."""
    summary = Summary.query.get_or_404(summary_id)
    return render_template('summary_detail.html', title=f"Note: {summary.course.code}", summary=summary)


@app.route('/summary/<int:summary_id>/helpful', methods=['POST'])
def mark_helpful(summary_id):
    """Upvote / mark a summary as helpful and award karma."""
    summary = Summary.query.get_or_404(summary_id)
    summary.helpful_count += 1
    if summary.author:
        summary.author.karma = (summary.author.karma or 50) + 5
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'helpful_count': summary.helpful_count})

    flash('Marked as helpful! (+5 Karma awarded to peer)', 'success')
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

    # Campus MVP Leaderboard
    top_contributors = User.query.order_by(User.karma.desc()).limit(5).all()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please log in to chat in the Campus Lounge.', 'warning')
            return redirect(url_for('login', next=url_for('lounge')))

        chat = ChatMessage(
            course_id=None,
            user_id=current_user.id,
            message=form.message.data.strip(),
            category=form.category.data,
            is_anonymous=bool(form.is_anonymous.data)
        )
        db.session.add(chat)
        # Small karma for helping out in lounge
        current_user.karma = (current_user.karma or 50) + 2
        db.session.commit()
        msg_type = "Anonymous post" if chat.is_anonymous else "Requirement / message"
        flash(f'{msg_type} posted to Campus Lounge!', 'success')
        return redirect(url_for('lounge'))

    return render_template(
        'lounge.html',
        title='Campus Lounge & Requirements',
        form=form,
        messages=messages,
        category_filter=category_filter,
        top_contributors=top_contributors
    )


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


@app.route('/attendance/<int:record_id>/log', methods=['POST'])
@login_required
def log_attendance_action(record_id):
    """
    1-tap instant attendance logger:
    Allows student to record '+1 Attended' or '+1 Missed' in one tap without a form.
    """
    record = AttendanceRecord.query.get_or_404(record_id)
    if record.user_id != current_user.id:
        flash('Unauthorized access to attendance record.', 'danger')
        return redirect(url_for('attendance_calculator'))

    status = request.args.get('status', 'present')
    if status == 'present':
        record.attended_classes += 1
        record.total_classes += 1
        db.session.commit()
        flash(f'✅ Present logged for {record.course.code}! Attendance is now {record.current_percentage}%.', 'success')
    elif status == 'absent':
        record.total_classes += 1
        db.session.commit()
        flash(f'⚠️ Missed class logged for {record.course.code}. Attendance is now {record.current_percentage}%.', 'warning')

    return redirect(url_for('attendance_calculator'))


@app.route('/attendance/<int:record_id>/target', methods=['POST'])
@login_required
def update_attendance_target(record_id):
    """Update custom attendance threshold target (e.g. 75% -> 80%)."""
    record = AttendanceRecord.query.get_or_404(record_id)
    if record.user_id != current_user.id:
        abort(403)

    try:
        new_target = float(request.form.get('target', 75.0))
        if 50.0 <= new_target <= 100.0:
            record.target_percentage = new_target
            db.session.commit()
            flash(f'Attendance target for {record.course.code} set to {new_target}%.', 'info')
    except ValueError:
        flash('Invalid target percentage value.', 'warning')

    return redirect(url_for('attendance_calculator'))


# ==========================================
# Academic Deadlines & Exam Countdown Tracker
# ==========================================

@app.route('/deadlines')
def deadlines_list():
    """View and filter upcoming assignments, lab viva, quizzes, and exams."""
    filter_cat = request.args.get('category', 'All')
    course_id = request.args.get('course_id', type=int)

    query = Deadline.query
    if filter_cat != 'All':
        query = query.filter_by(category=filter_cat)
    if course_id:
        query = query.filter_by(course_id=course_id)

    deadlines = query.order_by(Deadline.is_completed.asc(), Deadline.due_date.asc()).all()
    courses = Course.query.order_by(Course.code).all()
    return render_template(
        'deadlines.html',
        title='Academic Deadlines & Exam Countdown',
        deadlines=deadlines,
        courses=courses,
        filter_cat=filter_cat,
        selected_course_id=course_id
    )


@app.route('/deadlines/new', methods=['GET', 'POST'])
@login_required
def new_deadline():
    """Add a new assignment deadline or exam date."""
    courses = Course.query.order_by(Course.code).all()
    form = DeadlineForm()
    form.course_id.choices = [(c.id, f"{c.code} - {c.name}") for c in courses]

    if form.validate_on_submit():
        deadline = Deadline(
            course_id=form.course_id.data,
            user_id=current_user.id,
            title=form.title.data.strip(),
            due_date=form.due_date.data,
            category=form.category.data,
            priority=form.priority.data,
            description=form.description.data.strip() if form.description.data else None
        )
        db.session.add(deadline)
        current_user.karma = (current_user.karma or 50) + 10
        db.session.commit()
        flash('⏰ Deadline added to the calendar! (+10 Karma awarded)', 'success')
        return redirect(url_for('deadlines_list'))

    return render_template('deadline_new.html', title='Add Deadline / Exam Alert', form=form)


@app.route('/deadlines/<int:deadline_id>/toggle', methods=['POST'])
@login_required
def toggle_deadline(deadline_id):
    """Toggle deadline completed status."""
    deadline = Deadline.query.get_or_404(deadline_id)
    deadline.is_completed = not deadline.is_completed
    db.session.commit()
    status_text = "completed" if deadline.is_completed else "marked active"
    flash(f'Deadline marked as {status_text}.', 'info')
    return redirect(request.referrer or url_for('deadlines_list'))


@app.route('/deadlines/<int:deadline_id>/delete', methods=['POST'])
@login_required
def delete_deadline(deadline_id):
    """Delete a deadline."""
    deadline = Deadline.query.get_or_404(deadline_id)
    if deadline.user_id != current_user.id and current_user.role != 'admin':
        abort(403)
    db.session.delete(deadline)
    db.session.commit()
    flash('Deadline removed.', 'info')
    return redirect(url_for('deadlines_list'))


# ==========================================
# PYQ & Academic Resource Vault
# ==========================================

@app.route('/resources')
def resources_list():
    """Browse and search past exam papers (PYQs), formula sheets, and lab guides."""
    category_filter = request.args.get('category', 'All')
    course_id = request.args.get('course_id', type=int)
    search_query = request.args.get('q', '').strip()

    query = Resource.query
    if category_filter != 'All':
        query = query.filter_by(category=category_filter)
    if course_id:
        query = query.filter_by(course_id=course_id)
    if search_query:
        query = query.filter(
            (Resource.title.ilike(f"%{search_query}%")) |
            (Resource.description.ilike(f"%{search_query}%"))
        )

    resources = query.order_by(Resource.helpful_count.desc(), Resource.created_at.desc()).all()
    courses = Course.query.order_by(Course.code).all()
    return render_template(
        'resources.html',
        title='Academic Vault - PYQs & Formula Sheets',
        resources=resources,
        courses=courses,
        category_filter=category_filter,
        selected_course_id=course_id,
        search_query=search_query
    )


@app.route('/resources/new', methods=['GET', 'POST'])
@login_required
def new_resource():
    """Publish a study material or PYQ link."""
    courses = Course.query.order_by(Course.code).all()
    form = ResourceForm()
    form.course_id.choices = [(c.id, f"{c.code} - {c.name}") for c in courses]

    if form.validate_on_submit():
        resource = Resource(
            course_id=form.course_id.data,
            user_id=current_user.id,
            title=form.title.data.strip(),
            category=form.category.data,
            resource_url=form.resource_url.data.strip(),
            description=form.description.data.strip() if form.description.data else None
        )
        db.session.add(resource)
        current_user.karma = (current_user.karma or 50) + 10
        db.session.commit()
        flash('📚 Resource published to the academic vault! (+10 Karma awarded)', 'success')
        return redirect(url_for('resources_list'))

    return render_template('resource_new.html', title='Share Study Resource', form=form)


@app.route('/resources/<int:resource_id>/helpful', methods=['POST'])
def mark_resource_helpful(resource_id):
    """Upvote a study resource and award karma."""
    resource = Resource.query.get_or_404(resource_id)
    resource.helpful_count += 1
    if resource.author:
        resource.author.karma = (resource.author.karma or 50) + 5
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'helpful_count': resource.helpful_count})

    flash('Marked resource as helpful! (+5 Karma to contributor)', 'success')
    return redirect(request.referrer or url_for('resources_list'))


# ==========================================
# AI Smart Note Beautifier / Summarizer API
# ==========================================

@app.route('/api/ai-summarize', methods=['POST'])
def ai_summarize_note():
    """
    Client-side AI assistant helper to turn rough class notes or bullet points
    into clean, formatted notes with key takeaways, formulas, and homework items.
    """
    data = request.get_json() or {}
    raw_text = data.get('text', '').strip()
    topic = data.get('topic', 'Class Recap').strip()

    if not raw_text:
        return jsonify({'error': 'No text provided'}), 400

    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    takeaways = []
    homework = []
    tips = []

    for line in lines:
        lower = line.lower()
        if any(w in lower for w in ['hw', 'homework', 'assignment', 'submit', 'due', 'problem']):
            homework.append(line)
        elif any(w in lower for w in ['imp', 'exam', 'quiz', 'formula', 'test', 'note', 'remember', 'viva', 'theory']):
            tips.append(line)
        else:
            takeaways.append(line)

    formatted = f"### 📌 Core Topic: {topic}\n\n"
    formatted += "#### 💡 Key Concepts & Takeaways Covered:\n"
    if takeaways:
        for t in takeaways:
            clean_t = t.lstrip('-*• ')
            formatted += f"- {clean_t}\n"
    else:
        formatted += "- Comprehensive lecture concepts covered and key examples solved.\n"

    if homework:
        formatted += "\n#### 📝 Homework & Action Items:\n"
        for h in homework:
            clean_h = h.lstrip('-*• ')
            formatted += f"- [ ] {clean_h}\n"

    if tips:
        formatted += "\n#### ⚠️ Important Exam & Viva Tips:\n"
        for tip in tips:
            clean_tip = tip.lstrip('-*• ')
            formatted += f"> **Crucial Point:** {clean_tip}\n"

    return jsonify({
        'success': True,
        'formatted': formatted,
        'word_count': len(formatted.split())
    })


@app.route('/summary/<int:summary_id>/verify', methods=['POST'])
@login_required
def verify_summary(summary_id):
    """
    CR / Faculty Verification Seal:
    Allows authorized Class Representatives or Instructors to mark lecture notes as 'Verified Accurate'.
    Awards +20 Karma to the student author.
    """
    summary = Summary.query.get_or_404(summary_id)

    # Authorization check: Only CRs, Instructors, or Admins can verify
    if getattr(current_user, 'role', 'student') not in ['cr', 'instructor', 'admin']:
        flash('🔒 Access Denied: Only Class Representatives (CR) or Faculty can verify lecture notes.', 'danger')
        return redirect(request.referrer or url_for('summary_detail', summary_id=summary.id))

    # Anti-Farming check: Author cannot verify their own note
    if summary.user_id == current_user.id:
        flash('⚠️ Integrity Check: You cannot verify your own submitted notes to award yourself Karma.', 'warning')
        return redirect(request.referrer or url_for('summary_detail', summary_id=summary.id))

    summary.is_verified = not summary.is_verified
    if summary.is_verified:
        role_label = 'Class Representative' if current_user.role == 'cr' else current_user.role.title()
        summary.verified_by = f"{current_user.name} ({role_label})"
        if summary.author:
            summary.author.karma = (summary.author.karma or 50) + 20
        flash(f'✅ Lecture note officially verified by {summary.verified_by}! (+20 Karma awarded to author)', 'success')
    else:
        summary.verified_by = None
        flash('Verification seal removed.', 'info')

    db.session.commit()
    return redirect(request.referrer or url_for('summary_detail', summary_id=summary.id))


@app.route('/api/scan-whiteboard', methods=['POST'])
def scan_whiteboard():
    """
    Simulated whiteboard & handwritten notebook OCR engine.
    Analyzes an uploaded photo of a classroom whiteboard or notebook page,
    and extracts formatted markdown lecture notes with equations, headings, and homework.
    """
    course_name = request.form.get('course', 'Lecture Notes')
    
    # Check if a file was uploaded
    file = request.files.get('file')
    filename = file.filename if file else 'whiteboard_scan.jpg'

    # Simulated intelligent OCR extraction from classroom blackboard
    simulated_ocr_notes = f"""### 📸 Scanned Lecture Board Note: {course_name}
> *Extracted from image: {filename} via ClassCatch OCR Vision Engine*

#### 📌 Topics & Equations from Board:
- Core Concept: Algorithmic time complexity and recurrence relations.
- $T(n) = 2T(n/2) + O(n) \\implies O(n \\log n)$ via Master Theorem.
- Key Lemma: Optimal substructure property applies to dynamic programming.

#### 💡 Whiteboard Diagram & Summary:
1. Divide Phase: Split input array into equal halves.
2. Conquer Phase: Recursively sort each subarray.
3. Combine Phase: Merge two sorted runs in linear $O(n)$ time.

#### 📝 Board Assignment / Homework:
- [ ] Implement Merge Sort with custom comparator.
- [ ] Solve Exercise 3.4 from textbook before Thursday.
- [ ] Prepare for surprise viva on space complexity!"""

    return jsonify({
        'success': True,
        'text': simulated_ocr_notes,
        'message': 'Whiteboard successfully transcribed into structured notes!'
    })


@app.route('/api/save-whiteboard-note', methods=['POST'])
@login_required
def save_whiteboard_note():
    """
    Directly saves an AI-transcribed whiteboard note into the database as a lecture summary.
    """
    data = request.get_json() or {}
    course_id = data.get('course_id')
    topic = data.get('topic', 'Classroom Whiteboard Notes')
    content = data.get('content', '')
    date_str = data.get('date')

    if not course_id or not content:
        return jsonify({'success': False, 'message': 'Course and content are required.'}), 400

    note_date = date.today()
    if date_str:
        try:
            note_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    summary = Summary(
        course_id=int(course_id),
        user_id=current_user.id,
        date=note_date,
        topic=topic,
        category='Lecture Notes',
        content=content
    )
    db.session.add(summary)
    current_user.karma = (current_user.karma or 50) + 15
    db.session.commit()

    return jsonify({
        'success': True,
        'summary_id': summary.id,
        'redirect_url': url_for('summary_detail', summary_id=summary.id),
        'message': 'Whiteboard note successfully saved to course feed! (+15 Karma)'
    })


@app.route('/api/morning-dispatch')
@login_required
def morning_dispatch():
    """
    Morning WhatsApp / Telegram Dispatch Bot Simulator:
    Generates a personalized daily student briefing with today's timetable,
    room numbers, and attendance risk alerts.
    """
    today_abbr = date.today().strftime('%a')
    today_name = date.today().strftime('%A, %b %d')
    all_courses = Course.query.all()
    today_classes = [c for c in all_courses if today_abbr in c.schedule] or all_courses[:3]

    # Check attendance risk
    attendance_records = AttendanceRecord.query.filter_by(user_id=current_user.id).all()
    at_risk_courses = [r for r in attendance_records if r.current_percentage < 75.0]

    dispatch_text = f"☀️ *Good Morning, {current_user.name.split()[0]}! Here is your ClassCatch Daily Briefing:*\n\n"
    dispatch_text += f"📅 *Date:* {today_name}\n"
    dispatch_text += f"📚 *Today's Lectures ({len(today_classes)} classes):*\n"

    for idx, c in enumerate(today_classes, 1):
        dispatch_text += f"  {idx}. *{c.code}* - {c.name}\n"
        dispatch_text += f"     📍 {c.room} | ⏰ {c.schedule} | 👨‍🏫 {c.instructor}\n"

    if at_risk_courses:
        dispatch_text += "\n🚨 *CRITICAL ATTENDANCE ALERT:*\n"
        for r in at_risk_courses:
            dispatch_text += f"  ⚠️ *{r.course.code}*: Attendance at *{r.current_percentage}%* (< 75%). You must attend *{r.classes_needed}* consecutive classes to recover!\n"
    else:
        dispatch_text += "\n✅ *Attendance Safe:* All your tracked courses are currently >= 75%. Keep it up!\n"

    dispatch_text += f"\n🏆 *Your Karma Score:* {current_user.karma} ({current_user.badge['name']})\n"
    dispatch_text += "💬 *Check missed lecture notes:* http://classcatch.edu"

    return jsonify({
        'success': True,
        'dispatch': dispatch_text,
        'classes_count': len(today_classes),
        'at_risk_count': len(at_risk_courses)
    })


# ==========================================
# Google Play Store & PWA TWA Compliance Routes
# ==========================================

@app.route('/.well-known/assetlinks.json')
def assetlinks():
    """
    Digital Asset Links for Android Trusted Web Activity (TWA).
    Enables Play Store app to run full-screen without Chrome address bar.
    """
    package_name = os.environ.get('ANDROID_PACKAGE_NAME', 'com.classcatch.app')
    sha256_fingerprint = os.environ.get(
        'ANDROID_SHA256_FINGERPRINT',
        '14:6D:E9:7F:0F:7B:64:99:90:57:95:56:56:56:4C:E6:36:9C:A4:A5:6B:7F:2E:39:69:B3:68:5F:B6:58:24:99'
    )
    data = [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": package_name,
            "sha256_cert_fingerprints": [sha256_fingerprint]
        }
    }]
    return jsonify(data)


@app.route('/privacy')
def privacy_policy():
    """Google Play Store mandated Privacy Policy page."""
    return render_template('privacy.html', title='Privacy Policy - ClassCatch')


@app.route('/terms')
def terms_of_service():
    """Terms of Service page."""
    return render_template('terms.html', title='Terms of Service - ClassCatch')


@app.route('/offline')
def offline():
    """PWA offline fallback screen when network drops in lecture hall."""
    return render_template('offline.html', title='Offline Mode - ClassCatch')


# ==========================================
# Student Onboarding & Content Reporting
# ==========================================

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    """First-time student profile setup (university, program, semester, section)."""
    form = OnboardingForm()
    if request.method == 'GET':
        form.college.data = current_user.college or 'GLA University'
        form.program.data = current_user.program or 'B.Tech CSE'
        form.semester.data = current_user.semester or 5
        form.section.data = current_user.section or 'A'

    if form.validate_on_submit():
        current_user.college = form.college.data.strip()
        current_user.program = form.program.data.strip()
        current_user.semester = form.semester.data
        current_user.section = form.section.data.strip().upper()
        current_user.is_onboarded = True
        db.session.commit()
        log_audit('user.onboarded', 'user', current_user.id, f"Program: {current_user.program}, Sec: {current_user.section}")
        flash('🚀 Academic workspace ready! Welcome to ClassCatch.', 'success')
        return redirect(url_for('index'))

    return render_template('onboarding.html', title='Welcome to ClassCatch - Quick Setup', form=form)


@app.route('/onboarding/skip')
@login_required
def onboarding_skip():
    """Allow student to skip onboarding and jump straight to lectures."""
    current_user.is_onboarded = True
    db.session.commit()
    flash('You can customize your campus profile anytime from settings.', 'info')
    return redirect(url_for('index'))


@app.route('/report', methods=['POST'])
@login_required
def submit_report():
    """Submit a moderation report against spam, incorrect notes, or inappropriate content."""
    target_type = request.form.get('target_type') or (request.json and request.json.get('target_type'))
    target_id = request.form.get('target_id') or (request.json and request.json.get('target_id'))
    category = request.form.get('category') or (request.json and request.json.get('category')) or 'Other'
    reason = request.form.get('reason') or (request.json and request.json.get('reason')) or ''

    if not target_type or not target_id or not reason:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Missing required report fields.'}), 400
        flash('Please provide a reason for reporting this content.', 'warning')
        return redirect(request.referrer or url_for('index'))

    report = Report(
        reporter_id=current_user.id,
        target_type=target_type,
        target_id=int(target_id),
        category=category,
        reason=reason.strip(),
        status='Open'
    )
    db.session.add(report)
    db.session.commit()
    log_audit('report.submitted', 'report', report.id, f"Category: {category}, Target: {target_type}#{target_id}")

    if request.is_json:
        return jsonify({'success': True, 'message': 'Report submitted for review.'})
    flash('🛡️ Thank you for keeping ClassCatch safe. Our moderation team has received your report.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/maintenance')
def maintenance():
    """Maintenance splash display when administrator enables maintenance mode."""
    return render_template('maintenance.html', title='System Maintenance - ClassCatch')


# ==========================================
# Admin Control Center (/admin)
# ==========================================

@app.route('/admin')
@admin_required
def admin_dashboard():
    """ClassCatch Admin Control Center overview dashboard."""
    stats = {
        'total_users': User.query.count(),
        'students': User.query.filter_by(role='student').count(),
        'crs': User.query.filter_by(role='cr').count(),
        'admins': User.query.filter(User.role.in_(['admin', 'superadmin'])).count(),
        'courses': Course.query.filter_by(is_archived=False).count(),
        'archived_courses': Course.query.filter_by(is_archived=True).count(),
        'summaries': Summary.query.count(),
        'resources': Resource.query.count(),
        'pending_resources': Resource.query.filter_by(status='Pending Review').count(),
        'open_reports': Report.query.filter_by(status='Open').count(),
        'deadlines': Deadline.query.count(),
        'chat_messages': ChatMessage.query.count()
    }
    recent_audits = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    open_reports = Report.query.filter_by(status='Open').order_by(Report.created_at.desc()).limit(5).all()
    pending_resources = Resource.query.filter_by(status='Pending Review').order_by(Resource.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        title='Admin Control Center',
        stats=stats,
        recent_audits=recent_audits,
        open_reports=open_reports,
        pending_resources=pending_resources
    )


@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management view."""
    role_filter = request.args.get('role', '')
    query = request.args.get('q', '').strip()

    users_query = User.query
    if role_filter:
        users_query = users_query.filter_by(role=role_filter)
    if query:
        search_pattern = f"%{query}%"
        users_query = users_query.filter(
            (User.name.ilike(search_pattern)) | (User.email.ilike(search_pattern))
        )
    users = users_query.order_by(User.id.asc()).all()
    return render_template('admin/users.html', title='User Management', users=users, role_filter=role_filter, query=query)


@app.route('/admin/users/<int:user_id>/role', methods=['POST'])
@admin_required
def admin_change_user_role(user_id):
    """Change user role (student, cr, admin, superadmin)."""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    new_role = request.form.get('role', 'student')
    if new_role not in ['student', 'cr', 'admin', 'superadmin']:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin_users'))

    if (new_role == 'superadmin' or user.role == 'superadmin') and not current_user.is_superadmin():
        flash('Only Super Administrators can assign or modify SuperAdmin roles.', 'danger')
        return redirect(url_for('admin_users'))

    old_role = user.role
    user.role = new_role
    db.session.commit()
    log_audit('user.role_change', 'user', user.id, f"Changed role from {old_role} to {new_role}")
    flash(f"Updated role for {user.name} to {new_role.upper()}.", 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/toggle-suspend', methods=['POST'])
@admin_required
def admin_toggle_suspend_user(user_id):
    """Suspend or unsuspend a user account."""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == current_user.id:
        flash('You cannot suspend your own account.', 'warning')
        return redirect(url_for('admin_users'))
    if user.is_superadmin() and not current_user.is_superadmin():
        flash('Cannot suspend a Super Administrator.', 'danger')
        return redirect(url_for('admin_users'))

    user.is_suspended = not user.is_suspended
    db.session.commit()
    action = 'user.suspended' if user.is_suspended else 'user.unsuspended'
    log_audit(action, 'user', user.id, f"Account status set to {'SUSPENDED' if user.is_suspended else 'ACTIVE'}")
    flash(f"User {user.name} is now {'suspended' if user.is_suspended else 'active'}.", 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/courses')
@admin_required
def admin_courses():
    """Admin courses management."""
    show_archived = request.args.get('archived', '0') == '1'
    courses = Course.query.filter_by(is_archived=show_archived).order_by(Course.code.asc()).all()
    form = CourseForm()
    return render_template('admin/courses.html', title='Course Management', courses=courses, form=form, show_archived=show_archived)


@app.route('/admin/courses/new', methods=['POST'])
@admin_required
def admin_course_new():
    """Create new official course from admin panel."""
    form = CourseForm()
    if form.validate_on_submit():
        course = Course(
            name=form.name.data.strip(),
            code=form.code.data.strip().upper(),
            section=form.section.data.strip().upper() if form.section.data else 'A',
            semester=form.semester.data,
            instructor=form.instructor.data.strip() if form.instructor.data else 'Prof. TBD',
            room=form.room.data.strip() if form.room.data else 'Lecture Hall',
            schedule=form.schedule.data.strip() if form.schedule.data else 'TBD',
            status='Scheduled'
        )
        db.session.add(course)
        db.session.commit()
        log_audit('course.created', 'course', course.id, f"Created {course.code} - {course.name}")
        flash(f'Course {course.code} successfully created.', 'success')
    else:
        for err in form.errors.values():
            flash(f"Error: {err[0]}", 'danger')
    return redirect(url_for('admin_courses'))


@app.route('/admin/courses/<int:course_id>/toggle-archive', methods=['POST'])
@admin_required
def admin_course_toggle_archive(course_id):
    """Archive or restore a course."""
    course = db.session.get(Course, course_id)
    if not course:
        abort(404)
    course.is_archived = not course.is_archived
    db.session.commit()
    log_audit('course.archived' if course.is_archived else 'course.restored', 'course', course.id)
    flash(f"Course {course.code} has been {'archived' if course.is_archived else 'restored'}.", 'info')
    return redirect(url_for('admin_courses', archived=1 if course.is_archived else 0))


@app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
@superadmin_required
def admin_course_delete(course_id):
    """Permanently delete a course (SuperAdmin only)."""
    course = db.session.get(Course, course_id)
    if not course:
        abort(404)
    code = course.code
    db.session.delete(course)
    db.session.commit()
    log_audit('course.deleted', 'course', course_id, f"Deleted {code}")
    flash(f'Course {code} permanently removed.', 'warning')
    return redirect(url_for('admin_courses'))


@app.route('/admin/courses/import', methods=['GET', 'POST'])
@admin_required
def admin_course_import():
    """Bulk import courses from CSV data with validation and preview."""
    form = BulkCourseImportForm()
    parsed_courses = []
    errors = []

    if request.method == 'POST':
        csv_text = form.csv_data.data or request.form.get('csv_data', '')
        action = request.form.get('action', 'preview')

        if not csv_text.strip():
            flash('Please paste valid CSV data.', 'warning')
            return render_template('admin/course_import.html', title='Bulk Course Import', form=form, parsed_courses=[], errors=['Empty CSV payload'])

        f = io.StringIO(csv_text.strip())
        reader = csv.DictReader(f)
        row_num = 1
        for row in reader:
            row_num += 1
            code = (row.get('code') or '').strip().upper()
            name = (row.get('name') or '').strip()
            if not code or not name:
                errors.append(f"Row {row_num}: Missing required code or name.")
                continue
            try:
                sem = int(row.get('semester') or 1)
            except ValueError:
                sem = 1
            parsed_courses.append({
                'code': code,
                'name': name,
                'section': (row.get('section') or 'A').strip().upper(),
                'semester': sem,
                'instructor': (row.get('instructor') or 'Prof. TBD').strip(),
                'room': (row.get('room') or 'Lecture Hall').strip(),
                'schedule': (row.get('schedule') or 'TBD').strip()
            })

        if action == 'commit' and not errors and parsed_courses:
            added_count = 0
            for item in parsed_courses:
                course = Course(
                    code=item['code'],
                    name=item['name'],
                    section=item['section'],
                    semester=item['semester'],
                    instructor=item['instructor'],
                    room=item['room'],
                    schedule=item['schedule'],
                    status='Scheduled'
                )
                db.session.add(course)
                added_count += 1
            db.session.commit()
            log_audit('courses.bulk_imported', 'course', None, f"Imported {added_count} courses via CSV")
            flash(f"🎉 Successfully imported {added_count} courses!", 'success')
            return redirect(url_for('admin_courses'))

    return render_template('admin/course_import.html', title='Bulk Course Import', form=form, parsed_courses=parsed_courses, errors=errors)


@app.route('/admin/cr')
@admin_required
def admin_cr():
    """Admin Class Representative (CR) management."""
    assignments = CRAssignment.query.order_by(CRAssignment.created_at.desc()).all()
    students = User.query.filter(User.role.in_(['student', 'cr'])).order_by(User.name).all()
    courses = Course.query.filter_by(is_archived=False).order_by(Course.code).all()
    return render_template('admin/cr_management.html', title='CR Management', assignments=assignments, students=students, courses=courses)


@app.route('/admin/cr/assign', methods=['POST'])
@admin_required
def admin_cr_assign():
    """Assign a student as CR to a course/section."""
    user_id = request.form.get('user_id', type=int)
    course_id = request.form.get('course_id', type=int)
    section = (request.form.get('section') or 'A').strip().upper()

    user = db.session.get(User, user_id)
    course = db.session.get(Course, course_id)
    if not user or not course:
        flash('Invalid student or course selected.', 'danger')
        return redirect(url_for('admin_cr'))

    existing = CRAssignment.query.filter_by(user_id=user.id, course_id=course.id, section=section).first()
    if existing:
        flash(f"{user.name} is already assigned as CR for {course.code} Sec {section}.", 'info')
        return redirect(url_for('admin_cr'))

    assignment = CRAssignment(
        user_id=user.id,
        course_id=course.id,
        section=section,
        assigned_by_id=current_user.id
    )
    user.role = 'cr'
    db.session.add(assignment)
    db.session.commit()
    log_audit('cr.assigned', 'cr_assignment', assignment.id, f"Assigned {user.name} to {course.code} (Sec {section})")
    flash(f"Designated {user.name} as Class Representative for {course.code} (Sec {section}).", 'success')
    return redirect(url_for('admin_cr'))


@app.route('/admin/cr/<int:assignment_id>/remove', methods=['POST'])
@admin_required
def admin_cr_remove(assignment_id):
    """Revoke a CR assignment."""
    assignment = db.session.get(CRAssignment, assignment_id)
    if not assignment:
        abort(404)
    user = assignment.user
    course = assignment.course
    db.session.delete(assignment)
    db.session.commit()

    remaining = CRAssignment.query.filter_by(user_id=user.id).count()
    if remaining == 0 and user.role == 'cr':
        user.role = 'student'
        db.session.commit()

    log_audit('cr.revoked', 'cr_assignment', assignment_id, f"Revoked CR for {user.name} from {course.code}")
    flash(f"Revoked CR authority from {user.name}.", 'info')
    return redirect(url_for('admin_cr'))


@app.route('/admin/resources')
@admin_required
def admin_resources():
    """Admin Resource Vault moderation."""
    status_filter = request.args.get('status', 'Pending Review')
    resources_query = Resource.query
    if status_filter != 'ALL':
        resources_query = resources_query.filter_by(status=status_filter)
    resources = resources_query.order_by(Resource.created_at.desc()).all()
    return render_template('admin/resources.html', title='Resource Moderation', resources=resources, status_filter=status_filter)


@app.route('/admin/resources/<int:resource_id>/approve', methods=['POST'])
@admin_required
def admin_resource_approve(resource_id):
    """Approve a student uploaded resource."""
    resource = db.session.get(Resource, resource_id)
    if not resource:
        abort(404)
    resource.status = 'Approved'
    resource.rejection_reason = None
    if resource.author:
        resource.author.karma += 10
    db.session.commit()
    log_audit('resource.approved', 'resource', resource.id, f"Approved {resource.title} (+10 Karma to author)")
    flash(f"Resource '{resource.title}' has been approved and published to the Academic Vault.", 'success')
    return redirect(request.referrer or url_for('admin_resources'))


@app.route('/admin/resources/<int:resource_id>/reject', methods=['POST'])
@admin_required
def admin_resource_reject(resource_id):
    """Reject a resource with reason."""
    resource = db.session.get(Resource, resource_id)
    if not resource:
        abort(404)
    reason = request.form.get('rejection_reason', 'Does not meet academic quality guidelines.').strip()
    resource.status = 'Rejected'
    resource.rejection_reason = reason
    db.session.commit()
    log_audit('resource.rejected', 'resource', resource.id, f"Reason: {reason}")
    flash(f"Resource '{resource.title}' rejected.", 'warning')
    return redirect(request.referrer or url_for('admin_resources'))


@app.route('/admin/resources/<int:resource_id>/feature', methods=['POST'])
@admin_required
def admin_resource_toggle_feature(resource_id):
    """Toggle featured state on resource."""
    resource = db.session.get(Resource, resource_id)
    if not resource:
        abort(404)
    resource.is_featured = not resource.is_featured
    db.session.commit()
    log_audit('resource.featured', 'resource', resource.id, f"Featured: {resource.is_featured}")
    flash(f"Resource featured status updated.", 'info')
    return redirect(request.referrer or url_for('admin_resources'))


@app.route('/admin/resources/<int:resource_id>/delete', methods=['POST'])
@admin_required
def admin_resource_delete(resource_id):
    """Delete a resource."""
    resource = db.session.get(Resource, resource_id)
    if not resource:
        abort(404)
    title = resource.title
    db.session.delete(resource)
    db.session.commit()
    log_audit('resource.deleted', 'resource', resource_id, f"Deleted {title}")
    flash(f"Resource '{title}' deleted.", 'info')
    return redirect(request.referrer or url_for('admin_resources'))


@app.route('/admin/summaries')
@admin_required
def admin_summaries():
    """Admin lecture summary moderation."""
    course_id = request.args.get('course_id', type=int)
    summaries_query = Summary.query
    if course_id:
        summaries_query = summaries_query.filter_by(course_id=course_id)
    summaries = summaries_query.order_by(Summary.created_at.desc()).limit(100).all()
    courses = Course.query.order_by(Course.code).all()
    return render_template('admin/summaries.html', title='Summary Moderation', summaries=summaries, courses=courses, selected_course_id=course_id)


@app.route('/admin/summaries/<int:summary_id>/delete', methods=['POST'])
@admin_required
def admin_summary_delete(summary_id):
    """Remove inappropriate or erroneous summary."""
    summary = db.session.get(Summary, summary_id)
    if not summary:
        abort(404)
    topic = summary.topic or f"Summary #{summary.id}"
    db.session.delete(summary)
    db.session.commit()
    log_audit('summary.deleted', 'summary', summary_id, f"Deleted summary: {topic}")
    flash(f"Summary '{topic}' has been removed.", 'info')
    return redirect(request.referrer or url_for('admin_summaries'))


@app.route('/admin/announcements')
@admin_required
def admin_announcements():
    """Admin announcements management."""
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    courses = Course.query.order_by(Course.code).all()
    form = AnnouncementForm()
    return render_template('admin/announcements.html', title='Announcements Manager', announcements=announcements, courses=courses, form=form)


@app.route('/admin/announcements/new', methods=['POST'])
@admin_required
def admin_announcement_new():
    """Publish platform-wide or targeted official announcement."""
    form = AnnouncementForm()
    course_id = request.form.get('course_id', type=int)
    target_scope = request.form.get('target_scope', 'platform')
    is_pinned = bool(request.form.get('is_pinned'))

    if form.validate_on_submit():
        first_course = Course.query.first()
        ann = Announcement(
            course_id=course_id if target_scope != 'platform' and course_id else (first_course.id if first_course else 1),
            user_id=current_user.id,
            title=form.title.data.strip(),
            content=form.content.data.strip(),
            tag=form.tag.data,
            target_scope=target_scope,
            is_pinned=is_pinned
        )
        db.session.add(ann)
        db.session.commit()
        log_audit('announcement.published', 'announcement', ann.id, f"Title: {ann.title}, Scope: {target_scope}")
        flash('Official announcement published!', 'success')
    else:
        for err in form.errors.values():
            flash(f"Error: {err[0]}", 'danger')
    return redirect(url_for('admin_announcements'))


@app.route('/admin/announcements/<int:announcement_id>/delete', methods=['POST'])
@admin_required
def admin_announcement_delete(announcement_id):
    """Delete an announcement."""
    ann = db.session.get(Announcement, announcement_id)
    if not ann:
        abort(404)
    db.session.delete(ann)
    db.session.commit()
    log_audit('announcement.deleted', 'announcement', announcement_id)
    flash('Announcement removed.', 'info')
    return redirect(url_for('admin_announcements'))


@app.route('/admin/deadlines')
@admin_required
def admin_deadlines():
    """Admin official academic deadlines and exam countdowns."""
    deadlines = Deadline.query.order_by(Deadline.due_date.asc()).all()
    courses = Course.query.order_by(Course.code).all()
    form = DeadlineForm()
    return render_template('admin/deadlines.html', title='Official Deadlines & Exams', deadlines=deadlines, courses=courses, form=form)


@app.route('/admin/deadlines/new', methods=['POST'])
@admin_required
def admin_deadline_new():
    """Publish official academic deadline or exam countdown."""
    form = DeadlineForm()
    if form.validate_on_submit():
        dl = Deadline(
            course_id=form.course_id.data,
            user_id=current_user.id,
            title=form.title.data.strip(),
            due_date=form.due_date.data,
            category=form.category.data,
            priority=form.priority.data,
            description=form.description.data.strip() if form.description.data else None,
            is_official=True
        )
        db.session.add(dl)
        db.session.commit()
        log_audit('deadline.created', 'deadline', dl.id, f"Official Deadline: {dl.title} Due: {dl.due_date}")
        flash('Official deadline broadcast to students.', 'success')
    else:
        for err in form.errors.values():
            flash(f"Error: {err[0]}", 'danger')
    return redirect(url_for('admin_deadlines'))


@app.route('/admin/deadlines/<int:deadline_id>/delete', methods=['POST'])
@admin_required
def admin_deadline_delete(deadline_id):
    """Delete an official deadline."""
    dl = db.session.get(Deadline, deadline_id)
    if not dl:
        abort(404)
    db.session.delete(dl)
    db.session.commit()
    log_audit('deadline.deleted', 'deadline', deadline_id)
    flash('Deadline deleted.', 'info')
    return redirect(url_for('admin_deadlines'))


@app.route('/admin/reports')
@admin_required
def admin_reports():
    """Admin content report and student safety center."""
    status_filter = request.args.get('status', 'Open')
    reports_query = Report.query
    if status_filter != 'ALL':
        reports_query = reports_query.filter_by(status=status_filter)
    reports = reports_query.order_by(Report.created_at.desc()).all()
    return render_template('admin/reports.html', title='Report & Moderation Center', reports=reports, status_filter=status_filter)


@app.route('/admin/reports/<int:report_id>/status', methods=['POST'])
@admin_required
def admin_report_update_status(report_id):
    """Update report status (Under Review, Resolved, Dismissed)."""
    report = db.session.get(Report, report_id)
    if not report:
        abort(404)
    new_status = request.form.get('status', 'Resolved')
    notes = request.form.get('resolution_notes', '').strip()

    report.status = new_status
    report.resolution_notes = notes
    report.resolved_by_id = current_user.id
    db.session.commit()
    log_audit('report.status_updated', 'report', report.id, f"Status: {new_status}, Notes: {notes}")
    flash(f"Report #{report.id} marked as {new_status}.", 'success')
    return redirect(request.referrer or url_for('admin_reports'))


@app.route('/admin/feature-flags')
@admin_required
def admin_feature_flags():
    """Feature flag controls."""
    flags = FeatureFlag.query.order_by(FeatureFlag.name.asc()).all()
    return render_template('admin/feature_flags.html', title='Feature Controls', flags=flags)


@app.route('/admin/feature-flags/<string:key>/toggle', methods=['POST'])
@admin_required
def admin_feature_flag_toggle(key):
    """Toggle feature flag on/off."""
    flag = FeatureFlag.query.filter_by(key=key).first()
    if not flag:
        abort(404)
    flag.is_enabled = not flag.is_enabled
    db.session.commit()
    log_audit('feature_flag.toggled', 'feature_flag', flag.key, f"Set to {flag.is_enabled}")
    flash(f"Feature '{flag.name}' is now {'ENABLED' if flag.is_enabled else 'DISABLED'}.", 'success')
    return redirect(url_for('admin_feature_flags'))


@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    """Global system configuration settings."""
    form = SystemSettingsForm()
    if request.method == 'GET':
        try:
            form.attendance_threshold.data = float(get_system_setting('attendance_threshold', '75.0'))
            form.maintenance_mode.data = (get_system_setting('maintenance_mode', 'false') == 'true')
            form.registration_enabled.data = (get_system_setting('registration_enabled', 'true') == 'true')
            form.default_semester.data = int(get_system_setting('default_semester', '5'))
        except Exception:
            pass

    if form.validate_on_submit():
        settings_map = {
            'attendance_threshold': str(form.attendance_threshold.data),
            'maintenance_mode': 'true' if form.maintenance_mode.data else 'false',
            'registration_enabled': 'true' if form.registration_enabled.data else 'false',
            'default_semester': str(form.default_semester.data)
        }
        for k, v in settings_map.items():
            s = SystemSetting.query.filter_by(key=k).first()
            if s:
                s.value = v
            else:
                db.session.add(SystemSetting(key=k, value=v))
        db.session.commit()
        log_audit('settings.updated', 'system_setting', None, f"Updated platform settings: {settings_map}")
        flash('Platform settings updated successfully.', 'success')
        return redirect(url_for('admin_settings'))

    return render_template('admin/settings.html', title='Platform Settings', form=form)


@app.route('/admin/audit-logs')
@admin_required
def admin_audit_logs():
    """Administrative action audit history."""
    action_filter = request.args.get('action', '')
    logs_query = AuditLog.query
    if action_filter:
        logs_query = logs_query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    logs = logs_query.order_by(AuditLog.created_at.desc()).limit(150).all()
    return render_template('admin/audit_logs.html', title='System Audit Logs', logs=logs, action_filter=action_filter)


@app.route('/admin/export/<string:entity>')
@admin_required
def admin_export_csv(entity):
    """Export platform data to CSV format for backup and administrative reporting."""
    si = io.StringIO()
    writer = csv.writer(si)

    if entity == 'users':
        writer.writerow(['ID', 'Name', 'Email', 'Role', 'Karma', 'College', 'Program', 'Semester', 'Section', 'Suspended', 'Created At'])
        for u in User.query.order_by(User.id).all():
            writer.writerow([u.id, u.name, u.email, u.role, u.karma, u.college, u.program, u.semester, u.section, u.is_suspended, u.created_at])
    elif entity == 'courses':
        writer.writerow(['ID', 'Code', 'Name', 'Section', 'Semester', 'Instructor', 'Room', 'Schedule', 'Status', 'Archived'])
        for c in Course.query.order_by(Course.id).all():
            writer.writerow([c.id, c.code, c.name, c.section, c.semester, c.instructor, c.room, c.schedule, c.status, c.is_archived])
    elif entity == 'resources':
        writer.writerow(['ID', 'Course', 'Title', 'Category', 'URL', 'Author', 'Status', 'Downloads', 'Helpful Count', 'Created At'])
        for r in Resource.query.order_by(Resource.id).all():
            writer.writerow([r.id, r.course.code if r.course else '', r.title, r.category, r.resource_url, r.author.name if r.author else '', r.status, r.downloads, r.helpful_count, r.created_at])
    elif entity == 'summaries':
        writer.writerow(['ID', 'Course', 'Date', 'Topic', 'Category', 'Author', 'Verified', 'Verified By', 'Helpful Count', 'Created At'])
        for s in Summary.query.order_by(Summary.id).all():
            writer.writerow([s.id, s.course.code if s.course else '', s.date, s.topic, s.category, s.author.name if s.author else '', s.is_verified, s.verified_by, s.helpful_count, s.created_at])
    elif entity == 'reports':
        writer.writerow(['ID', 'Reporter', 'Target Type', 'Target ID', 'Category', 'Reason', 'Status', 'Resolution Notes', 'Created At'])
        for rep in Report.query.order_by(Report.id).all():
            writer.writerow([rep.id, rep.reporter.name if rep.reporter else '', rep.target_type, rep.target_id, rep.category, rep.reason, rep.status, rep.resolution_notes, rep.created_at])
    else:
        abort(404)

    log_audit('data.exported', 'export', entity, f"Exported CSV for {entity}")
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=classcatch_{entity}_{date.today()}.csv"}
    )


# ==========================================
# Database Auto-seed & App Runner
# ==========================================

def init_db():
    """Ensure database schema is created and populated with demo courses and settings."""
    with app.app_context():
        # Apply non-destructive column additions if running on PostgreSQL
        engine = db.engine
        if engine.dialect.name == 'postgresql':
            try:
                with engine.connect() as conn:
                    queries = [
                        'ALTER TABLE courses ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;',
                        'ALTER TABLE users ADD COLUMN IF NOT EXISTS college VARCHAR(120) DEFAULT \'GLA University\';',
                        'ALTER TABLE users ADD COLUMN IF NOT EXISTS program VARCHAR(100) DEFAULT \'B.Tech CSE\';',
                        'ALTER TABLE users ADD COLUMN IF NOT EXISTS semester INTEGER DEFAULT 5;',
                        'ALTER TABLE users ADD COLUMN IF NOT EXISTS section VARCHAR(20) DEFAULT \'A\';',
                        'ALTER TABLE users ADD COLUMN IF NOT EXISTS is_suspended BOOLEAN DEFAULT FALSE;',
                        'ALTER TABLE users ADD COLUMN IF NOT EXISTS is_onboarded BOOLEAN DEFAULT TRUE;',
                        'ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;',
                        'ALTER TABLE resources ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT \'Approved\';',
                        'ALTER TABLE resources ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;',
                        'ALTER TABLE resources ADD COLUMN IF NOT EXISTS rejection_reason TEXT;',
                        'ALTER TABLE announcements ADD COLUMN IF NOT EXISTS target_scope VARCHAR(30) DEFAULT \'course\';',
                        'ALTER TABLE announcements ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE;',
                        'ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS is_official BOOLEAN DEFAULT FALSE;',
                        'ALTER TABLE summaries ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;'
                    ]
                    from sqlalchemy import text
                    for q in queries:
                        conn.execute(text(q))
                    conn.commit()
            except Exception as e:
                print(f"[AUTO-MIGRATION NOTICE] {e}")

        db.create_all()

        # Seed default feature flags if none exist
        if FeatureFlag.query.count() == 0:
            default_flags = [
                FeatureFlag(key="catchup_feed", name="Missed Class Catch-up Engine", description="Aggregated multi-course lecture catch-up feed", is_enabled=True),
                FeatureFlag(key="attendance_tracker", name="Attendance & Safe Bunk Predictor", description="Safe bunk and recovery math calculator", is_enabled=True),
                FeatureFlag(key="academic_vault", name="Academic Resource & PYQ Vault", description="Student-shared previous exam questions and notes", is_enabled=True),
                FeatureFlag(key="campus_chat", name="Unofficial Peer & Course Chat", description="Peer discussion and requirements exchange", is_enabled=True),
                FeatureFlag(key="anonymous_doubts", name="Anonymous Doubt Clearing Mode", description="Masks student identity for honest doubts", is_enabled=True),
                FeatureFlag(key="ai_ocr", name="AI Whiteboard-to-Notes OCR Engine", description="Transcribes classroom board photos into notes", is_enabled=True),
                FeatureFlag(key="morning_dispatch", name="Morning Timetable & WhatsApp Digest", description="Daily academic briefing simulation", is_enabled=True),
                FeatureFlag(key="karma_rewards", name="Peer Contribution & Karma System", description="Rewards students for quality lecture summaries", is_enabled=True)
            ]
            db.session.add_all(default_flags)
            db.session.commit()

        # Seed default system settings if none exist
        if SystemSetting.query.count() == 0:
            default_settings = [
                SystemSetting(key="attendance_threshold", value="75.0", description="Institutional minimum attendance target percentage"),
                SystemSetting(key="maintenance_mode", value="false", description="Restricts student access for scheduled maintenance"),
                SystemSetting(key="registration_enabled", value="true", description="Allow new student registrations"),
                SystemSetting(key="default_semester", value="5", description="Default active academic semester")
            ]
            db.session.add_all(default_settings)
            db.session.commit()

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
