import json
import os
import sqlite3
import sys

from db import DB_PATH

BASE = os.path.dirname(os.path.abspath(__file__))
BACKUP = os.path.join(BASE, "tamper_backup.json")

print("Using database:", DB_PATH)
con = sqlite3.connect(DB_PATH)

has_audit = con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='audit'"
).fetchone()
if not has_audit:
    print("This database has no audit table.")
    print("Start the app once with: python app.py")
    print("Then register, log in, and run this demo again.")
    sys.exit()

if len(sys.argv) > 1 and sys.argv[1] == "restore":
    if not os.path.exists(BACKUP):
        print("Nothing to restore.")
        sys.exit()
    with open(BACKUP) as f:
        saved = json.load(f)
    con.execute("UPDATE audit SET action = ? WHERE id = ?",
                (saved["action"], saved["id"]))
    con.commit()
    os.remove(BACKUP)
    print("Restored event", saved["id"], "to", saved["action"])
else:
    row = con.execute(
        "SELECT id, action FROM audit ORDER BY id LIMIT 1 OFFSET 1").fetchone()
    if row is None:
        row = con.execute("SELECT id, action FROM audit LIMIT 1").fetchone()
    if row is None:
        print("The audit log is empty. Register and log in first.")
        sys.exit()
    with open(BACKUP, "w") as f:
        json.dump({"id": row[0], "action": row[1]}, f)
    con.execute("UPDATE audit SET action = 'FORGED' WHERE id = ?", (row[0],))
    con.commit()
    print("Event", row[0], "changed from", row[1], "to FORGED")
    print("Now open the Audit log page and check the card.")