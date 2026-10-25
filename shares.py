import os
import time
import secrets
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, abort, send_from_directory)
from db import get_db
from audit import log_event

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE, "uploads"))

bp = Blueprint("shares", __name__)


def _user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute(
        "SELECT id, email FROM users WHERE id = ?", (uid,)).fetchone()


def _problem(s, user):
    """Return a message if this share cannot be used, otherwise None."""
    if s["revoked"]:
        return "The owner has revoked this link."
    if time.time() > s["expires_at"]:
        return "This link has expired."
    if s["views"] >= s["max_views"]:
        return "The download limit for this link has been reached."
    if user["email"] != s["recipient_email"]:
        return "This link was shared with a different email address."
    return None


@bp.route("/share/<int:doc_id>", methods=["GET", "POST"])
def share_page(doc_id):
    user = _user()
    if not user:
        return redirect(url_for("login"))
    db = get_db()
    doc = db.execute("SELECT * FROM documents WHERE id = ?",
                     (doc_id,)).fetchone()
    if doc is None:
        abort(404)
    if doc["owner_id"] != user["id"]:
        log_event(db, user["email"], "share_denied", str(doc_id))
        abort(403)

    new_link = None
    new_email = None
    if request.method == "POST":
        email = request.form.get("recipient", "").strip().lower()
        try:
            hours = int(request.form.get("hours", "24"))
            max_views = int(request.form.get("max_views", "3"))
        except ValueError:
            hours, max_views = 0, 0
        if "@" not in email or len(email) < 5:
            flash("Enter the recipient's email address.")
        elif not (1 <= hours <= 168) or not (1 <= max_views <= 20):
            flash("Choose a valid time limit and download limit.")
        else:
            token = secrets.token_urlsafe(24)
            expires = int(time.time()) + hours * 3600
            db.execute(
                "INSERT INTO shares(doc_id, token, recipient_email, "
                "expires_at, max_views) VALUES (?,?,?,?,?)",
                (doc_id, token, email, expires, max_views))
            log_event(db, user["email"], "share_create", doc["original_name"],
                      "to=%s hours=%d max_downloads=%d"
                      % (email, hours, max_views))
            new_link = url_for("shares.open_share", token=token,
                               _external=True)
            new_email = email

    rows = db.execute("SELECT * FROM shares WHERE doc_id = ? ORDER BY id DESC",
                      (doc_id,)).fetchall()
    now = time.time()
    shares = []
    for r in rows:
        if r["revoked"]:
            status = "Revoked"
        elif now > r["expires_at"]:
            status = "Expired"
        elif r["views"] >= r["max_views"]:
            status = "Used up"
        else:
            status = "Active"
        shares.append({"id": r["id"], "email": r["recipient_email"],
                       "expires_at": r["expires_at"], "views": r["views"],
                       "max_views": r["max_views"], "status": status})
    return render_template("share.html", doc=doc, shares=shares,
                           new_link=new_link, new_email=new_email)


@bp.route("/share/revoke/<int:share_id>", methods=["POST"])
def revoke(share_id):
    user = _user()
    if not user:
        return redirect(url_for("login"))
    db = get_db()
    row = db.execute(
        "SELECT s.id, s.doc_id, d.owner_id, d.original_name FROM shares s "
        "JOIN documents d ON d.id = s.doc_id WHERE s.id = ?",
        (share_id,)).fetchone()
    if row is None:
        abort(404)
    if row["owner_id"] != user["id"]:
        log_event(db, user["email"], "revoke_denied", str(share_id))
        abort(403)
    db.execute("UPDATE shares SET revoked = 1 WHERE id = ?", (share_id,))
    log_event(db, user["email"], "share_revoke", row["original_name"])
    flash("Link revoked.")
    return redirect(url_for("shares.share_page", doc_id=row["doc_id"]))


def _load(token):
    return get_db().execute(
        "SELECT s.*, d.original_name, d.stored_name, u.email AS owner_email "
        "FROM shares s JOIN documents d ON d.id = s.doc_id "
        "JOIN users u ON u.id = d.owner_id WHERE s.token = ?",
        (token,)).fetchone()


@bp.route("/s/<token>")
def open_share(token):
    s = _load(token)
    if s is None:
        abort(404)
    user = _user()
    if user is None:
        flash("Log in with the email address this link was shared with, "
              "then open the link again.")
        return redirect(url_for("login"))
    problem = _problem(s, user)
    if problem:
        log_event(get_db(), user["email"], "share_open_refused",
                  s["original_name"], problem)
    return render_template("shared_view.html", s=s, problem=problem)


@bp.route("/s/<token>/download")
def share_download(token):
    s = _load(token)
    if s is None:
        abort(404)
    user = _user()
    if user is None:
        return redirect(url_for("login"))
    db = get_db()
    problem = _problem(s, user)
    if problem:
        log_event(db, user["email"], "share_download_refused",
                  s["original_name"], problem)
        flash(problem)
        return redirect(url_for("shares.open_share", token=token))
    cur = db.execute(
        "UPDATE shares SET views = views + 1 WHERE id = ? AND revoked = 0 "
        "AND views < max_views AND expires_at >= ?",
        (s["id"], int(time.time())))
    if cur.rowcount != 1:
        flash("This link can no longer be used.")
        return redirect(url_for("shares.open_share", token=token))
    log_event(db, user["email"], "share_download", s["original_name"],
              "owner=" + s["owner_email"])
    return send_from_directory(UPLOAD_DIR, s["stored_name"],
                               as_attachment=True,
                               download_name=s["original_name"])