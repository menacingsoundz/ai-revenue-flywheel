"""SQLite storage for the AI Revenue Flywheel. Stdlib sqlite3 only."""
import hashlib, json, os, sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get("FLYWHEEL_DB", os.path.join(os.path.dirname(__file__), "..", "data", "flywheel.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
  category TEXT, description TEXT, price_cents INTEGER NOT NULL, status TEXT DEFAULT 'draft',
  qc_status TEXT DEFAULT 'pending', file_path TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS product_files(
  id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, filename TEXT, path TEXT,
  file_type TEXT, size_bytes INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS qc_checks(
  id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, passed INTEGER, checks_json TEXT,
  notes TEXT, checked_at TEXT);
CREATE TABLE IF NOT EXISTS marketing_drafts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE, kind TEXT, title TEXT, body TEXT,
  status TEXT DEFAULT 'draft', created_at TEXT);
CREATE TABLE IF NOT EXISTS publishing_queue(
  id INTEGER PRIMARY KEY AUTOINCREMENT, draft_id INTEGER, channel TEXT, copy_text TEXT,
  link TEXT, status TEXT DEFAULT 'queued', created_at TEXT);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT DEFAULT 'manual', external_id TEXT,
  product_slug TEXT, amount_cents INTEGER, fee_cents INTEGER DEFAULT 0,
  refund_cents INTEGER DEFAULT 0, is_test INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS expenses(
  id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, amount_cents INTEGER,
  category TEXT, is_test INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS financial_ledger(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, label TEXT, amount_cents INTEGER,
  created_at TEXT);
CREATE TABLE IF NOT EXISTS agent_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, job TEXT, status TEXT,
  detail TEXT, started_at TEXT, finished_at TEXT);
CREATE TABLE IF NOT EXISTS decision_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, decision TEXT, reason TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, summary TEXT, payload_json TEXT,
  status TEXT DEFAULT 'pending', requested_at TEXT, decided_at TEXT, decided_by TEXT);
CREATE TABLE IF NOT EXISTS schedules(
  id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT UNIQUE, name TEXT, weekday TEXT,
  time_local TEXT, enabled INTEGER DEFAULT 1, last_run TEXT, config_json TEXT);
CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS activity_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, detail TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS error_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, message TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS research(
  id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT, opportunity TEXT, score INTEGER,
  evidence TEXT, sources_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS llm_usage(
  id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, model TEXT, calls INTEGER DEFAULT 1,
  day TEXT, created_at TEXT);
"""

def now():
    return datetime.now(timezone.utc).isoformat()

def connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = connect()
    c.executescript(SCHEMA)
    c.commit(); c.close()

def slug_hash(text):
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]

def log_activity(actor, action, detail=""):
    c = connect(); c.execute("INSERT INTO activity_log(actor,action,detail,created_at) VALUES(?,?,?,?)",
        (actor, action, detail, now())); c.commit(); c.close()

def log_error(source, message):
    c = connect(); c.execute("INSERT INTO error_log(source,message,created_at) VALUES(?,?,?)",
        (source, str(message)[:2000], now())); c.commit(); c.close()

def get_setting(key, default=None):
    c = connect(); r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone(); c.close()
    return r["value"] if r else default

def set_setting(key, value):
    c = connect()
    c.execute("INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
              (key, str(value), now()))
    c.commit(); c.close()
