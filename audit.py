import hashlib
import json
import time

GENESIS = "0" * 64

def _hash(prev, ts, actor, action, target, detail):
    payload = json.dumps([prev, ts, actor, action, target, detail],
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()

def log_event(db, actor, action, target="", detail=""):
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    prev = row["hash"] if row else GENESIS
    ts = int(time.time())
    h = _hash(prev, ts, actor, action, target, detail)
    db.execute(
        "INSERT INTO audit(ts,actor,action,target,detail,prev_hash,hash) "
        "VALUES (?,?,?,?,?,?,?)",
        (ts, actor, action, target, detail, prev, h))
    db.execute("COMMIT")

def verify_chain(db):
    prev = GENESIS
    for r in db.execute("SELECT * FROM audit ORDER BY id").fetchall():
        expected = _hash(prev, r["ts"], r["actor"], r["action"],
                         r["target"], r["detail"])
        if r["prev_hash"] != prev or r["hash"] != expected:
            return False, r["id"]
        prev = r["hash"]
    return True, None