# 🎓 ClassCatch

> **Peer-Powered Class Catch-up & Student Hub for College Students**

ClassCatch empowers students who attended a class to post concise lecture summaries, assignments given, and announcements made. Students who missed the class can easily catch up by selecting their course and date.

Additionally, ClassCatch features an **Unofficial Class Chat** for peer requirements and doubts, a **Class Announcements Board**, an **Interactive Attendance & Bunk Calculator**, and a **Class Timetable & Room Availability Tracker**.

---

## 🌟 Key Features

1. **Class Catch-up Board**:
   - Date-sorted lecture recaps with topic, concepts, homework assigned, and announcements.
   - Date picker filter to pinpoint exact missed lecture dates.
   - Upvote / *"Found this Helpful"* counter for top student contributors.
2. **💬 Unofficial Class Chat & Campus Lounge**:
   - Dedicated peer chat rooms for each course + a campus-wide lounge.
   - Filter discussions by: *🙋 Requirement*, *❓ Question / Doubt*, *📄 Notes Request*, and *💬 General*.
3. **📢 Class Notice & Announcement Hub**:
   - Important notices with priority tags (*Exam*, *Quiz*, *Assignment Deadline*, *Room Change*, *Urgent*).
4. **🧮 Interactive Attendance & Bunk Predictor**:
   - Real-time client-side calculator: calculates attendance percentage.
   - **Safe Bunks Predictor**: Tells you how many consecutive classes you can safely skip while staying $\ge 75\%$.
   - **Recovery Predictor**: Tells you how many consecutive classes you must attend to climb back above $75\%$.
   - Save and track attendance records per enrolled course on your student profile.
5. **🗓️ Class Timetable & Room Availability**:
   - View scheduled lecture theater/lab rooms, instructor names, weekly time slots, and real-time class status (*Scheduled*, *Cancelled*, *Extra Class*).
6. **🔐 Authentication & Security**:
   - Secure student registration and login with session management via `Flask-Login`.
   - Passwords securely hashed with `Werkzeug`.
   - Form validation & CSRF protection with `Flask-WTF`.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask 3.0+
- **Database & ORM**: SQLite, Flask-SQLAlchemy
- **Authentication**: Flask-Login
- **Forms & Validation**: Flask-WTF, WTForms, email-validator
- **Frontend & Styling**: HTML5, Vanilla CSS, Bootstrap 5.3 CDN, Bootstrap Icons, FontAwesome 6, Google Fonts (*Plus Jakarta Sans*)

---

## 📂 Project Structure

```
gla/
├── app.py                  # Main Flask application and routing logic
├── models.py               # SQLAlchemy database models (User, Course, Summary, ChatMessage, etc.)
├── forms.py                # Flask-WTF validated form definitions
├── seed.py                 # Database initialization & mock data seed script
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation and setup guide
├── static/
│   └── css/
│       └── style.css       # Custom modern UI styling, chat bubbles, and indicators
└── templates/
    ├── base.html           # Master layout with navigation, flash toasts, and footer
    ├── index.html          # Dashboard (course directory, today's recaps, notice board)
    ├── course.html         # Course hub (Catch-ups, Unofficial Chat, Notices, Timetable)
    ├── attendance.html     # Interactive attendance calculator & course-wise tracker
    ├── lounge.html         # Campus-wide unofficial student lounge & requirements feed
    ├── post_summary.html   # Dedicated summary publishing form
    ├── summary_detail.html # Full view for an individual lecture catch-up note
    ├── login.html          # Clean card-based login screen
    └── register.html       # Clean student sign-up screen
```

---

## 🚀 Step-by-Step Setup & Run Instructions

### 1. Clone or Navigate to Project Directory
```powershell
cd c:\Users\hp\OneDrive\Desktop\gla
```

### 2. Create and Activate a Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows PowerShell
.\venv\Scripts\Activate.ps1

# (If PowerShell displays an execution policy error, run:)
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Seed the Database with Sample Data
Run `seed.py` to automatically create all tables and populate realistic courses, sample catch-ups, chat discussions, and announcements:
```powershell
python seed.py
```

### 5. Start the Application
```powershell
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Demo Accounts

Use any of these pre-seeded student accounts to test:

| Student Name | Email | Password | Role |
| :--- | :--- | :--- | :--- |
| **Alex Rivera** | `alex@classcatch.edu` | `password123` | Student |
| **Sarah Chen** | `sarah@classcatch.edu` | `password123` | Student |
| **David Sharma** | `david@classcatch.edu` | `password123` | Student |

*You can also register a brand new student account via the **"Join ClassCatch"** button on the top navigation.*

---

## 📊 Database Models Overview

- **`User`**: `id`, `name`, `email`, `password_hash`, `role`, `avatar_color`
- **`Course`**: `id`, `name`, `code`, `section`, `semester`, `instructor`, `room`, `schedule`, `status`
- **`Summary`**: `id`, `course_id` (FK), `user_id` (FK), `date`, `topic`, `category`, `content`, `helpful_count`, `created_at`
- **`ChatMessage`**: `id`, `course_id` (FK, nullable), `user_id` (FK), `message`, `category`, `created_at`
- **`Announcement`**: `id`, `course_id` (FK), `user_id` (FK), `title`, `content`, `tag`, `created_at`
- **`AttendanceRecord`**: `id`, `user_id` (FK), `course_id` (FK), `total_classes`, `attended_classes`, `target_percentage`

---

## 💡 How Bunk Prediction Works

- **Safe Bunk Formula**:
  $$\text{Safe Bunks} = \left\lfloor \frac{\text{Attended Classes}}{\text{Target \%} / 100} \right\rfloor - \text{Total Classes}$$
- **Recovery Requirement Formula**:
  $$\text{Classes Needed} = \left\lceil \frac{(\text{Target \%} / 100) \times \text{Total} - \text{Attended}}{1 - (\text{Target \%} / 100)} \right\rceil$$

---

## 📄 License
This project is open-source for college education and peer learning.
