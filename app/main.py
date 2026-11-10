"""FastAPI app: serves the mobile dashboard + JSON API. No secrets in any response.
Auth: if ADMIN_PASSWORD env is set, mutating/approval endpoints require header
X-Admin-Token matching it (login endpoint issues it). Reads are open on localhost."""
import hashlib, hmac, json, os, secrets
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import db, llm, finance
from app.agents import AGENTS
from app.seed import seed
from app.scheduler import run_job, load_config
from app.products import BUILDERS

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
STATIC = os.path.join(ROOT, "static")

app = FastAPI(title="AI Revenue Flywheel", version="1.0.0")
TOKENS = set()

def require_auth(request: Request):
    pw = os.environ.get("ADMIN_PASSWORD", "")
    if not pw:
        return True
    tok = request.headers.get("X-Admin-Token", "")
    if tok in TOKENS:
        return True
    raise HTTPException(401, "Admin token required. Log in from Settings.")

def rows(q, args=()):
    c = db.connect(); r = [dict(x) for x in c.execute(q, args).fetchall()]; c.close(); return r

def one(q, args=()):
    c = db.connect(); r = c.execute(q, args).fetchone(); c.close(); return dict(r) if r else None

def write(q, args=()):
    c = db.connect(); cur = c.execute(q, args); c.commit(); lid = cur.lastrowid; c.close(); return lid

@app.on_event("startup")
def startup():
    db.init_db(); seed()

@app.get("/api/health")
def health():
    return {"status": "ok", "llm": llm.provider_status()}

@app.get("/api/dashboard")
def dashboard():
    fin = finance.summary()
    return {"finance": fin, "products": one("SELECT COUNT(*) n, SUM(CASE WHEN status='listed' THEN 1 ELSE 0 END) listed FROM products"),
            "orders": fin["orders"], "llm": llm.provider_status(),
            "gumroad_connected": bool(os.environ.get("GUMROAD_ACCESS_TOKEN")),
            "pending_approvals": one("SELECT COUNT(*) n FROM approvals WHERE status='pending'")["n"],
            "recent_errors": rows("SELECT * FROM error_log ORDER BY id DESC LIMIT 5")}

@app.get("/api/agents")
def agents():
    out = []
    for name, a in AGENTS.items():
        out.append({"name": name, "description": a.description, "status": a.status,
                    "last_run": a.last_run, "errors": a.errors[-3:],
                    "recent": rows("SELECT job,status,detail,started_at FROM agent_runs WHERE agent=? ORDER BY id DESC LIMIT 3", (name,))})
    return out

@app.post("/api/agents/{name}/run")
def run_agent(name: str, request: Request, auth=Depends(require_auth)):
    if name not in AGENTS: raise HTTPException(404, "unknown agent")
    if AGENTS[name].status == "disabled": raise HTTPException(400, "agent disabled")
    return AGENTS[name].run(job="manual")

@app.post("/api/agents/{name}/toggle")
def toggle_agent(name: str, body: dict, auth=Depends(require_auth)):
    if name not in AGENTS: raise HTTPException(404, "unknown agent")
    db.set_setting(f"agent:{name}:enabled", "1" if body.get("enabled") else "0")
    db.log_activity("admin", f"agent {name} {'enabled' if body.get('enabled') else 'disabled'}")
    return {"name": name, "status": AGENTS[name].status}

@app.get("/api/products")
def products():
    return rows("SELECT * FROM products ORDER BY id")

@app.get("/api/products/{slug}")
def product(slug: str):
    p = one("SELECT * FROM products WHERE slug=?", (slug,))
    if not p: raise HTTPException(404, "not found")
    p["files"] = rows("SELECT * FROM product_files WHERE product_id=?", (p["id"],))
    p["qc"] = rows("SELECT * FROM qc_checks WHERE product_id=? ORDER BY id DESC LIMIT 5", (p["id"],))
    return p

class ProductIn(BaseModel):
    title: str; category: str = "template"; description: str; price_cents: int

@app.post("/api/products")
def create_product(body: ProductIn, auth=Depends(require_auth)):
    slug = body.title.lower().replace(" ", "-")[:60]
    slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-")
    if one("SELECT id FROM products WHERE slug=?", (slug,)): raise HTTPException(400, "a product with that slug already exists (dedupe)")
    pid = write("INSERT INTO products(slug,title,category,description,price_cents,status,qc_status,created_at,updated_at) VALUES(?,?,?,?,?,'draft','pending',?,?)",
                (slug, body.title, body.category, body.description, body.price_cents, db.now(), db.now()))
    return one("SELECT * FROM products WHERE id=?", (pid,))

@app.post("/api/products/{slug}/qc")
def qc_product(slug: str, auth=Depends(require_auth)):
    p = one("SELECT * FROM products WHERE slug=?", (slug,))
    if not p: raise HTTPException(404, "not found")
    return AGENTS["quality_control"].check_product(p["id"], slug, p["file_path"])

@app.post("/api/products/{slug}/approve-list")
def approve_list(slug: str, auth=Depends(require_auth)):
    """Listing requires QC pass AND a human approval record. Creates the approval if none exists."""
    p = one("SELECT * FROM products WHERE slug=?", (slug,))
    if not p: raise HTTPException(404, "not found")
    if p["qc_status"] != "passed":
        raise HTTPException(400, "QC gate: product has not passed quality control and cannot be listed.")
    ap = one("SELECT * FROM approvals WHERE kind='publish' AND status='approved' AND json_extract(payload_json,'$.slug')=?", (slug,))
    if not ap:
        aid = write("INSERT INTO approvals(kind,summary,payload_json,status,requested_at) VALUES(?,?,?,?,?)",
                    ("publish", f"Approve listing: {p['title']}", json.dumps({"slug": slug}), "pending", db.now()))
        return {"status": "approval_required", "approval_id": aid, "note": "Human approval required before listing. Approve it in the Approval Queue."}
    write("UPDATE products SET status='listed', updated_at=? WHERE slug=?", (db.now(), slug))
    return one("SELECT * FROM products WHERE slug=?", (slug,))

@app.post("/api/products/{slug}/archive")
def archive(slug: str, auth=Depends(require_auth)):
    write("UPDATE products SET status='archived', updated_at=? WHERE slug=?", (db.now(), slug))
    return {"slug": slug, "status": "archived"}

@app.get("/api/products/{slug}/download")
def download(slug: str):
    p = one("SELECT * FROM products WHERE slug=?", (slug,))
    if not p or not p["file_path"] or not os.path.exists(p["file_path"]):
        raise HTTPException(404, "file not available")
    return FileResponse(p["file_path"], filename=os.path.basename(p["file_path"]))

@app.get("/api/marketing")
def marketing():
    return {"drafts": rows("SELECT * FROM marketing_drafts ORDER BY id"),
            "queue": rows("SELECT q.*, d.title FROM publishing_queue q LEFT JOIN marketing_drafts d ON d.id=q.draft_id ORDER BY q.id")}

@app.post("/api/marketing/generate")
def gen_marketing(auth=Depends(require_auth)):
    return AGENTS["marketing"].run(job="manual")

@app.get("/api/finance")
def fin():
    return {"summary": finance.summary(),
            "orders": rows("SELECT * FROM orders ORDER BY id DESC LIMIT 50"),
            "expenses": rows("SELECT * FROM expenses ORDER BY id DESC LIMIT 50"),
            "ledger": rows("SELECT * FROM financial_ledger ORDER BY id DESC LIMIT 50")}

class OrderIn(BaseModel):
    product_slug: str; amount_cents: int; fee_cents: int = 0; external_id: str = ""; is_test: int = 0

@app.post("/api/orders")
def add_order(body: OrderIn, auth=Depends(require_auth)):
    if body.is_test == 0 and not body.external_id:
        raise HTTPException(400, "Real orders need an external_id (e.g. Gumroad sale id). Use is_test=1 for test orders.")
    oid = write("INSERT INTO orders(source,external_id,product_slug,amount_cents,fee_cents,is_test,created_at) VALUES(?,?,?,?,?,?,?)",
                ("manual", body.external_id or None, body.product_slug, body.amount_cents, body.fee_cents, body.is_test, db.now()))
    return one("SELECT * FROM orders WHERE id=?", (oid,))

class ExpenseIn(BaseModel):
    label: str; amount_cents: int; category: str = "other"; is_test: int = 0

@app.post("/api/expenses")
def add_expense(body: ExpenseIn, auth=Depends(require_auth)):
    if body.amount_cents > int(db.get_setting("spending_limit_cents", "0") or 0) and body.is_test == 0:
        # spending above the $0 limit requires an approved spend approval
        ap = one("SELECT * FROM approvals WHERE kind='spend' AND status='approved' AND json_extract(payload_json,'$.label')=?", (body.label,))
        if not ap:
            aid = write("INSERT INTO approvals(kind,summary,payload_json,status,requested_at) VALUES(?,?,?,?,?)",
                        ("spend", f"Spend approval: {body.label} ${body.amount_cents/100:.2f}", json.dumps({"label": body.label, "amount_cents": body.amount_cents}), "pending", db.now()))
            return JSONResponse({"status": "approval_required", "approval_id": aid,
                                 "note": "Spending limit is $0. This expense needs human approval first."}, status_code=202)
    eid = write("INSERT INTO expenses(label,amount_cents,category,is_test,created_at) VALUES(?,?,?,?,?)",
                (body.label, body.amount_cents, body.category, body.is_test, db.now()))
    return one("SELECT * FROM expenses WHERE id=?", (eid,))

@app.get("/api/approvals")
def approvals():
    return rows("SELECT * FROM approvals ORDER BY id DESC LIMIT 50")

@app.post("/api/approvals/{aid}/decide")
def decide(aid: int, body: dict, auth=Depends(require_auth)):
    ap = one("SELECT * FROM approvals WHERE id=?", (aid,))
    if not ap: raise HTTPException(404, "not found")
    if body.get("decision") not in ("approved", "rejected"): raise HTTPException(400, "decision must be approved or rejected")
    write("UPDATE approvals SET status=?, decided_at=?, decided_by='admin' WHERE id=?", (body["decision"], db.now(), aid))
    if body["decision"] == "approved" and ap["kind"] == "publish":
        slug = json.loads(ap["payload_json"])["slug"]
        write("UPDATE products SET status='listed', updated_at=? WHERE slug=?", (db.now(), slug))
    db.log_activity("admin", f"approval {aid} {body['decision']}", ap["summary"])
    return one("SELECT * FROM approvals WHERE id=?", (aid,))

@app.post("/api/approvals/request")
def request_approval(body: dict, auth=Depends(require_auth)):
    kind = body.get("kind", "general")
    if kind not in ("spend", "publish", "refund", "account_change", "strategy"):
        raise HTTPException(400, "unknown approval kind")
    aid = write("INSERT INTO approvals(kind,summary,payload_json,status,requested_at) VALUES(?,?,?,?,?)",
                (kind, body.get("summary", kind), json.dumps(body.get("payload", {})), "pending", db.now()))
    return one("SELECT * FROM approvals WHERE id=?", (aid,))

@app.get("/api/schedules")
def schedules():
    return load_config()

@app.post("/api/jobs/{job_id}/run")
def run_job_api(job_id: str, auth=Depends(require_auth)):
    return run_job(job_id)

@app.get("/api/activity")
def activity():
    return {"activity": rows("SELECT * FROM activity_log ORDER BY id DESC LIMIT 30"),
            "errors": rows("SELECT * FROM error_log ORDER BY id DESC LIMIT 30"),
            "decisions": rows("SELECT * FROM decision_log ORDER BY id DESC LIMIT 20"),
            "runs": rows("SELECT * FROM agent_runs ORDER BY id DESC LIMIT 30")}

@app.get("/api/settings")
def settings():
    # NEVER return secret values; only whether each is configured.
    return {"llm_daily_cap": db.get_setting("llm_daily_cap", "50"),
            "spending_limit_cents": db.get_setting("spending_limit_cents", "0"),
            "approval_required_publish": db.get_setting("approval_required_publish", "1"),
            "secrets": {"GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
                        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
                        "GUMROAD_ACCESS_TOKEN": bool(os.environ.get("GUMROAD_ACCESS_TOKEN")),
                        "ADMIN_PASSWORD": bool(os.environ.get("ADMIN_PASSWORD"))},
            "llm": llm.provider_status()}

@app.post("/api/settings")
def update_settings(body: dict, auth=Depends(require_auth)):
    for k in ("llm_daily_cap", "spending_limit_cents", "approval_required_publish"):
        if k in body: db.set_setting(k, str(body[k]))
    return {"ok": True}

class LoginIn(BaseModel):
    password: str

@app.post("/api/login")
def login(body: LoginIn):
    pw = os.environ.get("ADMIN_PASSWORD", "")
    if not pw: raise HTTPException(400, "No admin password is set on the server (ADMIN_PASSWORD env).")
    if not hmac.compare_digest(body.password, pw): raise HTTPException(401, "wrong password")
    tok = secrets.token_hex(16); TOKENS.add(tok)
    return {"token": tok}

@app.get("/api/research")
def research():
    return rows("SELECT * FROM research ORDER BY score DESC")

app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
