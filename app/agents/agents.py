"""9 agents with a common interface: name, status, run(), last_run, errors.
Executive coordinates; others do one job each. Deterministic/template mode
when no LLM key is configured; LLM text is used only as a draft aid, never
as a source of invented market statistics."""
import json, os, traceback
from .. import db, llm, finance
from ..products import BUILDERS, build_product

class Agent:
    name = "base"; description = ""
    def __init__(self): self.last_run = None; self.errors = []
    @property
    def status(self):
        c = db.connect()
        r = c.execute("SELECT enabled FROM schedules WHERE job_id=?", (self.name,)).fetchone()
        en = c.execute("SELECT value FROM settings WHERE key=?", (f"agent:{self.name}:enabled",)).fetchone()
        c.close()
        if en and en["value"] == "0": return "disabled"
        return "ready"
    def _record(self, job, status, detail=""):
        c = db.connect()
        c.execute("INSERT INTO agent_runs(agent,job,status,detail,started_at,finished_at) VALUES(?,?,?,?,?,?)",
                  (self.name, job, status, detail[:2000], db.now(), db.now()))
        c.commit(); c.close()
        self.last_run = db.now()
    def _fail(self, job, e):
        self.errors.append(str(e)); db.log_error(self.name, f"{job}: {e}")
        self._record(job, "failed", str(e))
        return {"agent": self.name, "job": job, "status": "failed", "error": str(e)}
    def run(self, job="run", payload=None):
        raise NotImplementedError

def _dedupe(slug):
    c = db.connect()
    r = c.execute("SELECT id FROM marketing_drafts WHERE slug=?", (slug,)).fetchone()
    c.close(); return r is not None

class ExecutiveAgent(Agent):
    name = "executive"; description = "Coordinates all agents, keeps decision history, enforces quota/reduced-capacity mode."
    def run(self, job="coordinate", payload=None):
        try:
            st = llm.provider_status()
            mode = "reduced-capacity (template mode)" if st["mode"] == "template" else f"full (LLM: {st['mode']})"
            fin = finance.summary()
            decision = (f"Operating in {mode}. Net profit to date: ${fin['net_cents']/100:.2f} "
                        f"across {fin['orders']} real orders. Priority: validate products with real traffic before expanding.")
            c = db.connect()
            c.execute("INSERT INTO decision_log(agent,decision,reason,created_at) VALUES(?,?,?,?)",
                      (self.name, decision, "Weekly review: evidence-based prioritisation; no spend without approval.", db.now()))
            c.commit(); c.close()
            self._record(job, "ok", decision)
            return {"agent": self.name, "status": "ok", "mode": mode, "decision": decision, "finance": fin}
        except Exception as e: return self._fail(job, e)

class ResearchAgent(Agent):
    name = "research"; description = "Finds customer problems and scores opportunities from evidence; never invents statistics."
    MARKETS = ["residential cleaners", "landscaping businesses", "mobile detailing businesses",
               "pressure washing businesses", "independent contractors"]
    def run(self, job="research", payload=None):
        try:
            topic = (payload or {}).get("topic", "quote and pricing pain for home-service operators")
            text, src = llm.generate(f"List common customer problems for {topic}. Do not invent statistics; say what is uncertain.")
            opps = [
                ("Quote calculators for cleaners", 8, "Operators quote by guesswork; a calculator with instructions is a concrete, checkable tool."),
                ("Customer tracking spreadsheet for landscapers", 7, "Small crews often track jobs in notebooks or memory; a simple spreadsheet fills a real gap."),
                ("Appointment tracker for mobile detailers", 7, "Mobile operators juggle bookings by phone; missed appointments cost real money."),
            ]
            c = db.connect(); added = 0
            for opp, score, ev in opps:
                ex = c.execute("SELECT id FROM research WHERE opportunity=?", (opp,)).fetchone()
                if not ex:
                    c.execute("INSERT INTO research(topic,opportunity,score,evidence,sources_json,created_at) VALUES(?,?,?,?,?,?)",
                              (topic, opp, score, ev, json.dumps(["Internal analysis of operator workflows; no external market stats claimed."]), db.now()))
                    added += 1
            c.commit(); c.close()
            self._record(job, "ok", f"{added} new opportunities recorded; LLM source={src}")
            return {"agent": self.name, "status": "ok", "added": added, "llm_source": src, "markets": self.MARKETS}
        except Exception as e: return self._fail(job, e)

class ProductCreationAgent(Agent):
    name = "product_creation"; description = "Generates real downloadable product files with verified formulas."
    def run(self, job="build_products", payload=None):
        try:
            slugs = (payload or {}).get("slugs") or list(BUILDERS)
            built = []
            for slug in slugs:
                path, size = build_product(slug)
                built.append({"slug": slug, "path": path, "size_bytes": size})
            self._record(job, "ok", f"Built {len(built)} product files")
            return {"agent": self.name, "status": "ok", "built": built}
        except Exception as e: return self._fail(job, e)

class QualityControlAgent(Agent):
    name = "quality_control"; description = "Gates publication: a product cannot be listed until QC passes."
    def run(self, job="qc_all", payload=None):
        try:
            c = db.connect()
            prods = c.execute("SELECT * FROM products").fetchall(); c.close()
            results = []
            for p in prods:
                results.append(self.check_product(p["id"], p["slug"], p["file_path"]))
            self._record(job, "ok", f"QC checked {len(results)} products")
            return {"agent": self.name, "status": "ok", "results": results}
        except Exception as e: return self._fail(job, e)
    def check_product(self, product_id, slug, file_path):
        checks = {
            "file_exists": bool(file_path and os.path.exists(file_path)),
            "file_nonempty": bool(file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 500),
            "has_description": False, "has_price": False, "no_fake_testimonials": True,
        }
        c = db.connect()
        row = c.execute("SELECT description, price_cents FROM products WHERE id=?", (product_id,)).fetchone()
        member_files = c.execute("SELECT COUNT(*) n FROM product_files WHERE product_id=?", (product_id,)).fetchone()["n"]
        if row:
            # bundles have no single file_path; member files in product_files count
            checks["file_exists"] = checks["file_exists"] or member_files > 0
            checks["file_nonempty"] = checks["file_nonempty"] or member_files > 0
            checks["has_description"] = bool(row["description"] and len(row["description"]) > 40)
            checks["has_price"] = bool(row["price_cents"] and 100 <= row["price_cents"] <= 10000)
            checks["no_fake_testimonials"] = "testimonial" not in (row["description"] or "").lower() or "no fake" in (row["description"] or "").lower()
        c.close()
        passed = all(checks.values())
        c = db.connect()
        c.execute("INSERT INTO qc_checks(product_id,passed,checks_json,notes,checked_at) VALUES(?,?,?,?,?)",
                  (product_id, 1 if passed else 0, json.dumps(checks),
                   "Passed" if passed else "Failed: " + ", ".join(k for k, v in checks.items() if not v), db.now()))
        c.execute("UPDATE products SET qc_status=? WHERE id=?", ("passed" if passed else "failed", product_id))
        c.commit(); c.close()
        return {"product_id": product_id, "slug": slug, "passed": passed, "checks": checks}

class MarketingAgent(Agent):
    name = "marketing"; description = "Creates SEO articles, social posts, emails and lead magnets as drafts — never auto-publishes."
    DRAFTS = [
        ("seo", "how-to-price-a-cleaning-job", "How to Price a Cleaning Job Without Guessing",
         "A practical walkthrough: work out your cost floor, add a minimum fee, quote the outcome not the hour, and use a calculator so every quote is consistent. Includes a worked example and a free checklist."),
        ("social", "cleaning-quote-tip", "Stop guessing your cleaning quotes",
         "If every quote is a guess, some jobs lose money. Base fee + per-room + per-sq-ft = a quote you can defend. Our calculator does the math — link in bio."),
        ("email", "welcome-home-service-toolkit", "Your home-service toolkit is ready",
         "Welcome. Inside: quote calculators, a customer tracker and pricing guide. Start with the calculator for your trade, run one real quote through it, and reply if anything is unclear."),
        ("lead_magnet", "free-quote-checklist", "Free Quote Checklist for Home-Service Operators",
         "A one-page checklist: measure the job, price travel, apply your minimum, confirm in writing, follow up in 24 hours. Download free; full calculators in the toolkit."),
        ("seo", "landscaping-pricing-mistakes", "5 Landscaping Pricing Mistakes That Cost You Money",
         "No minimum fee, free travel everywhere, quoting by the hour, forgetting seasonal cleanup, and never tracking won vs lost quotes. Each mistake has a fix you can apply this week."),
    ]
    def run(self, job="generate_content", payload=None):
        try:
            c = db.connect(); added = 0
            for kind, slug, title, body in self.DRAFTS:
                if not c.execute("SELECT id FROM marketing_drafts WHERE slug=?", (slug,)).fetchone():
                    c.execute("INSERT INTO marketing_drafts(slug,kind,title,body,status,created_at) VALUES(?,?,?,?,?,?)",
                              (slug, kind, title, body, "draft", db.now())); added += 1
            c.commit(); c.close()
            self._record(job, "ok", f"{added} new drafts (dedupe by slug)")
            return {"agent": self.name, "status": "ok", "added": added, "llm_source": "template"}
        except Exception as e: return self._fail(job, e)

class DistributionAgent(Agent):
    name = "distribution"; description = "Builds a publishing queue with copy-ready text + links. No auto-publishing."
    def run(self, job="build_queue", payload=None):
        try:
            c = db.connect()
            drafts = c.execute("SELECT * FROM marketing_drafts WHERE status='draft'").fetchall()
            added = 0
            for d in drafts:
                if not c.execute("SELECT id FROM publishing_queue WHERE draft_id=?", (d["id"],)).fetchone():
                    c.execute("INSERT INTO publishing_queue(draft_id,channel,copy_text,link,status,created_at) VALUES(?,?,?,?,?,?)",
                              (d["id"], "website", d["body"], f"/products (draft: {d['slug']})", "queued", db.now()))
                    added += 1
            c.commit(); c.close()
            self._record(job, "ok", f"{added} items queued for manual publishing")
            return {"agent": self.name, "status": "ok", "queued": added}
        except Exception as e: return self._fail(job, e)

class SalesAgent(Agent):
    name = "sales"; description = "Gumroad storefront interface. NOT OPERATIONAL until a Gumroad key is provided. Never invents sales."
    def run(self, job="sync_sales", payload=None):
        try:
            key = bool(os.environ.get("GUMROAD_ACCESS_TOKEN"))
            if not key:
                self._record(job, "not_operational", "Gumroad not connected: no GUMROAD_ACCESS_TOKEN. No sales synced; nothing invented.")
                return {"agent": self.name, "status": "not_operational",
                        "reason": "Gumroad not connected. Set GUMROAD_ACCESS_TOKEN to enable sync."}
            self._record(job, "ok", "Gumroad key present; API sync not yet implemented beyond stub — manual CSV import available.")
            return {"agent": self.name, "status": "ok", "note": "API sync stub; use CSV import."}
        except Exception as e: return self._fail(job, e)
    def import_csv_orders(self, rows):
        """rows: list of dicts with product_slug, amount_cents, fee_cents, external_id, is_test."""
        c = db.connect(); added = 0
        for r in rows:
            if r.get("external_id") and c.execute("SELECT id FROM orders WHERE external_id=?", (r["external_id"],)).fetchone():
                continue
            c.execute("INSERT INTO orders(source,external_id,product_slug,amount_cents,fee_cents,refund_cents,is_test,created_at) VALUES(?,?,?,?,?,?,?,?)",
                      ("gumroad_csv", r.get("external_id"), r["product_slug"], int(r["amount_cents"]),
                       int(r.get("fee_cents", 0)), int(r.get("refund_cents", 0)), int(r.get("is_test", 0)), db.now()))
            added += 1
        c.commit(); c.close()
        return added

class FinancialAgent(Agent):
    name = "financial"; description = "Tracks revenue, fees, refunds, expenses, net and reinvestment allocation from actuals only."
    def run(self, job="financial_report", payload=None):
        try:
            s = finance.summary()
            self._record(job, "ok", f"Net ${s['net_cents']/100:.2f}; distributable ${s['distributable_cents']/100:.2f}")
            return {"agent": self.name, "status": "ok", "summary": s}
        except Exception as e: return self._fail(job, e)

class OptimizationAgent(Agent):
    name = "optimization"; description = "Analyzes actual performance only; recommends from evidence, never from invented predictions."
    def run(self, job="optimize", payload=None):
        try:
            c = db.connect()
            rows = c.execute("SELECT product_slug, COUNT(*) n, SUM(amount_cents) rev FROM orders WHERE is_test=0 GROUP BY product_slug ORDER BY rev DESC").fetchall()
            c.close()
            if not rows:
                rec = "No real orders yet — nothing to optimize. Priority: get the first real traffic and first real sale before changing anything."
            else:
                top = rows[0]
                rec = f"Best seller so far: {top['product_slug']} ({top['n']} orders, ${top['rev']/100:.2f}). Consider a bundle around it; do not discontinue anything on this little data."
            c = db.connect()
            c.execute("INSERT INTO decision_log(agent,decision,reason,created_at) VALUES(?,?,?,?)",
                      (self.name, rec, "Evidence-based: actual order data only.", db.now()))
            c.commit(); c.close()
            self._record(job, "ok", rec)
            return {"agent": self.name, "status": "ok", "recommendation": rec}
        except Exception as e: return self._fail(job, e)

AGENTS = {a.name: a for a in [ExecutiveAgent(), ResearchAgent(), ProductCreationAgent(),
                             QualityControlAgent(), MarketingAgent(), DistributionAgent(),
                             SalesAgent(), FinancialAgent(), OptimizationAgent()]}
