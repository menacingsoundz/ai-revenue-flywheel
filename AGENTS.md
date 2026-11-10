# Agents (all in `app/agents/agents.py`, common interface: `name`, `description`, `status`, `run(job, payload)`, `last_run`, `errors`)

| Agent | Job |
|---|---|
| executive | Coordinates, keeps decision history, enforces quota / reduced-capacity mode, weekly priority review |
| research | Scores opportunities from evidence for home-service markets (cleaners, landscapers, detailers, pressure washers, contractors); stores sources; never invents statistics |
| product_creation | Generates the real `.xlsx`/`.txt` product files via `app/products.py` |
| quality_control | Gates publication: file exists + non-empty, description present, price in range, no fake testimonials. A product cannot be listed until QC passes |
| marketing | Generates SEO articles, social posts, emails, lead magnets as **drafts only** — never auto-publishes |
| distribution | Builds the publishing queue with copy-ready text + links for manual publishing |
| sales | Gumroad interface. **NOT OPERATIONAL** until `GUMROAD_ACCESS_TOKEN` is set. Manual CSV import with dedupe by external_id. Never invents sales |
| financial | Gross / fees / refunds / expenses / net from actuals only; allocation 50% retained / 25% infra+AI / 15% expansion / 10% reserve — recommendation only, no money moves |
| optimization | Analyzes actual order data only. With zero orders it says so and recommends getting first traffic/sale before changing anything |

Enable/disable per agent from the dashboard (Agents tab) or via `settings` key `agent:<name>:enabled`.
Run any agent manually from the dashboard or via the scheduler CLI.
