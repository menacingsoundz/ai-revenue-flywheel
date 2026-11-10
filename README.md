# AI Revenue Flywheel

A phone-controlled, autonomous AI business that creates and sells practical digital tools
to independent home-service operators (cleaners, landscapers, mobile detailers, pressure
washers, contractors). **$0 software/infrastructure budget. No revenue is guaranteed.
No fake orders, sales, customers, reviews or market statistics anywhere in the system.**

## What it is

- **Stack:** Python FastAPI + SQLite (file DB, survives restart) + static mobile-first dashboard served by the same app. Deps: fastapi, uvicorn, openpyxl, pytest, httpx.
- **9 agents** in `app/agents/agents.py` (executive, research, product creation, quality control, marketing, distribution, sales, financial, optimization) with a common interface.
- **8 real products** generated as `.xlsx` (live formulas) and `.txt` files in `data/products/`, all QC-passed. 4 bundle definitions. Nothing is listed for sale until QC passes **and** a human approves it.
- **AI:** Gemini (Google AI Studio free tier) and OpenAI are both **optional**. With no key the system runs in deterministic template mode and says so on the dashboard. Daily LLM cap default 50, quota-monitored, cached by dedupe, falls back to template mode on any failure. No paid API is ever called.
- **Money:** spending limit defaults to **$0**. Any spend, refund, transfer, account change, publish or strategy change needs a human approval in the Approvals tab. The system never spends or moves money automatically.

## Run it locally

```bash
cd ~/workspace/ai-revenue-flywheel
./run.sh            # seeds the DB, serves on http://localhost:8000
# or: .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 on your phone's browser (same Wi-Fi) or on this machine.

## Run a scheduled job manually

```bash
.venv/bin/python -m app.scheduler --run monday_research
.venv/bin/python -m app.scheduler --run tuesday_build
.venv/bin/python -m app.scheduler --run wednesday_marketing
.venv/bin/python -m app.scheduler --run thursday_acquisition
.venv/bin/python -m app.scheduler --run friday_finance
.venv/bin/python -m app.scheduler --run weekend_maintenance
.venv/bin/python -m app.scheduler --list   # show the schedule
```

## Optional keys (server env vars only — never in chat, the dashboard, or the repo)

```bash
export GEMINI_API_KEY="..."        # Google AI Studio free tier (optional)
export OPENAI_API_KEY="..."        # optional alternative
export GUMROAD_ACCESS_TOKEN="..."  # enables Gumroad sales sync (see STOREFRONT-GUMROAD.md)
export ADMIN_PASSWORD="..."        # enables token login for mutating endpoints
```

See `.env.example`. Keys are read from the environment at runtime; the API never returns them.

## Deploy free (needs your authorization — not done for you)

- **Railway (recommended, free tier):** create a project from this folder, set the start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, add the env vars above (only the ones you want).
  SQLite lives on the container disk — add a Railway volume for `data/` so the DB survives restarts.
- **Cloudflare Pages:** serves the static dashboard only; the API needs a separate host (Railway), so Railway alone is simpler.

## Current honest status

- Revenue: **$0**, orders: **0**, products: 12 (all QC-passed, 0 listed — listing needs your approval).
- Gumroad: **NOT CONNECTED**. LLM: **template mode** (no key provided).
- Nothing has been published, listed, or sold. Nothing is auto-published ever.

## Docs

- `ARCHITECTURE.md`, `DATABASE.md`, `AGENTS.md`, `SCHEDULES.md`, `STOREFRONT-GUMROAD.md`, `SECURITY.md`, `TEST_RESULTS.md`
