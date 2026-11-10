# Architecture

```
Phone browser ──► FastAPI (app/main.py) ──► SQLite (data/flywheel.db)
                     │  serves static/ dashboard + JSON API
                     ├─► app/agents/agents.py   (9 agents, common interface)
                     ├─► app/products.py        (openpyxl file generation)
                     ├─► app/llm.py             (Gemini/OpenAI optional, template fallback)
                     ├─► app/finance.py         (profit + 50/25/15/10 allocation)
                     ├─► app/scheduler.py       (Mon–Fri + weekend jobs, dedupe, retry)
                     └─► app/db.py              (schema, settings, activity/error logs)
```

- **Decisions:** FastAPI + SQLite chosen as the simplest working stack with zero cost and no
  external services required. No paid deps. Static HTML/CSS/JS dashboard, no build step.
- **Reduced-capacity mode:** when no LLM key is set or the daily cap (default 50) is hit, all
  agents run on deterministic templates and the dashboard says so.
- **Dedupe:** products by slug, marketing drafts by slug, publishing queue by draft, scheduler
  jobs by job+day, CSV orders by external_id.
- **Retry/recovery:** scheduler retries a failed agent up to 3 times with exponential backoff,
  then logs the error and continues the cycle. A failed LLM call never crashes a job.
- **Approval gates:** publish, spend, refund, transfer, account change, strategy change all
  require a row in `approvals` with status `approved`. Listing additionally requires QC pass.
