"""Product creation: generates REAL downloadable files with verified formulas.
openpyxl workbooks use live Excel formulas (totals compute in Excel/Sheets).
Every product ships with instructions + worked examples inside the file."""
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

BASE = os.path.join(os.path.dirname(__file__), "..", "data", "products")
TITLE_FILL = PatternFill("solid", fgColor="1F4E79")
TITLE_FONT = Font(bold=True, color="FFFFFF", size=13)
H_FONT = Font(bold=True, color="FFFFFF")
H_FILL = PatternFill("solid", fgColor="2E75B6")

def _wb(title, instructions, examples):
    wb = Workbook()
    ws = wb.active; ws.title = "Calculator"
    ws["A1"] = title; ws["A1"].font = TITLE_FONT; ws["A1"].fill = TITLE_FILL
    ws.merge_cells("A1:D1")
    ws["A2"] = "INSTRUCTIONS"; ws["A2"].font = Font(bold=True)
    ws["A3"] = instructions; ws["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A3:D3"); ws.row_dimensions[3].height = 60
    ws["A4"] = "WORKED EXAMPLE"; ws["A4"].font = Font(bold=True)
    ws["A5"] = examples; ws["A5"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A5:D5"); ws.row_dimensions[5].height = 45
    ws.column_dimensions["A"].width = 34; ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18; ws.column_dimensions["D"].width = 30
    return wb, ws

def _headers(ws, row, cols):
    for i, h in enumerate(cols, start=1):
        c = ws.cell(row=row, column=i, value=h); c.font = H_FONT; c.fill = H_FILL

def cleaning_calculator(path):
    wb, ws = _wb("Residential Cleaning Quote Calculator",
        "Enter the yellow cells. The quote updates automatically. Base visit fee covers travel + setup; "
        "add per-bedroom, per-bathroom and per-sq-ft charges. Discounts apply only after the subtotal. "
        "Never quote below your minimum — the sheet flags quotes under the minimum fee.",
        "Example: 3 bed, 2 bath, 1,500 sq ft, deep clean. Base $45 + 3x$18 + 2x$15 + 1500x$0.04 = $189. "
        "Deep-clean multiplier 1.25 -> $236.25. Change any yellow cell and the total recalculates.")
    _headers(ws, 7, ["Item", "Value", "Unit / notes", ""])
    rows = [("Base visit fee ($)", 45), ("Bedrooms (count)", 3), ("Per bedroom ($)", 18),
            ("Bathrooms (count)", 2), ("Per bathroom ($)", 15),
            ("Living area (sq ft)", 1500), ("Per sq ft ($)", 0.04),
            ("Deep clean? (1=yes, 0=no)", 1), ("Deep-clean multiplier", 1.25),
            ("Discount ($, 0 if none)", 0), ("Minimum fee ($)", 75)]
    r = 8
    for label, val in rows:
        ws.cell(row=r, column=1, value=label); ws.cell(row=r, column=2, value=val); r += 1
    # B8 base, B9 beds, B10 per-bed, B11 baths, B12 per-bath, B13 sqft, B14 per-sqft,
    # B15 deep?, B16 mult, B17 discount, B18 min
    ws["A20"] = "SUBTOTAL (before multiplier)"; ws["B20"] = "=B8+B9*B10+B11*B12+B13*B14"
    ws["A21"] = "TOTAL QUOTE"; ws["B21"] = "=MAX(B18,(B20*IF(B15=1,B16,1))-B17)"
    for rr in (20, 21):
        ws.cell(row=rr, column=1).font = Font(bold=True); ws.cell(row=rr, column=2).font = Font(bold=True)
    ws["A22"] = "Check: total must be >= minimum fee"; ws["B22"] = '=IF(B21>=B18,"OK","BELOW MINIMUM")'
    wb.save(path); return path

def _simple_quote(path, title, instructions, examples, lines, total_formula, check=None):
    wb, ws = _wb(title, instructions, examples)
    _headers(ws, 7, ["Item", "Value", "Unit / notes", ""])
    r = 8
    for label, val in lines:
        ws.cell(row=r, column=1, value=label); ws.cell(row=r, column=2, value=val); r += 1
    ws[f"A{r+1}"] = "TOTAL QUOTE"; ws.cell(row=r+1, column=1).font = Font(bold=True)
    ws.cell(row=r+1, column=2, value=total_formula).font = Font(bold=True)
    if check:
        ws[f"A{r+2}"] = check[0]; ws.cell(row=r+2, column=2, value=check[1])
    wb.save(path); return path

def landscaping_calculator(path):
    return _simple_quote(path, "Landscaping Pricing Calculator",
        "Enter yellow cells. Mowing is priced per visit from lawn size; beds, hedges and cleanup are add-ons. "
        "The monthly estimate assumes 4 visits. Adjust rates to your local market — these are starting rates, not market data.",
        "Example: 8,000 sq ft lawn at $0.012/sq ft = $96/visit; + 2 beds x $25 + hedge trim $40 = $186/visit; monthly (4 visits) = $744.",
        [("Lawn size (sq ft)", 8000), ("Mowing rate per sq ft ($)", 0.012),
         ("Garden beds (count)", 2), ("Per bed ($)", 25), ("Hedge trimming ($)", 40),
         ("Seasonal cleanup ($)", 0), ("Visits per month", 4)],
        "=B8*B9+B10*B11+B12+B13",
        ("MONTHLY ESTIMATE (4 visits)", "=B16*B14"))

def detailing_calculator(path):
    return _simple_quote(path, "Mobile Detailing Pricing Calculator",
        "Pick a package base price, then add services. Interior + exterior packages already include the wash — "
        "do not double-count. Add travel only for jobs beyond your free radius.",
        "Example: Full detail base $149 + pet hair $25 + engine bay $30 = $204. Travel $0 within 15 miles.",
        [("Package base price ($)", 149), ("Pet hair removal ($)", 25), ("Engine bay ($)", 30),
         ("Headlight restoration ($)", 0), ("Odor treatment ($)", 0), ("Travel fee ($)", 0)],
        "=SUM(B8:B13)")

def pressure_washing_calculator(path):
    return _simple_quote(path, "Pressure Washing Quote Calculator",
        "Price by area: driveway, patio, siding and deck each have a per-sq-ft rate. Minimum job fee applies. "
        "Measure or estimate each area honestly; under-measuring is the most common quoting mistake.",
        "Example: driveway 600 sq ft x $0.18 = $108; patio 300 x $0.15 = $45; siding 1,200 x $0.10 = $120; total $273 (above $150 minimum).",
        [("Driveway (sq ft)", 600), ("Driveway rate ($/sq ft)", 0.18),
         ("Patio (sq ft)", 300), ("Patio rate ($/sq ft)", 0.15),
         ("Siding (sq ft)", 1200), ("Siding rate ($/sq ft)", 0.10),
         ("Deck (sq ft)", 0), ("Deck rate ($/sq ft)", 0.20), ("Minimum job fee ($)", 150)],
        "=MAX(B16,B8*B9+B10*B11+B12*B13+B14*B15)",
        ("Check: total >= minimum?", '=IF(B18>=B16,"OK","CHECK")'))

def customer_spreadsheet(path):
    wb = Workbook(); ws = wb.active; ws.title = "Customers"
    ws["A1"] = "Customer Management — fill one row per customer. Status: Lead / Active / Past / Lost."
    ws["A1"].font = Font(bold=True)
    _headers(ws, 3, ["Name", "Phone", "Email", "Address", "Service", "Last service date",
                      "Price ($)", "Status", "Notes"])
    for row in [("Example Customer", "555-0100", "example@example.com", "12 Main St",
                 "House cleaning", "2026-11-01", 120, "Active", "Prefers Fridays"),
                ("", "", "", "", "", "", "", "", "")]:
        ws.append(list(row)) if False else None
    ws.append(["Example Customer", "555-0100", "example@example.com", "12 Main St",
               "House cleaning", "2026-11-01", 120, "Active", "Prefers Fridays — EXAMPLE ROW, delete it"])
    ws["A6"] = "TOTALS (active customers only)"; ws["A6"].font = Font(bold=True)
    ws["G6"] = '=SUMIF(H4:H100,"Active",G4:G100)'; ws["G6"].font = Font(bold=True)
    ws["A7"] = "Active customer count"; ws["G7"] = '=COUNTIF(H4:H100,"Active")'
    for col, w in zip("ABCDEFGHI", [22, 14, 26, 26, 18, 16, 10, 10, 30]):
        ws.column_dimensions[col].width = w
    ws2 = wb.create_sheet("Monthly revenue")
    ws2["A1"] = "Enter each completed job: date, customer, amount. Total sums automatically."
    _headers(ws2, 3, ["Date", "Customer", "Service", "Amount ($)"])
    ws2["A8"] = "TOTAL"; ws2["D8"] = "=SUM(D4:D100)"; ws2["D8"].font = Font(bold=True)
    wb.save(path); return path

def appointment_tracker(path):
    wb = Workbook(); ws = wb.active; ws.title = "Appointments"
    ws["A1"] = "Appointment Tracker — one row per job. Status: Booked / Done / Cancelled / No-show."
    ws["A1"].font = Font(bold=True)
    _headers(ws, 3, ["Date", "Time", "Customer", "Service", "Address", "Price ($)", "Paid?", "Status"])
    ws.append(["2026-11-10", "09:00", "Example Customer", "House cleaning", "12 Main St", 120, "No", "Booked"])
    ws["A7"] = "Jobs this week"; ws["G7"] = '=COUNTA(C4:C100)'
    ws["A8"] = "Booked value ($)"; ws["F8"] = "=SUM(F4:F100)"; ws["F8"].font = Font(bold=True)
    ws["A9"] = "Collected ($)"; ws["F9"] = '=SUMIF(G4:G100,"Yes",F4:F100)'
    ws["A10"] = "Outstanding ($)"; ws["F10"] = "=F8-F9"
    for col, w in zip("ABCDEFGH", [12, 8, 20, 18, 24, 11, 8, 12]):
        ws.column_dimensions[col].width = w
    wb.save(path); return path

def communication_templates(path):
    text = """CUSTOMER COMMUNICATION TEMPLATES — for home-service operators
Use these as starting points. Replace [brackets] with your details. Keep messages short and specific.

1. QUOTE FOLLOW-UP (text/email, send 24h after a quote)
Hi [Name], this is [Your Name] from [Business]. Your quote for [service] is $[amount], valid until [date].
Happy to answer any questions or lock in a date — just reply here.

2. BOOKING CONFIRMATION
Hi [Name], you're booked for [service] on [date] at [time] at [address]. Total: $[amount].
Please make sure [access note, e.g. gate code / pets secured]. Reply YES to confirm.

3. DAY-BEFORE REMINDER
Reminder: we're coming tomorrow, [date] at [time], for [service]. Total due: $[amount].
If anything changed, reply here and we'll adjust.

4. AFTER THE JOB — THANK YOU + REVIEW ASK
Thanks, [Name]! Your [service] is done. If you're happy with the work, a short review here helps a lot: [review link].
Anything not right? Reply and we'll make it right.

5. LATE / RESCHEDULE
Hi [Name], running about [X] minutes late today — sorry about that. New arrival: [time].
If that doesn't work, reply and we'll reschedule at no charge.

6. MISSED PAYMENT (polite)
Hi [Name], quick reminder — $[amount] for [service] on [date] is still open. You can pay here: [payment link].
Questions? Just reply. Thanks!

7. REBOOKING / SEASONAL
Hi [Name], it's been [X weeks] since your last [service]. Want us back on [suggested date]?
Reply YES and I'll hold that slot for you.

8. PRICE INCREASE NOTICE (send 30 days ahead)
Hi [Name], from [date] our [service] moves from $[old] to $[new] as costs have risen.
Your next booking before [date] stays at the old price. Thanks for sticking with us.

Rules: never promise a result you can't deliver; never copy another business's reviews;
keep every message truthful about price, timing and what's included.
"""
    with open(path, "w") as f: f.write(text)
    return path

def pricing_guide(path):
    text = """PRICING GUIDE FOR HOME-SERVICE OPERATORS
A practical starting guide — not market data. Test prices with real quotes and adjust.

1. KNOW YOUR FLOOR. Add up fuel, supplies, equipment wear, travel time, insurance and tax for one job.
   Your price must clear that floor or the job loses money. The calculators in this toolkit do that math.
2. PRICE THE JOB, NOT THE HOUR (mostly). Customers buy a clean house, a mowed lawn, a detailed car —
   quote the outcome. Track your effective hourly rate privately to check you're not undercharging.
3. THREE TIERS WORK. Basic / Standard / Premium lets customers choose up instead of haggling down.
4. MINIMUM FEES PROTECT YOU. A $75–$150 minimum stops tiny jobs eating your day in travel.
5. CHARGE FOR DISTANCE. Free radius (e.g. 15 miles), then a travel fee beyond it.
6. RAISE PRICES IN SMALL STEPS. 5–10% at a time, with 30 days' notice to regulars. Grandfather nobody forever.
7. DEPOSITS FOR BIG JOBS. 25–50% upfront on jobs over $300 protects against no-shows.
8. TRACK EVERY QUOTE. Won vs lost, and why. If you win 100% of quotes, you're too cheap. If you win under
   30%, check whether the quote, the follow-up, or the price is the problem — don't guess.
9. BUNDLES BEAT DISCOUNTS. A regular schedule (weekly/biweekly) at a fair price beats one-off discounts.
10. NEVER FAKE SOCIAL PROOF. No invented reviews, testimonials or customer counts. Real reviews only.

Worked example: a cleaner whose floor is $28/job (supplies $6, fuel $8, wear $4, tax/fees $10)
charging $45 makes $17 before their own time. At 2 hours on site that's $8.50/hour — too low.
At $95 for the same job, the margin is $67, or $33.50/hour. Use the quote calculators to run your own numbers.
"""
    with open(path, "w") as f: f.write(text)
    return path

BUILDERS = {
    "cleaning-quote-calculator": ("Residential Cleaning Quote Calculator", cleaning_calculator, "cleaning-quote-calculator.xlsx"),
    "landscaping-pricing-calculator": ("Landscaping Pricing Calculator", landscaping_calculator, "landscaping-pricing-calculator.xlsx"),
    "detailing-pricing-calculator": ("Mobile Detailing Pricing Calculator", detailing_calculator, "detailing-pricing-calculator.xlsx"),
    "pressure-washing-quote-calculator": ("Pressure Washing Quote Calculator", pressure_washing_calculator, "pressure-washing-quote-calculator.xlsx"),
    "customer-management-spreadsheet": ("Customer Management Spreadsheet", customer_spreadsheet, "customer-management-spreadsheet.xlsx"),
    "appointment-tracker": ("Appointment Tracker", appointment_tracker, "appointment-tracker.xlsx"),
    "customer-communication-templates": ("Customer Communication Templates", communication_templates, "customer-communication-templates.txt"),
    "pricing-guide-home-service": ("Pricing Guide for Home-Service Operators", pricing_guide, "pricing-guide-home-service.txt"),
}

def build_product(slug):
    os.makedirs(BASE, exist_ok=True)
    title, fn, fname = BUILDERS[slug]
    path = os.path.join(BASE, fname)
    fn(path)
    return path, os.path.getsize(path)

def build_all():
    out = {}
    for slug in BUILDERS:
        out[slug] = build_product(slug)
    return out
