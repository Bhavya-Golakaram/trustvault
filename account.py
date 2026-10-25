from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db
from audit import log_event

bp = Blueprint("account", __name__)


@bp.route("/account", methods=["GET", "POST"])
def account_page():
    uid = session.get("user_id")
    if uid is None:
        return redirect(url_for("login"))
    db = get_db()
    user = db.execute("SELECT id, email, pw_hash FROM users WHERE id = ?",
                      (uid,)).fetchone()
    if user is None:
        return redirect(url_for("login"))

    if request.method == "POST":
        current = request.form.get("current", "")
        new = request.form.get("new", "")
        if not check_password_hash(user["pw_hash"], current):
            log_event(db, user["email"], "password_change_failed",
                      user["email"])
            flash("Your current password is wrong.")
        elif len(new) < 8:
            flash("The new password must be at least 8 characters.")
        elif new == current:
            flash("Choose a password different from the current one.")
        else:
            db.execute("UPDATE users SET pw_hash = ? WHERE id = ?",
                       (generate_password_hash(new), uid))
            log_event(db, user["email"], "password_changed", user["email"])
            flash("Password changed.")
        return redirect(url_for("account.account_page"))

    n_docs = db.execute("SELECT COUNT(*) AS n FROM documents WHERE owner_id = ?",
                        (uid,)).fetchone()["n"]
    n_shares = db.execute(
        "SELECT COUNT(*) AS n FROM shares s JOIN documents d ON d.id = s.doc_id "
        "WHERE d.owner_id = ?", (uid,)).fetchone()["n"]
    n_events = db.execute("SELECT COUNT(*) AS n FROM audit WHERE actor = ?",
                          (user["email"],)).fetchone()["n"]
    return render_template("account.html", email=user["email"], n_docs=n_docs,
                           n_shares=n_shares, n_events=n_events)