import os
import re
import uuid
import threading
import time
import json
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import yt_dlp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production-please")
CORS(app)

DOWNLOAD_DIR = "/tmp/snaplink_downloads"
DB_PATH = os.environ.get("DB_PATH", "/tmp/snaplink_users.json")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme123")

# Write YouTube cookies from environment variable to a temp file
COOKIES_FILE = None
youtube_cookies = os.environ.get("YOUTUBE_COOKIES", "").strip()
if youtube_cookies:
    COOKIES_FILE = "/tmp/youtube_cookies.txt"
    with open(COOKIES_FILE, "w") as f:
        f.write(youtube_cookies)

PLATFORM_PATTERNS = {
    "tiktok":    [r"tiktok\.com", r"vm\.tiktok\.com", r"vt\.tiktok\.com"],
    "youtube":   [r"youtube\.com", r"youtu\.be"],
    "instagram": [r"instagram\.com", r"instagr\.am"],
    "twitter":   [r"twitter\.com", r"x\.com", r"t\.co"],
    "facebook":  [r"facebook\.com", r"fb\.watch", r"fb\.com"],
}

def detect_platform(url):
    for platform, patterns in PLATFORM_PATTERNS.items():
        for p in patterns:
            if re.search(p, url, re.IGNORECASE):
                return platform
    return "unknown"

def load_db():
    if not os.path.exists(DB_PATH):
        return {"users": {}, "pending": {}}
    try:
        with open(DB_PATH) as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "pending": {}}

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)

def init_db():
    db = load_db()
    if ADMIN_USERNAME not in db["users"]:
        db["users"][ADMIN_USERNAME] = {
            "username": ADMIN_USERNAME,
            "password": generate_password_hash(ADMIN_PASSWORD),
            "role": "admin",
            "approved": True,
            "created_at": datetime.utcnow().isoformat(),
            "download_count": 0,
        }
        save_db(db)

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("username"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

def cleanup_old_files():
    while True:
        now = time.time()
        for fname in os.listdir(DOWNLOAD_DIR):
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 600:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
        time.sleep(120)

threading.Thread(target=cleanup_old_files, daemon=True).start()

@app.route("/")
@login_required
def index():
    return render_template("index.html", username=session.get("username"), role=session.get("role"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("username"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        db = load_db()
        user = db["users"].get(username)
        if user and check_password_hash(user["password"], password):
            if not user.get("approved"):
                error = "Your account is pending approval."
            else:
                session["username"] = username
                session["role"] = user.get("role", "user")
                return redirect(url_for("index"))
        else:
            error = "Incorrect username or password."
    return render_template("login.html", error=error)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("username"):
        return redirect(url_for("index"))
    error = None
    success = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        note     = request.form.get("note", "").strip()
        if not username or not password:
            error = "Please fill in all fields."
        elif len(username) < 3 or not re.match(r'^[a-z0-9_]+$', username):
            error = "Username must be 3+ characters: letters, numbers, underscores only."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            db = load_db()
            if username in db["users"] or username in db["pending"]:
                error = "That username is already taken."
            else:
                db["pending"][username] = {
                    "username": username,
                    "password": generate_password_hash(password),
                    "note": note,
                    "requested_at": datetime.utcnow().isoformat(),
                }
                save_db(db)
                success = "Request submitted! The admin will review your account shortly."
    return render_template("signup.html", error=error, success=success)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
@admin_required
def admin():
    db = load_db()
    users   = list(db["users"].values())
    pending = list(db["pending"].values())
    return render_template("admin.html", users=users, pending=pending,
                           admin_username=session.get("username"))

@app.route("/admin/approve/<username>", methods=["POST"])
@admin_required
def approve_user(username):
    db = load_db()
    if username in db["pending"]:
        user_data = db["pending"].pop(username)
        db["users"][username] = {
            "username": username,
            "password": user_data["password"],
            "role": "user",
            "approved": True,
            "created_at": datetime.utcnow().isoformat(),
            "download_count": 0,
        }
        save_db(db)
        flash(f"{username} approved.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/reject/<username>", methods=["POST"])
@admin_required
def reject_user(username):
    db = load_db()
    if username in db["pending"]:
        db["pending"].pop(username)
        save_db(db)
        flash(f"{username}'s request rejected.", "info")
    return redirect(url_for("admin"))

@app.route("/admin/remove/<username>", methods=["POST"])
@admin_required
def remove_user(username):
    db = load_db()
    if username == session.get("username"):
        flash("You cannot remove yourself.", "error")
        return redirect(url_for("admin"))
    if username in db["users"]:
        db["users"].pop(username)
        save_db(db)
        flash(f"{username} removed.", "info")
    return redirect(url_for("admin"))

@app.route("/admin/promote/<username>", methods=["POST"])
@admin_required
def promote_user(username):
    db = load_db()
    if username in db["users"]:
        db["users"][username]["role"] = "admin"
        save_db(db)
        flash(f"{username} promoted to admin.", "success")
    return redirect(url_for("admin"))

@app.route("/api/download", methods=["POST"])
@login_required
def download():
    data    = request.get_json()
    url     = data.get("url", "").strip()
    quality = data.get("quality", "best")
    if not url:
        return jsonify({"error": "No URL provided."}), 400

    platform = detect_platform(url)
    job_id   = str(uuid.uuid4())[:8]
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}_%(title).60s.%(ext)s")

    # Platform-aware format selection
    if quality == "audio":
        format_str = "bestaudio/best"
    elif platform == "youtube":
        if quality == "720":
            format_str = "(bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a])/(bestvideo[height<=720]+bestaudio)/best[height<=720]/best"
        elif quality == "480":
            format_str = "(bestvideo[height<=480][vcodec^=avc1]+bestaudio[acodec^=mp4a])/(bestvideo[height<=480]+bestaudio)/best[height<=480]/best"
        else:
            format_str = "(bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a])/(bestvideo+bestaudio)/best"
    else:
        if quality == "720":
            format_str = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif quality == "480":
            format_str = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        else:
            format_str = "bestvideo+bestaudio/best"

    ydl_opts = {
        "format": format_str,
        "outtmpl": out_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 3,
    }

    # YouTube-specific settings
    if platform == "youtube":
        ydl_opts["merge_output_format"] = "mp4"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }]
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            ydl_opts["cookiefile"] = COOKIES_FILE
    else:
        ydl_opts["merge_output_format"] = "mp4"

    if quality == "audio":
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:
                info = info["entries"][0]
            title = info.get("title", "video")
            ext   = "mp3" if quality == "audio" else "mp4"

        downloaded = None
        for fname in os.listdir(DOWNLOAD_DIR):
            if fname.startswith(job_id):
                downloaded = os.path.join(DOWNLOAD_DIR, fname)
                break

        if not downloaded or not os.path.exists(downloaded):
            return jsonify({"error": "Download failed — file not found after processing."}), 500

        db = load_db()
        uname = session.get("username")
        if uname and uname in db["users"]:
            db["users"][uname]["download_count"] = db["users"][uname].get("download_count", 0) + 1
            save_db(db)

        safe_title = re.sub(r'[^\w\s\-]', '', title).strip()[:60]
        filename   = f"{safe_title}.{ext}" if safe_title else f"video.{ext}"

        return send_file(
            downloaded,
            as_attachment=True,
            download_name=filename,
            mimetype="audio/mpeg" if quality == "audio" else "video/mp4"
        )

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Private" in msg or "login" in msg.lower():
            return jsonify({"error": "This video is private or requires login."}), 400
        if "Unsupported URL" in msg:
            return jsonify({"error": "This URL is not supported."}), 400
        if "not available" in msg.lower() or "format" in msg.lower():
            return jsonify({"error": "This format is not available for that video. Try a different quality setting."}), 400
        return jsonify({"error": f"Download failed: {msg[:200]}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)[:200]}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
