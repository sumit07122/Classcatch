# ClassCatch — Developer Handover & Operations Manual

> **Version:** 2.0.0 (Production Release)  
> **Target Institution:** GLA University, Mathura Campus  
> **Core Architecture:** Flask WSGI, PostgreSQL (Neon Serverless), Vanilla CSS & Bootstrap 5, Modern JavaScript

---

## 1. System Overview & Technology Stack

**ClassCatch** is an institutional academic continuity and catch-up platform designed for university students. It bridges the gap caused by class absences, uncoordinated peer sharing, and attendance deficits through verified peer notes, real-time timetable tracking, and official section announcements.

### Technology Stack Summary
| Layer | Technology | Key Details |
|---|---|---|
| **Backend Framework** | Python 3.11+ / Flask | Lightweight, robust WSGI application |
| **Database & ORM** | PostgreSQL (Neon Serverless) / SQLAlchemy | ACID compliance, pooling, instant restore |
| **Authentication** | Flask-Login + Google Identity Services (GIS) | Restricted to institutional `@gla.ac.in` domain |
| **Frontend Styling** | Vanilla CSS + Bootstrap 5 | Modern glassmorphism, responsive grid, dark/light accents |
| **Form Handling** | Flask-WTF / WTForms | CSRF protection, server-side validation |
| **Deployment Target** | Vercel Serverless WSGI / Gunicorn | Global low-latency CDN and edge caching |
| **Security Controls** | Werkzeug Password Hashing + Security Headers | HSTS, CSP, X-Frame-Options, anti-tampering |

---

## 2. Directory & File Organization

```
gla/
├── app.py                     # Main application entry point, route definitions, middleware
├── models.py                  # Database entities, relationships, RBAC helper methods
├── forms.py                   # Form validation classes (SummaryForm, LoginForm, etc.)
├── mailer.py                  # Transactional email delivery (Brevo API / SMTP fallback)
├── test_pilot_qa.py           # Automated test suite for QA and security headers
├── vercel.json                # Vercel serverless deployment build and routing config
├── requirements.txt           # Production Python dependencies
├── static/
│   ├── css/
│   │   └── style.css          # Design tokens, typography, glassmorphism components
│   ├── js/
│   │   └── main.js            # PWA service worker, interactive UI, clipboard helpers
│   └── images/                # Brand badges, avatars, icons
└── templates/
    ├── base.html              # Core navigation layout, global modal containers
    ├── index.html             # Main dashboard (Timetable, summaries, deadlines)
    ├── course.html            # Unified course hub (Summaries, chat, notices)
    ├── summary_detail.html    # Detailed note reader with CR approval & delete actions
    ├── catchup.html           # "What Did I Miss?" date-filtered absence hub
    ├── attendance.html        # Smart attendance calculator with 75% rule solver
    ├── select_section.html    # Multi-section switcher and enrollment request
    ├── enrollment_pending.html# Pending enrollment hold screen
    ├── login.html             # Official institutional authentication screen
    └── admin/                 # Administration and CR designation panels
```

---

## 3. Database Schema & Models Reference

All tables reside in PostgreSQL via SQLAlchemy in [`models.py`](models.py).

### Core Entities

#### 1. `User` (`users`)
Represents students, Class Representatives (CRs), instructors, and administrators.
- `id`: Primary key.
- `email`: Institutional email address (unique index).
- `name`: Full student or faculty name.
- `role`: Role string: `'student'`, `'cr'`, `'instructor'`, `'admin'`, `'superadmin'`.
- `section`: Default assigned academic section (e.g. `'2FE'`).
- `karma`: Reputation points earned by contributing verified summaries (+20 on CR approval, +5 on peer helpful mark).
- `is_verified`: Boolean indicating institutional email address confirmation.
- **Key Methods**:
  - `user.is_admin()`: Returns `True` if `role in ['admin', 'superadmin']`.
  - `user.is_cr()`: Returns `True` if `role in ['cr', 'admin', 'superadmin']`.
  - `user.is_cr_for(course_id, section)`: Evaluates if user holds Class Representative authority for a given subject/section.

#### 2. `Course` (`courses`)
Academic subjects linked to sections and timetables.
- `id`: Primary key.
- `name`, `code`: Subject title (e.g., *Design and Analysis of Algorithms*, *BCSE 0031*).
- `section`: Section scope (`'2FE'`, `'2FD'`, etc.).
- `schedule`: Class timing string (e.g., `'Mon, Wed 10:00 AM'`).
- `room`: Room designation (e.g., `'AB-VI Room 306'`).
- `status`: `'Scheduled'`, `'Cancelled'`, or `'Extra Class'`.

#### 3. `Summary` (`summaries`)
Peer-contributed lecture notes and catch-up digests.
- `id`: Primary key.
- `course_id`: Foreign key to `courses.id`.
- `user_id`: Foreign key to `users.id` (author).
- `date`: Lecture date.
- `topic`: Optional lecture subject heading.
- `category`: `'Lecture Notes'`, `'Assignment'`, `'Exam Prep'`, or `'Lab Work'`.
- `content`: Markdown/plain text content of the summary.
- `is_verified`: **CR Quality Gate** (`False` on initial student post; `True` once approved by CR or if posted directly by CR/Admin).
- `verified_by`: Name and title of the verifying CR.

#### 4. `CRAssignment` (`cr_assignments`)
Explicit assignment of Class Representative authority to specific courses and sections.

#### 5. `Enrollment` (`enrollments`)
Academic section registration record ensuring section isolation.
- `status`: `'approved'`, `'pending'`, or `'rejected'`.
- `is_active`: Enforces one active section per student.

---

## 4. Role-Based Access Control (RBAC)

ClassCatch enforces strict access boundaries:

```
[Superadmin / Admin]
        │
        ▼ Full System Authority (Users, Roster, Global Deletes)
[Class Representative (CR)]
        │
        ▼ Section Authority (Approves student notes, manages course feed)
[Student]
        │
        ▼ Read verified notes, submit notes (pending approval), track attendance
```

### CR Quality Gate Workflow
1. **Student Submission:**
   - Student submits notes at `/course/<id>/summary` or `/summary/new`.
   - `is_verified` is initialized to `False`.
   - The student receives an informative toast: *"Submitted! It will appear once approved by your Class Representative (CR)."*
   - Author sees the post marked with an amber badge: `Pending CR Review`.
   - Peer students **cannot** see the pending note on `/course/<id>`, `/catchup`, `/`, or `/search`.

2. **CR Review & Approval:**
   - The designated CR for the course/section sees the note with the button: `Approve Note (CR)`.
   - Clicking triggers `POST /summary/<id>/verify`.
   - The note is set to `is_verified = True`, `verified_by = current_user.name`.
   - The author is automatically awarded **+20 Karma**.
   - An immutable record is written to `audit_logs`.
   - The note becomes publicly visible across the institution with the green `CR Verified` seal.

3. **Post Deletion:**
   - Allowed strictly for:
     1. The original post author (`current_user.id == summary.user_id`).
     2. The designated CR for that course (`current_user.is_cr_for(course.id, course.section)`).
     3. Platform Administrators (`current_user.is_admin()`).
   - Action: `POST /summary/<id>/delete` with browser confirmation dialog.

---

## 5. Local Development & Deployment

### Prerequisites
- Python 3.11+
- Neon PostgreSQL Database URL
- Git

### Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/sumit07122/Classcatch.git
cd Classcatch

# 2. Set up virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or source venv/bin/activate  # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (.env)
cp .env.example .env
# Ensure DATABASE_URL, SECRET_KEY, and GOOGLE_CLIENT_ID are populated

# 5. Run the application
python app.py
```
App runs locally at `http://127.0.0.1:5000`.

### Vercel Serverless Deployment
The repository is pre-configured with `vercel.json`:
- Builds via `@vercel/python`.
- Routes all endpoints through `app.py`.
- Ensure the following Environment Variables are configured in Vercel Project Settings:
  - `DATABASE_URL`: Your pooled Neon Postgres connection string.
  - `SECRET_KEY`: High-entropy cryptographic string.
  - `GOOGLE_CLIENT_ID`: Google Cloud OAuth credentials for GIS.

---

## 6. Maintenance & Operational Best Practices

1. **Audit Logs:** Every critical action (CR assignment, role promotion, post approval, post deletion) logs to the `audit_logs` table.
2. **Database Migrations:** When updating schema in `models.py`, generate and run standard SQLAlchemy migrations or direct SQL statements on your Neon branch before merging to `main`.
3. **Automated Testing:** Run `python scratch/test_cr_workflow.py` to validate RBAC, CR verification, and deletion safeguards.
