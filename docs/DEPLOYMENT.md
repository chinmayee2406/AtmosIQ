# AtmosIQ — Deployment and Cloud Publishing Guide

This document describes how to deploy AtmosIQ to GitHub and Streamlit Community Cloud.

---

## 1. Local Run Instructions

### Option A: 1-Click Launch (macOS)
Double-click `run_atmosiq.command` in the project root directory.
This script sets environment paths, verifies the virtual environment, launches Streamlit, and opens `http://127.0.0.1:8501` in your browser.

### Option B: Terminal Command
```bash
cd ~/Desktop/AtmosIQ
.venv/bin/streamlit run app/main.py --server.port 8501
```

---

## 2. GitHub Preparation & Push

The local repository is already configured with a comprehensive `.gitignore` ensuring that `.venv`, caches, and temporary files are excluded.

### Step 1: Stage and Commit
```bash
cd ~/Desktop/AtmosIQ
git add .
git commit -m "feat: complete AtmosIQ climate intelligence platform"
```

### Step 2: Create Remote Repository on GitHub
1. Log into your GitHub account at https://github.com/new.
2. Create a new repository named `AtmosIQ`.
3. Keep it Public (or Private as needed). Do **not** initialize with README, .gitignore, or license (already created locally).

### Step 3: Link and Push
```bash
git remote add origin https://github.com/<your-username>/AtmosIQ.git
git branch -M main
git push -u origin main
```

---

## 3. Streamlit Community Cloud Deployment

1. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your GitHub account.
2. Click **New app**.
3. Select your repository: `<your-username>/AtmosIQ`.
4. Branch: `main`.
5. Main file path: `app/main.py`.
6. Advanced settings:
   - Python version: `3.11`
7. Click **Deploy!**.

Streamlit Cloud will automatically install dependencies from `requirements.txt` and launch the app with a public URL (e.g., `https://<your-username>-atmosiq.streamlit.app`).
