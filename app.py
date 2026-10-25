import os
import uuid
import time
import hashlib
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_from_directory, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db import get_db, close_db, init_db
from audit import log_event

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE, "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED = {"pdf", "png", "jpg", "jpeg", "txt", "docx"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.teardown_appcontext(close_db)
init_db()

from audit_views import bp as audit_bp
app.register_blueprint(audit_bp)
from shares import bp as shares_bp
app.register_blueprint(shares_bp)
from ui import bp as ui_bp
app.register_blueprint(ui_bp)
from account import bp as account_bp
app.register_blueprint(account_bp)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


@app.template_filter("dt")
def format_time(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts)) + " UTC"


@app.errorhandler(413)
def too_large(e):
    flash("File is too large. Maximum size is 5 MB.")
    return redirect(url_for("dashboard"))


def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute(
        "SELECT id, email FROM users WHERE id = ?", (uid,)).fetchone()


@app.route("/")
def home():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if "@" not in email or len(email) < 5:
            flash("Enter a valid email address.")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.")
        else:
            db = get_db()
            exists = db.execute(
                "SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if exists:
                flash("That email is already registered.")
            else:
                db.execute(
                    "INSERT INTO users(email, pw_hash) VALUES (?, ?)",
                    (email, generate_password_hash(password)))
                log_event(db, email, "register", email)
                flash("Account created. Please log in.")
                return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT id, email, pw_hash FROM users WHERE email = ?",
            (email,)).fetchone()
        if user and check_password_hash(user["pw_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            log_event(db, email, "login_ok", email)
            return redirect(url_for("dashboard"))
        log_event(db, email or "unknown", "login_failed", email)
        flash("Wrong email or password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    user = current_user()
    if user:
        log_event(get_db(), user["email"], "logout", user["email"])
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    docs = get_db().execute(
        "SELECT id, original_name, sha256, uploaded_at FROM documents "
        "WHERE owner_id = ? ORDER BY id DESC", (user["id"],)).fetchall()
    return render_template("dashboard.html", user=user, docs=docs)


@app.route("/upload", methods=["POST"])
def upload():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    f = request.files.get("file")
    if not f or f.filename == "":
        flash("Choose a file first.")
        return redirect(url_for("dashboard"))
    original = secure_filename(f.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED:
        flash("File type not allowed. Allowed: " + ", ".join(sorted(ALLOWED)))
        return redirect(url_for("dashboard"))
    stored = uuid.uuid4().hex + "." + ext
    path = os.path.join(UPLOAD_DIR, stored)
    f.save(path)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    db = get_db()
    db.execute(
        "INSERT INTO documents(owner_id, original_name, stored_name, sha256, "
        "uploaded_at) VALUES (?,?,?,?,?)",
        (user["id"], original, stored, digest, int(time.time())))
    log_event(db, user["email"], "upload", original, "sha256=" + digest)
    flash("Uploaded: " + original)
    return redirect(url_for("dashboard"))


@app.route("/download/<int:doc_id>")
def download(doc_id):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?",
                     (doc_id,)).fetchone()
    if doc is None:
        abort(404)
    if doc["owner_id"] != user["id"]:
        log_event(db, user["email"], "download_denied", str(doc_id))
        abort(403)
    log_event(db, user["email"], "download", doc["original_name"])
    return send_from_directory(UPLOAD_DIR, doc["stored_name"],
                               as_attachment=True,
                               download_name=doc["original_name"])


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)