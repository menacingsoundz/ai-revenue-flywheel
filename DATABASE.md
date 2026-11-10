# Database (SQLite, `data/flywheel.db`)

| Table | Purpose |
|---|---|
| products | Catalog: slug, title, category, description, price_cents, status (draft/listed/archived), qc_status, file_path |
| product_files | Files belonging to a product (bundles list member files) |
| qc_checks | Every QC run: passed flag + per-check JSON |
| marketing_drafts | Draft content (status `draft` until a human approves publishing) |
| publishing_queue | Copy-ready text + channel + link, status `queued` — manual publishing only |
| orders | Real orders only. Empty at seed. `is_test` orders are excluded from all totals |
| expenses | Real expenses; test expenses flagged `is_test` |
| financial_ledger | Reserved for ledger entries (currently informational) |
| agent_runs | Every agent run: agent, job, status, detail, timestamps |
| decision_log | Executive/optimization decisions with reasons |
| approvals | Human approval gate: kind (spend/publish/refund/account_change/strategy), summary, payload, status |
| schedules | Jobs from `config/schedules.json` (id, weekday, time, enabled) |
| settings | Key/value: `llm_daily_cap` (50), `spending_limit_cents` (0), `approval_required_publish` (1), per-agent enable flags |
| activity_log / error_log | Audit trail and error trail |
| research | Opportunities with score, evidence text, sources JSON — no invented statistics |
| llm_usage | Per-day LLM call counts for quota monitoring |

Seed (`app/seed.py`) inserts **only** the 12 product definitions and 6 schedules. Zero fake orders, sales, customers or revenue.
