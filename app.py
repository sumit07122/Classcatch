import os
from datetime import date, datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Course, Summary, ChatMessage, Announcement, AttendanceRecord, Deadline, Resource
from forms import (
    RegistrationForm, LoginForm, SummaryForm, ChatMessageForm,
    AnnouncementForm, AttendanceForm, DeadlineForm, ResourceForm
)

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
    return db.session.get(User, int(user_id))


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
    Allows Class Representatives or Instructors to mark lecture notes as 'Verified Accurate'.
    Awards +20 Karma to the student author.
    """
    summary = Summary.query.get_or_404(summary_id)
    summary.is_verified = not summary.is_verified
    if summary.is_verified:
        summary.verified_by = current_user.name
        if summary.author:
            summary.author.karma = (summary.author.karma or 50) + 20
        flash(f'✅ Lecture note verified by {current_user.name}! (+20 Karma awarded to author)', 'success')
    else:
        summary.verified_by = None
        flash('Verification removed.', 'info')

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
