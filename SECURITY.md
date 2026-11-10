# Security & Backups

- **Secrets:** only via server environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`,
  `GUMROAD_ACCESS_TOKEN`, `ADMIN_PASSWORD`). Never in frontend code, the repo, downloadable
  files, or chat. `GET /api/settings` returns only booleans (configured yes/no), never values.
  A grep test (`test_12`) checks frontend/public files for key-like strings.
- **Auth:** if `ADMIN_PASSWORD` is set, mutating endpoints (run agents, create/QC/list products,
  record orders/expenses, decide approvals, change settings, run jobs) require header
  `X-Admin-Token` from `POST /api/login`. If no password is set, the app assumes a trusted
  local network — set a password before exposing it publicly.
- **Spending:** limit defaults to $0 (`settings.spending_limit_cents`). Any expense above the
  limit creates a pending `spend` approval instead of recording. No money ever moves automatically.
- **Approval gates:** spend, publish, refund, transfer, account change, strategy change.
  Listing a product additionally requires a QC pass.
- **Data protection:** no customer data is collected yet. When Gumroad sales arrive, only order
  totals/product are stored — no card data ever touches this system.
- **Backups:** copy `data/flywheel.db` and `data/products/` regularly. The DB is a single SQLite
  file: `cp data/flywheel.db backups/flywheel-$(date +%F).db`. On Railway, attach a volume to
  `data/` so restarts don't wipe it.
- **Recovery:** every agent/scheduler failure is logged to `error_log` with the job continuing;
  the dashboard shows recent errors. Restarting the app re-seeds missing catalog/schedule rows
  (idempotent — never duplicates).
