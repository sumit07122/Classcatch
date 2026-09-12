# 🎓 ClassCatch — Production Academic Companion & Campus Operations Platform

> **"Missed class? ClassCatch catches it for you."**

ClassCatch is a student-first academic workspace and institutional management platform built for college students and academic administrators. It solves the daily friction of missed lectures, urgent deadlines, safe bunk predictions, and academic resource sharing.

---

## 🌟 Architecture & Core Pillars

### 1. Student Academic Workspace
* **Absence & Catch-Up Engine (`/catchup`)**: Multi-course aggregated lecture notes for any date. Includes 1-click **WhatsApp-formatted digest export** to keep study groups in sync.
* **1-Tap Attendance & Safe Bunk Predictor (`/attendance`)**: Instant `+ Present` and `+ Missed` buttons per subject. Real-time safe bunk countdown ($\ge 75\%$) and recovery class requirements.
* **Academic Resource Vault (`/resources`)**: Community-shared Previous Year Questions (PYQs), formula cheat sheets, and tested lab manuals with download metrics and helpful ratings.
* **Global Academic Search (`/search`)**: Instant multi-table search across subjects, summaries, deadlines, and vault files with keyboard shortcut (`/`).
* **Unofficial Peer Chat & Doubt Mode (`/lounge`)**: Course-specific discussions and anonymous doubt clearing.
* **AI Whiteboard-to-Notes OCR (`/api/save-whiteboard-note`)**: Client-side photo scanner with live thumbnail preview and 1-tap save into structured course notes.

---

### 2. Admin Control Center (`/admin`)
ClassCatch includes an enterprise-grade, code-free administrative management console:

| Admin Module | Route | Capabilities |
| :--- | :--- | :--- |
| **Operational Dashboard** | `/admin` | Real-time metrics (users, active courses, pending approvals, open reports, audit stream, 1-click CSV exports). |
| **User & Access Control** | `/admin/users` | Search, filter by role, promote/demote (Student, CR, Admin, SuperAdmin), account suspension. |
| **Course & Schedule Manager** | `/admin/courses` | Create, edit, archive, and delete official courses, lecture hall assignments, and weekly timings. |
| **Bulk CSV Course Import** | `/admin/courses/import` | Paste tabular schedule data from Excel/Sheets with live schema validation and preview before commit. |
| **CR Authority Center** | `/admin/cr` | Designate Class Representatives (CRs) per subject/section with server-side authorization enforcement. |
| **Resource Vault Moderation** | `/admin/resources` | Review student-uploaded PYQs and slides; 1-click Approve, Reject with customized feedback, or Feature. |
| **Lecture Note Moderation** | `/admin/summaries` | Inspect and remove inaccurate summaries or verify notes on behalf of instructors. |
| **Official Announcements** | `/admin/announcements` | Publish platform-wide or course-targeted notices with priority flags (`Urgent`, `Exam`, `Room Change`). |
| **Official Deadlines & Exams** | `/admin/deadlines` | Broadcast department midterms, quizzes, and project evaluation dates directly to student countdowns. |
| **Student Safety & Reports** | `/admin/reports` | Moderation center for student-submitted reports (`Spam`, `Incorrect Info`, `Harassment`, `Broken Link`). |
| **Feature Controls & Killswitches** | `/admin/feature-flags` | Toggle platform modules on/off live without code changes (`catchup_feed`, `attendance_tracker`, `ai_ocr`, etc.). |
| **Platform Settings** | `/admin/settings` | Configure minimum attendance target %, enable/disable Maintenance Mode, toggle student registration. |
| **Operational Audit Logs** | `/admin/audit-logs` | Immutable chronological trail of all administrative actions, role modifications, and moderation decisions. |
| **1-Click Data Backups** | `/admin/export/<type>` | Instant CSV exports for Users, Courses, Resources, Summaries, and Reports. |

---

## 👥 Role-Based Access Control (RBAC)

1. **Student (`student`)**:
   - Manage personal attendance, calculate safe bunks, post lecture catch-up notes, share resources, join peer chats, and report content.
2. **Class Representative (`cr`)**:
   - Authorized per course/section. Can verify lecture summaries (`CR Verified` badge) and post course-wide announcements. Blocked from verifying own summaries to prevent Karma farming.
3. **Platform Administrator (`admin`)**:
   - Full access to `/admin` operations: User management, course creation, resource moderation, official deadlines, feature controls, and data exports.
4. **Super Administrator (`superadmin`)**:
   - Full platform governance: Permanent course deletions, administrative role promotions, and platform-wide emergency maintenance mode.

---

## 🚀 Quickstart & Local Development

### 1. Prerequisites
* Python 3.10+
* Git

### 2. Setup Environment
```powershell
# Clone the repository
git clone https://github.com/sumit07122/Classcatch.git
cd Classcatch

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Database
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://neondb_owner:npg_1aH6lbvWfhzc@ep-divine-heart-aeteyc0r-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require
SECRET_KEY=classcatch-production-secret-2026
```
*(If `DATABASE_URL` is omitted, ClassCatch automatically defaults to local SQLite `sqlite:///classcatch.db`).*

### 4. Run Automated Test Suite
Run the 20 comprehensive end-to-end and RBAC test suites:
```powershell
python test_app.py
```

### 5. Start Development Server
```powershell
python app.py
# Server runs at http://127.0.0.1:5000
```

---

## 🔑 Demo & Test Credentials

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `superadmin@classcatch.edu` | `password123` | Full Platform & System Control (`/admin`) |
| **Admin** | `admin@classcatch.edu` | `password123` | Administrative Control Center (`/admin`) |
| **Class Rep (CR)** | `alex@classcatch.edu` | `password123` | CR for CSE-301 & Verified Contributor |
| **Student 1** | `sarah@classcatch.edu` | `password123` | Standard Student Profile |
| **Student 2** | `david@classcatch.edu` | `password123` | Standard Student Profile |

---

## 🛠️ CLI Management Utilities

### Create / Elevate a SuperAdmin
Create a new administrator or elevate an existing student account:
```powershell
python clean_slate.py --create-admin --name "Dean of Academics" --email "admin@college.edu" --password "securepassword123"
```

### Clean Mock Data for Production Launch
```powershell
# Clear dummy activity but preserve courses, timetables, and system settings:
python clean_slate.py --activity-only

# Complete factory reset:
python clean_slate.py --full-reset
```

---

## ☁️ Production Deployment (Vercel — $0 Tier)

1. Push your code to GitHub: `https://github.com/sumit07122/Classcatch.git`.
2. Navigate to [Vercel](https://vercel.com/) and click **New Project** $\rightarrow$ Import `sumit07122/Classcatch`.
3. Under **Environment Variables**, add:
   * `DATABASE_URL` = your Neon Serverless Postgres connection string.
   * `SECRET_KEY` = any secure random 32-character string.
4. Click **Deploy**. Vercel will deploy ClassCatch with automatic SSL.

---

## 📱 Google Play Store (PWABuilder Android TWA)

ClassCatch includes full Google Play compliance fixtures:
* `manifest.json` & PWA Service Worker caching (`static/sw.js`).
* Digital Asset Links (`/.well-known/assetlinks.json`) for full-screen chrome-less operation.
* Mandatory Privacy Policy (`/privacy`) and Terms of Service (`/terms`).

**Packaging Steps:**
1. Open [PWABuilder.com](https://www.pwabuilder.com/).
2. Enter your live production URL.
3. Click **Package for Android** to generate your signed `app-release.aab` ready for upload to the Google Play Developer Console. Reference [PLAY_STORE_PACKAGE_GUIDE.md](file:///c:/Users/hp/OneDrive/Desktop/gla/PLAY_STORE_PACKAGE_GUIDE.md) for full release details.
