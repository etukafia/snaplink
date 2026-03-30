# SnapLink — Deployment Guide (Multi-User Edition)
## Deploy to Railway (Free, No Coding Required)

---

### What You Need Before Starting
- A free GitHub account → https://github.com
- A free Railway account → https://railway.app (sign up with GitHub)

---

## STEP 1 — Upload the Files to GitHub

1. Go to https://github.com and log in
2. Click the "+" button (top right) → "New repository"
3. Name it "snaplink" — leave everything else as default
4. Click "Create repository"
5. On the next page, click "uploading an existing file"
6. Drag and drop ALL files from this zip including the templates/ folder
7. Click "Commit changes"

---

## STEP 2 — Deploy on Railway

1. Go to https://railway.app and log in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your snaplink repository
5. Railway will detect it automatically and start building (~2 minutes)

---

## STEP 3 — Set Your Admin Credentials (IMPORTANT)

1. In Railway, click your project → click the service (the purple box)
2. Click the "Variables" tab
3. Add these variables:

   ADMIN_USERNAME  →  your chosen admin username (e.g. mbu)
   ADMIN_PASSWORD  →  a strong password (e.g. MyP@ss99!)
   SECRET_KEY      →  any random string (e.g. xK9mP2qL5rT8)

4. Click "Deploy" to restart with your settings

---

## STEP 4 — Get Your App URL

1. In Railway → "Settings" tab → "Networking" → "Generate Domain"
2. You'll get a URL like: https://snaplink-production-xxxx.up.railway.app
3. Open it — you'll see the SnapLink login page

---

## STEP 5 — Invite Your Friends

Share your URL with friends. Here's the flow:

1. They visit your URL and click "Request access"
2. They fill in a username, password, and optional note to you
3. YOU log in as admin and visit /admin
4. You see their request — click Approve or Reject
5. They can now log in and use SnapLink!

---

## Admin Panel Features  (visit /admin when logged in as admin)

- Approve or reject pending signup requests
- Remove users at any time
- Promote trusted users to admin
- See each user's download count and join date

---

## Security Notes

- Passwords are securely hashed — even you cannot see them
- Each user has their own account
- Unapproved users see a "pending" message and cannot access the app
- You (the admin) are created automatically on first launch

---

## Railway Free Tier Notes

- 500 hours/month uptime (enough for personal use)
- App may sleep after inactivity — first load after sleep takes ~10 seconds
- For always-on hosting, upgrade to Railway Hobby ($5/month)

---

## Troubleshooting

Problem: Can't log in as admin
Fix: Double-check ADMIN_USERNAME and ADMIN_PASSWORD in Railway Variables

Problem: Friend's request not showing in admin panel
Fix: Refresh the /admin page

Problem: Download fails
Fix: Try a different quality setting; YouTube has extra restrictions

Problem: App won't load
Fix: Click your Railway service → "Logs" tab to see error messages

---

SnapLink — self-hosted, invite-only, private. For personal use only.
