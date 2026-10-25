import time
from flask import Blueprint, session
from db import get_db
from audit import verify_chain

bp = Blueprint("ui", __name__)


@bp.app_context_processor
def vault_info():
    uid = session.get("user_id")
    if uid is None:
        return {}
    db = get_db()
    u = db.execute("SELECT email FROM users WHERE id = ?", (uid,)).fetchone()
    if u is None:
        return {}
    ok, bad_id = verify_chain(db)
    total = db.execute("SELECT COUNT(*) AS n FROM audit").fetchone()["n"]
    active = db.execute(
        "SELECT COUNT(*) AS n FROM shares s JOIN documents d ON d.id = s.doc_id "
        "WHERE d.owner_id = ? AND s.revoked = 0 AND s.views < s.max_views "
        "AND s.expires_at >= ?", (uid, int(time.time()))).fetchone()["n"]
    recent = db.execute(
        "SELECT ts, action, target FROM audit WHERE actor = ? "
        "ORDER BY id DESC LIMIT 5", (u["email"],)).fetchall()
    chain = list(reversed(db.execute(
        "SELECT id, hash FROM audit ORDER BY id DESC LIMIT 4").fetchall()))
    return {"me": u["email"], "v": {"ok": ok, "bad_id": bad_id, "total": total,
            "active": active, "recent": recent, "chain": chain}}