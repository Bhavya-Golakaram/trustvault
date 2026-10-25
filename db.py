import os
import sqlite3
from flask import g

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE, "trustvault.db"))


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, isolation_level=None)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    con = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE, "schema.sql")) as f:
        con.executescript(f.read())
    try:
        con.execute("ALTER TABLE users ADD COLUMN recovery_hash TEXT")
        con.commit()
    except sqlite3.OperationalError:
        pass
    con.close()