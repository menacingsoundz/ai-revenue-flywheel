"""Seed ONLY catalog definitions + schedules. Zero fake orders/sales/customers."""
import json, os
from . import db
from .products import BUILDERS, build_product

CATALOG = [
    ("cleaning-quote-calculator", "Residential Cleaning Quote Calculator", "calculator",
     "Quote cleaning jobs by base fee + per-bedroom, per-bathroom and per-sq-ft rates, with a deep-clean multiplier and minimum fee. Includes instructions and a worked example.", 1200),
    ("landscaping-pricing-calculator", "Landscaping Pricing Calculator", "calculator",
     "Price mowing by lawn size plus beds, hedges and cleanup, with a monthly estimate. Includes instructions and a worked example.", 1200),
    ("detailing-pricing-calculator", "Mobile Detailing Pricing Calculator", "calculator",
     "Build a detailing quote from a package base price plus add-on services and travel. Includes instructions and a worked example.", 1500),
    ("pressure-washing-quote-calculator", "Pressure Washing Quote Calculator", "calculator",
     "Quote pressure washing by area — driveway, patio, siding, deck — with a minimum job fee. Includes instructions and a worked example.", 1500),
    ("customer-management-spreadsheet", "Customer Management Spreadsheet", "template",
     "Track customers, services, prices and status in one sheet, with automatic active-customer totals and a monthly revenue tab.", 900),
    ("appointment-tracker", "Appointment Tracker", "template",
     "Track every booking: date, customer, service, price, paid status, with booked value and outstanding totals computed automatically.", 900),
    ("customer-communication-templates", "Customer Communication Templates", "template",
     "Eight ready-to-use messages: quote follow-up, booking confirmation, reminders, thank-you/review ask, reschedule, payment reminder, rebooking and price notices.", 700),
    ("pricing-guide-home-service", "Pricing Guide for Home-Service Operators", "guide",
     "A practical pricing guide: cost floors, minimum fees, tiers, deposits and tracking won vs lost quotes. No invented market statistics.", 900),
    ("cleaning-bundle", "Cleaning Business Bundle", "bundle",
     "Cleaning Quote Calculator + Customer Management Spreadsheet + Appointment Tracker + Communication Templates.", 2900),
    ("landscaping-bundle", "Landscaping Business Bundle", "bundle",
     "Landscaping Pricing Calculator + Customer Management Spreadsheet + Appointment Tracker + Communication Templates.", 2900),
    ("detailing-bundle", "Detailing Business Bundle", "bundle",
     "Detailing Pricing Calculator + Customer Management Spreadsheet + Appointment Tracker + Communication Templates.", 2900),
    ("premium-home-service-toolkit", "Premium Home-Service Toolkit", "bundle",
     "All 8 products: all 4 calculators, customer spreadsheet, appointment tracker, communication templates and the pricing guide.", 4900),
]
BUNDLE_FILES = {"cleaning-bundle": ["cleaning-quote-calculator", "customer-management-spreadsheet", "appointment-tracker", "customer-communication-templates"],
                "landscaping-bundle": ["landscaping-pricing-calculator", "customer-management-spreadsheet", "appointment-tracker", "customer-communication-templates"],
                "detailing-bundle": ["detailing-pricing-calculator", "customer-management-spreadsheet", "appointment-tracker", "customer-communication-templates"],
                "premium-home-service-toolkit": list(BUILDERS)}

def seed():
    db.init_db()
    c = db.connect()
    for slug, title, cat, desc, price in CATALOG:
        row = c.execute("SELECT id FROM products WHERE slug=?", (slug,)).fetchone()
        if row: continue
        if slug in BUILDERS:
            path, size = build_product(slug)
            c.execute("INSERT INTO products(slug,title,category,description,price_cents,status,qc_status,file_path,created_at,updated_at) VALUES(?,?,?,?,?,'draft','pending',?,?,?)",
                      (slug, title, cat, desc, price, path, db.now(), db.now()))
            pid = c.execute("SELECT id FROM products WHERE slug=?", (slug,)).fetchone()["id"]
            c.execute("INSERT INTO product_files(product_id,filename,path,file_type,size_bytes,created_at) VALUES(?,?,?,?,?,?)",
                      (pid, os.path.basename(path), path, "xlsx" if path.endswith(".xlsx") else "txt", size, db.now()))
        else:
            c.execute("INSERT INTO products(slug,title,category,description,price_cents,status,qc_status,created_at,updated_at) VALUES(?,?,?,?,?,'draft','pending',?,?)",
                      (slug, title, cat, desc, price, db.now(), db.now()))
            pid = c.execute("SELECT id FROM products WHERE slug=?", (slug,)).fetchone()["id"]
            for member in BUNDLE_FILES[slug]:
                m = c.execute("SELECT file_path FROM products WHERE slug=?", (member,)).fetchone()
                if m and m["file_path"]:
                    c.execute("INSERT INTO product_files(product_id,filename,path,file_type,size_bytes,created_at) VALUES(?,?,?,?,?,?)",
                              (pid, os.path.basename(m["file_path"]), m["file_path"], "xlsx" if m["file_path"].endswith(".xlsx") else "txt", os.path.getsize(m["file_path"]), db.now()))
    # schedules from config
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "schedules.json")
    with open(cfg_path) as f: cfg = json.load(f)
    for s in cfg["jobs"]:
        c.execute("INSERT OR IGNORE INTO schedules(job_id,name,weekday,time_local,enabled,config_json) VALUES(?,?,?,?,?,?)",
                  (s["id"], s["name"], s["weekday"], s["time_local"], 1 if s.get("enabled", True) else 0, json.dumps(s)))
    c.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES('spending_limit_cents','0',?)", (db.now(),))
    c.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES('llm_daily_cap','50',?)", (db.now(),))
    c.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES('approval_required_publish','1',?)", (db.now(),))
    c.commit(); c.close()
    return {"products": len(CATALOG), "note": "Seeded catalog + schedules only. No orders, no sales, no customers."}

if __name__ == "__main__":
    print(seed())
