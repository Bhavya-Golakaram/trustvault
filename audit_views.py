from flask import Blueprint, render_template, redirect, url_for, session
from db import get_db
from audit import verify_chain

bp = Blueprint("audit_views", __name__)


@bp.route("/audit")
def audit_page():
    uid = session.get("user_id")
    if uid is None:
        return redirect(url_for("login"))
    db = get_db()
    user = db.execute(
        "SELECT id, email FROM users WHERE id = ?", (uid,)).fetchone()
    if user is None:
        return redirect(url_for("login"))
    rows = db.execute(
        "SELECT id, ts, actor, action, target, hash FROM audit "
        "WHERE actor = ? ORDER BY id DESC LIMIT 100",
        (user["email"],)).fetchall()
    ok, bad_id = verify_chain(db)
    head = db.execute(
        "SELECT id, hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    total = db.execute("SELECT COUNT(*) AS n FROM audit").fetchone()["n"]
    return render_template("audit.html", user=user, rows=rows, ok=ok,
                           bad_id=bad_id, head=head, total=total)