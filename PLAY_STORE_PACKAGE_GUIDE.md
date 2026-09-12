# 🚀 ClassCatch: Google Play Store & Supabase Deployment Playbook

This complete guide will take your ClassCatch project from local development to a live production database on **Supabase** and publish it as an official Android app on the **Google Play Store**.

---

## 📑 Table of Contents
1. [Step 1: Connect Supabase PostgreSQL Database](#step-1-connect-supabase-postgresql-database)
2. [Step 2: Deploy Web App Live (Render / Railway)](#step-2-deploy-web-app-live-render--railway)
3. [Step 3: Generate Android Bundle (.aab) with PWABuilder](#step-3-generate-android-bundle-aab-with-pwabuilder)
4. [Step 4: Release on Google Play Console](#step-4-release-on-google-play-console)
5. [Step 5: Digital Asset Links Verification](#step-5-digital-asset-links-verification)

---

## Step 1: Connect Supabase PostgreSQL Database

1. Sign up / log in to [Supabase](https://supabase.com/).
2. Click **New Project**:
   - **Name:** `classcatch`
   - **Database Password:** Enter a strong password (keep this safe).
   - **Region:** Select the region closest to your college (e.g. `ap-south-1` Mumbai).
3. Once the database is ready (~1 minute):
   - Navigate to **Project Settings** (gear icon) $\rightarrow$ **Database**.
   - Under **Connection String**, select **URI** (or **Session Pooler** on port `6543`).
   - Copy the string. It looks like:
     ```text
     postgresql://postgres.[YOUR-REF]:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
     ```
4. On your local machine, open or create `.env`:
   ```env
   DATABASE_URL=postgresql://postgres.[YOUR-REF]:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   SECRET_KEY=your-random-production-secret-key-2026
   ANDROID_PACKAGE_NAME=com.classcatch.app
   ```
5. Run the 1-click database setup script:
   ```powershell
   python supabase_setup.py
   ```
   *This automatically builds all tables (`users`, `courses`, `summaries`, `deadlines`, `resources`, `chat_messages`, etc.) and seeds default demo data.*

---

## Step 2: Deploy Web App Live (Render / Railway)

### Deploying on Render (Free Tier):
1. Push your repository to GitHub:
   ```powershell
   git add .
   git commit -m "Ready for production"
   git push origin main
   ```
2. Go to [Render Dashboard](https://dashboard.render.com/) $\rightarrow$ **New +** $\rightarrow$ **Web Service**.
3. Connect your GitHub repository.
4. Fill in the build settings:
   - **Name:** `classcatch`
   - **Region:** Ohio or Frankfurt (or nearest)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python supabase_setup.py`
   - **Start Command:** `gunicorn app:app`
5. Under **Environment Variables**, add:
   - `DATABASE_URL`: *(Your Supabase connection string)*
   - `SECRET_KEY`: *(Your secure secret string)*
   - `ANDROID_PACKAGE_NAME`: `com.classcatch.app`
6. Click **Deploy Web Service**.
7. In ~2 minutes, your web application will be live at:
   `https://classcatch.onrender.com`

---

## Step 3: Generate Android Bundle (.aab) with PWABuilder

Google Play requires an `.aab` (Android App Bundle). You can generate one in 5 minutes with zero Java/Kotlin coding using **PWABuilder** (maintained by Microsoft & Google):

1. Open [PWABuilder.com](https://www.pwabuilder.com/) in your browser.
2. Enter your live HTTPS URL (e.g. `https://classcatch.onrender.com`) and click **Start**.
3. PWABuilder will test your PWA:
   - Manifest: ✅ Verified
   - Service Worker: ✅ Verified
   - Security: ✅ Verified
4. Click **Package for Store** $\rightarrow$ select **Android**.
5. Customize your app options:
   - **Package ID:** `com.classcatch.app`
   - **App Name:** `ClassCatch`
   - **Theme Color:** `#4361ee`
   - **Background Color:** `#0d1117`
   - **Signing Key:** Choose **"Generate new key"** (download and backup the generated `.keystore` file).
6. Click **Generate Bundle**.
7. Download the `.zip` archive. Inside you will find:
   - `app-release.aab` (Ready to upload to Google Play)
   - `assetlinks.json` (Contains your signing certificate fingerprint)

---

## Step 4: Release on Google Play Console

1. Go to [Google Play Console](https://play.google.com/console) and create a developer account ($25 one-time registration fee).
2. Click **Create App**:
   - **App Name:** `ClassCatch: College Catch-up & Attendance Hub`
   - **Default Language:** `English (United States)` or `English (India)`
   - **Type:** `App`
   - **Price:** `Free`
3. Complete the **Store Presence** requirements:
   - **Short Description:** *Peer-powered class catch-up notes, attendance & bunk predictor, and student hub.*
   - **Full Description:** Describe your course catch-ups, blackboard photo OCR scanner, anonymous doubt box, exam countdowns, and PYQ vault.
   - **App Icon:** 512x512 PNG.
   - **Feature Graphic:** 1024x500 PNG.
   - **Screenshots:** Upload 4–8 phone screenshots from your app.
4. Set Up **App Content**:
   - **Privacy Policy URL:** `https://your-domain.com/privacy` *(Already implemented & live!)*
   - **Target Audience:** 18+ (College students).
   - **Content Rating Questionnaire:** Fill in the questionnaire (Everything is educational; will receive "Everyone / PEGI 3" rating).
5. Upload the Build:
   - Go to **Release** $\rightarrow$ **Production** $\rightarrow$ **Create New Release**.
   - Upload `app-release.aab`.
   - Release Name: `1.0.0`.
   - Click **Save** $\rightarrow$ **Review Release** $\rightarrow$ **Rollout to Production**.

---

## Step 5: Digital Asset Links Verification

To ensure your app opens in **true native full-screen mode** without an address bar:
1. Open Google Play Console $\rightarrow$ **App Integrity** $\rightarrow$ **App Signing**.
2. Copy the **SHA-256 certificate fingerprint**.
3. In your server environment variables (Render / `.env`), set:
   ```env
   ANDROID_SHA256_FINGERPRINT="14:6D:E9:7F:0F:7B:64:99..."
   ```
4. Verify by visiting `https://your-domain.com/.well-known/assetlinks.json` in your browser. It will output your app's verified signature.

---

## 🛠️ Tech Stack Summary
- **Backend Framework:** Python 3.13 / Flask 3.1
- **WSGI Production Server:** Gunicorn
- **Database:** Supabase Managed PostgreSQL (with connection pooling)
- **Mobile Engine:** Progressive Web App (PWA) + Android Trusted Web Activity (TWA)
- **Styling:** Plus Jakarta Sans typography, Bootstrap 5.3, custom glassmorphism & cards
- **Real-Time Features:** Attendance Bunk Predictor, Blackboard OCR Parser, Anonymous Doubts, CR Verification Seal, WhatsApp Briefing Dispatcher
