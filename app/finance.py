"""Financial math. All figures from ACTUAL recorded orders/expenses only.
Allocation of distributable (net) profit: 50% retained / 25% infra+AI / 15% expansion / 10% reserve.
Never spends or moves money; allocation is a recommendation only."""
from . import db

ALLOCATION = {"retained_profit": 0.50, "infrastructure_ai": 0.25, "expansion": 0.15, "reserve": 0.10}

def cents(dollars): return int(round(dollars * 100))

def summary():
    c = db.connect()
    o = c.execute("SELECT COALESCE(SUM(amount_cents),0) g, COALESCE(SUM(fee_cents),0) f,"
                  " COALESCE(SUM(refund_cents),0) r, COUNT(*) n FROM orders WHERE is_test=0").fetchone()
    e = c.execute("SELECT COALESCE(SUM(amount_cents),0) x FROM expenses WHERE is_test=0").fetchone()
    c.close()
    gross, fees, refunds, n = int(o["g"]), int(o["f"]), int(o["r"]), int(o["n"])
    expenses = int(e["x"])
    net = gross - fees - refunds - expenses
    distributable = max(net, 0)
    alloc = {k: int(round(distributable * v)) for k, v in ALLOCATION.items()}
    # fix rounding drift so parts sum exactly to distributable
    drift = distributable - sum(alloc.values())
    if drift:
        alloc["retained_profit"] += drift
    return {"gross_cents": gross, "fees_cents": fees, "refunds_cents": refunds,
            "expenses_cents": expenses, "net_cents": net, "orders": n,
            "distributable_cents": distributable, "allocation_cents": alloc,
            "allocation_pct": {k: int(v * 100) for k, v in ALLOCATION.items()},
            "reinvestment_balance_cents": alloc["infrastructure_ai"] + alloc["expansion"],
            "note": "Real orders only. Test orders excluded. Allocation is a recommendation; no money moves automatically."}

def allocate(net_cents):
    """Pure function used by tests: $100 net -> 50/25/15/10 dollars."""
    net = max(int(net_cents), 0)
    alloc = {k: int(round(net * v)) for k, v in ALLOCATION.items()}
    drift = net - sum(alloc.values())
    if drift:
        alloc["retained_profit"] += drift
    return alloc
