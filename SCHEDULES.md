# Schedules (`config/schedules.json`, mirrored into the `schedules` table)

| Job | When | Agents / work |
|---|---|---|
| monday_research | Mon 08:00 | Research opportunities, generate product ideas, executive performance review |
| tuesday_build | Tue 08:00 | Build approved products, run QC |
| wednesday_marketing | Wed 08:00 | Generate marketing content, prepare publishing materials |
| thursday_acquisition | Thu 08:00 | Analyze acquisition opportunities, improve listings (optimization + marketing) |
| friday_finance | Fri 08:00 | Financial report, evaluate experiments, recommend next week's priorities |
| weekend_maintenance | Sat 09:00 | Low-resource maintenance, error review, prepare next cycle |

Configurable: edit `config/schedules.json` (and the `schedules` table `enabled` flag).
Dedupe: a job that already succeeded today is skipped (`skipped_duplicate`).
Retry: up to 3 attempts with exponential backoff per agent; failures are logged to `error_log` and the cycle continues.
Run manually: `python -m app.scheduler --run <job_id>` or the dashboard (Agents tab → Run now).
Note: this project ships no cron/host scheduler — on Railway use its cron, or run jobs manually from the phone dashboard (the intended 15–30 min/week supervision).
