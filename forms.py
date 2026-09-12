from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    TextAreaField, SelectField, DateField, IntegerField, FloatField
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, NumberRange
from models import User

class RegistrationForm(FlaskForm):
    """Form for new student registration."""
    name = StringField('Full Name', validators=[
        DataRequired(message="Please enter your full name."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField('College / Student Email', validators=[
        DataRequired(message="Please enter your email address."),
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=6, message="Password must be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Create Account')

    def validate_email(self, email):
        """Ensure email is not already registered."""
        user = User.query.filter_by(email=email.data.strip().lower()).first()
        if user:
            raise ValidationError("An account with this email address already exists. Please log in.")


class LoginForm(FlaskForm):
    """Form for user authentication."""
    email = StringField('Email Address', validators=[
        DataRequired(message="Please enter your email address."),
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Please enter your password.")
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class SummaryForm(FlaskForm):
    """Form for posting a class summary / catch-up note."""
    course_id = SelectField('Course', coerce=int, validators=[
        DataRequired(message="Please select a course.")
    ])
    date = DateField('Class Date', default=date.today, validators=[
        DataRequired(message="Please select the date of the class.")
    ])
    category = SelectField('Category', choices=[
        ('Lecture Notes', '📝 Lecture Notes & Concepts'),
        ('Assignment', '📋 Assignment / Homework Given'),
        ('Exam Prep', '🎯 Midterm / Quiz Highlights'),
        ('Lab Work', '🧪 Practical / Lab Experiment')
    ], default='Lecture Notes')
    topic = StringField('Topic / Chapter Covered', validators=[
        Optional(),
        Length(max=200, message="Topic title cannot exceed 200 characters.")
    ])
    content = TextAreaField('Class Summary & Key Takeaways', validators=[
        DataRequired(message="Please share what was covered, assignments assigned, or announcements made.")
    ])
    submit = SubmitField('Post Class Catch-up')


class ChatMessageForm(FlaskForm):
    """Form for posting messages in unofficial class/lounge chat."""
    message = TextAreaField('Message / Requirement', validators=[
        DataRequired(message="Please enter your message or question.")
    ])
    category = SelectField('Type', choices=[
        ('General', '💬 General Discussion'),
        ('Requirement', '🙋 Requirement / Lab Manual'),
        ('Doubt', '❓ Question / Doubt'),
        ('Notes Request', '📄 Notes Request')
    ], default='General')
    is_anonymous = BooleanField('Ask Anonymously 🎭')
    submit = SubmitField('Send Message')


class AnnouncementForm(FlaskForm):
    """Form for posting an announcement to the class board."""
    title = StringField('Announcement Title', validators=[
        DataRequired(message="Please enter an announcement title."),
        Length(max=150, message="Title cannot exceed 150 characters.")
    ])
    tag = SelectField('Priority / Tag', choices=[
        ('General', '📢 General Update'),
        ('Assignment', '⏰ Assignment Deadline'),
        ('Exam', '📝 Midterm / Exam Alert'),
        ('Quiz', '⚡ Upcoming Quiz'),
        ('Room Change', '🚪 Room / Venue Change'),
        ('Urgent', '🚨 Urgent Notice')
    ], default='General')
    content = TextAreaField('Announcement Details', validators=[
        DataRequired(message="Please provide announcement details.")
    ])
    submit = SubmitField('Publish Announcement')


class AttendanceForm(FlaskForm):
    """Form for recording or updating course attendance."""
    course_id = SelectField('Course', coerce=int, validators=[
        DataRequired(message="Please select a course.")
    ])
    total_classes = IntegerField('Total Classes Held', validators=[
        DataRequired(message="Please enter total classes held."),
        NumberRange(min=0, message="Total classes cannot be negative.")
    ])
    attended_classes = IntegerField('Classes Attended', validators=[
        NumberRange(min=0, message="Attended classes cannot be negative.")
    ])
    target_percentage = FloatField('Target Minimum (%)', default=75.0, validators=[
        DataRequired(message="Please enter target criteria percentage."),
        NumberRange(min=50.0, max=100.0, message="Target must be between 50% and 100%.")
    ])
    submit = SubmitField('Save Attendance')

    def validate_attended_classes(self, field):
        """Validate attended cannot exceed total classes."""
        if self.total_classes.data is not None and field.data is not None:
            if field.data > self.total_classes.data:
                raise ValidationError("Classes attended cannot be greater than total classes held.")


class DeadlineForm(FlaskForm):
    """Form for adding academic deadlines and exam countdowns."""
    course_id = SelectField('Course', coerce=int, validators=[
        DataRequired(message="Please select a course.")
    ])
    title = StringField('Deadline Title', validators=[
        DataRequired(message="Please enter a title for this deadline."),
        Length(max=150, message="Title cannot exceed 150 characters.")
    ])
    due_date = DateField('Due Date', default=date.today, validators=[
        DataRequired(message="Please specify the due date.")
    ])
    category = SelectField('Type', choices=[
        ('Assignment', '📋 Assignment / Homework'),
        ('Quiz / Exam', '🎯 Quiz / Midterm / Endterm'),
        ('Lab Submission', '🧪 Lab Experiment / Code Repo'),
        ('Project Milestone', '🚀 Project Phase / Presentation')
    ], default='Assignment')
    priority = SelectField('Priority', choices=[
        ('Normal', '🟢 Normal'),
        ('Medium', '🟡 Medium Priority'),
        ('High', '🔴 High / Critical')
    ], default='Normal')
    description = TextAreaField('Additional Instructions / Submission Portal', validators=[
        Optional()
    ])
    submit = SubmitField('Add Deadline')


class ResourceForm(FlaskForm):
    """Form for sharing academic PYQs, cheat sheets, and lab guides."""
    course_id = SelectField('Course', coerce=int, validators=[
        DataRequired(message="Please select a course.")
    ])
    title = StringField('Resource Title', validators=[
        DataRequired(message="Please enter a title for the resource."),
        Length(max=150, message="Title cannot exceed 150 characters.")
    ])
    category = SelectField('Category', choices=[
        ('PYQ & Solutions', '📚 Previous Year Questions (PYQs) & Solutions'),
        ('Formula Cheat Sheet', '⚡ Formula Sheet & Quick Revision Map'),
        ('Lab Manual & Codes', '🧪 Lab Manual, Viva Questions & Code'),
        ('Handwritten Notes', '✍️ Handwritten Class Notes (Clean Scan)'),
        ('Syllabus & Slides', '📊 Official Syllabus & Professor Slides')
    ], default='PYQ & Solutions')
    resource_url = StringField('Resource Link (Google Drive / GitHub / PDF URL)', validators=[
        DataRequired(message="Please provide a valid link to the resource.")
    ])
    description = TextAreaField('Description / What makes this helpful', validators=[
        Optional()
    ])
    submit = SubmitField('Share Resource (+10 Karma)')


class CourseForm(FlaskForm):
    """Form for adding real university courses/subjects."""
    name = StringField('Subject / Course Name', validators=[
        DataRequired(message="Please enter the subject name."),
        Length(max=100, message="Course name must be under 100 characters.")
    ])
    code = StringField('Course Code (e.g. CSE-301, BCA-204)', validators=[
        DataRequired(message="Course code is required."),
        Length(max=20, message="Course code must be under 20 characters.")
    ])
    section = StringField('Section / Batch (e.g. A, B, Section-1)', default='A', validators=[
        Optional(), Length(max=20)
    ])
    semester = IntegerField('Semester', default=1, validators=[
        DataRequired(message="Please specify the semester number."),
        NumberRange(min=1, max=12, message="Semester must be between 1 and 12.")
    ])
    instructor = StringField('Professor / Instructor Name', validators=[
        Optional(), Length(max=100)
    ])
    room = StringField('Room / Lecture Hall Location', validators=[
        Optional(), Length(max=50)
    ])
    schedule = StringField('Weekly Timings (e.g. Mon, Wed, Fri 10:00 AM)', validators=[
        Optional(), Length(max=100)
    ])
    submit = SubmitField('Add Course to Timetable')

