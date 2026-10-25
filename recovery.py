import time
import secrets
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db
from audit import log_event

bp = Blueprint("recovery", __name__)


def _new_code():
    raw = secrets.token_hex(8).upper()
    return "-".join(raw[i:i + 4] for i in range(0, 16, 4))


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        code = request.form.get("code", "").strip().upper()
        new = request.form.get("new", "")
        db = get_db()
        since = int(time.time()) - 900
        fails = db.execute(
            "SELECT COUNT(*) AS n FROM audit WHERE actor = ? "
            "AND action = 'reset_failed' AND ts > ?",
            (email or "unknown", since)).fetchone()["n"]
        if fails >= 5:
            flash("Too many failed attempts. Try again in 15 minutes.")
            return redirect(url_for("recovery.forgot"))
        user = db.execute(
            "SELECT id, recovery_hash FROM users WHERE email = ?",
            (email,)).fetchone()
        if len(new) < 8:
            flash("The new password must be at least 8 characters.")
        elif (user and user["recovery_hash"]
              and check_password_hash(user["recovery_hash"], code)):
            db.execute(
                "UPDATE users SET pw_hash = ?, recovery_hash = NULL "
                "WHERE id = ?", (generate_password_hash(new), user["id"]))
            log_event(db, email, "password_reset", email)
            flash("Password reset. Log in with your new password, then "
                  "create a new recovery code on the Account page.")
            return redirect(url_for("login"))
        else:
            log_event(db, email or "unknown", "reset_failed", email)
            flash("Email or recovery code is wrong.")
    return render_template("forgot.html")


@bp.route("/account/recovery", methods=["POST"])
def make_code():
    uid = session.get("user_id")
    if uid is None:
        return redirect(url_for("login"))
    db = get_db()
    user = db.execute("SELECT email FROM users WHERE id = ?",
                      (uid,)).fetchone()
    if user is None:
        return redirect(url_for("login"))
    code = _new_code()
    db.execute("UPDATE users SET recovery_hash = ? WHERE id = ?",
               (generate_password_hash(code), uid))
    log_event(db, user["email"], "recovery_code_created", user["email"])
    return render_template("recovery_code.html", code=code)