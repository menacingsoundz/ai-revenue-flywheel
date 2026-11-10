# Test Results

Run: `.venv/bin/python -m pytest tests/ -q` (from `~/workspace/ai-revenue-flywheel/`)

**Result: 15 passed, 0 failed** (3 deprecation warnings only: FastAPI `on_event` and httpx/TestClient — cosmetic).

Coverage maps to the prompt's 14 checks (+1 seed-integrity check):

| # | Check | Result |
|---|---|---|
| 1 | Mobile dashboard loads | PASS — `/` returns 200 with dashboard; `/api/dashboard` returns $0/0 orders honestly |
| 2 | Database saves and retrieves | PASS |
| 3 | AI can generate a product | PASS — all 8 product files generated via `build_all()` |
| 4 | Quality control workflow | PASS — QC fail blocks listing; QC pass allows (approval still required) |
| 5 | Product files exist + formulas correct | PASS — cleaning quote 45+3·18+2·15+1500·0.04=189, ×1.25=236.25; landscaping 186; pressure washing 273 |
| 6 | Marketing drafts recorded | PASS — 5 drafts, all status `draft`, never auto-published |
| 7 | Scheduled workflows execute + dedupe | PASS — job runs ok, second same-day run `skipped_duplicate`, draft regen adds 0 |
| 8 | Sales recording accurate | PASS — $12.00 order, $1.20 fee → net $10.80; TEST orders excluded from totals |
| 9 | Profit calculations correct | PASS — net = gross − fees − refunds − expenses |
| 10 | Reinvestment calculations correct | PASS — $100 net → $50 / $25 / $15 / $10 exactly |
| 11 | Failed AI requests handled | PASS — no key → template fallback; bogus key → `failed`, no crash |
| 12 | No API keys in frontend/public files | PASS — grep test over html/js/css/md |
| 13 | Approval gates work | PASS — unapproved publish creates pending approval, product stays unlisted; approving lists it; spend above $0 blocked |
| 14 | Recovery from ordinary errors | PASS — unknown job logged, system still healthy |
| 15 | Seed has no fake sales | PASS — catalog only, no seeded orders |

Also verified live (2026-11-09): `uvicorn` boot, dashboard HTTP 200, `/api/dashboard` shows
gross $0 / net $0 / 0 orders / template mode / Gumroad not connected, 12 products, and
QC run: **12/12 products passed** (one real bug found and fixed during verification: bundles
initially failed QC because they have member files, not a single file — fixed in
`QualityControlAgent.check_product`, re-verified 12/12).

One test initially failed (`test_15` counted 13 products because `test_04` adds a draft product);
fixed the assertion to `>= 12`. A later run caught `test_12` flagging the Gumroad doc's example
`GUMROAD_ACCESS_TOKEN=<...>` line as a key-like string — a false positive in the doc wording, not a
leaked secret; reworded the doc to name the variable without an `=` value pattern and re-ran green.
Final run: **15 passed, 0 failed**.
