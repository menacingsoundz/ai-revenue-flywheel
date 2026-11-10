# Gumroad Storefront Integration — NOT CONNECTED

Status: **NOT CONNECTED. No listings have been created. No sales exist.**

## What is built

- `SalesAgent` (`app/agents/agents.py`): reports `not_operational` until a key is set; never invents sales.
- Manual CSV import: `SalesAgent.import_csv_orders(rows)` — dedupes by `external_id`.
- Dashboard Finance tab + `POST /api/orders`: real orders require an `external_id` (e.g. Gumroad sale id); test orders use `is_test=1` and are excluded from totals.
- Product files in `data/products/` are ready to upload as Gumroad product files.

## Exact steps to connect (your action, needs your Gumroad account)

1. Log in to Gumroad → Settings → Advanced → **Generate an access token** (or create an application).
2. On the server (Railway dashboard → Variables, or your shell), set the
   `GUMROAD_ACCESS_TOKEN` environment variable to the token you generated.
   Never paste the token in chat, the dashboard, or the repo.
3. Restart the app. The dashboard will show "Gumroad: connected" and the Sales agent will leave `not_operational` status.
4. Create listings **manually in Gumroad** first (upload the files from `data/products/`, set the prices below). The app does not auto-create listings — that needs your approval per listing.
5. Sales sync: the API sync is a stub; until it is implemented, import sales via CSV (Gumroad → Sales → Export) through the Sales agent's CSV import. Each import dedupes by sale id.

## Prices (starting test prices, not validated market prices)

| Product | Price |
|---|---|
| Residential Cleaning Quote Calculator | $12.00 |
| Landscaping Pricing Calculator | $12.00 |
| Mobile Detailing Pricing Calculator | $15.00 |
| Pressure Washing Quote Calculator | $15.00 |
| Customer Management Spreadsheet | $9.00 |
| Appointment Tracker | $9.00 |
| Customer Communication Templates | $7.00 |
| Pricing Guide for Home-Service Operators | $9.00 |
| Cleaning / Landscaping / Detailing Bundle | $29.00 each |
| Premium Home-Service Toolkit (all 8) | $49.00 |

Gumroad takes a fee per sale (check Gumroad's current fee schedule before pricing final); the app records `fee_cents` per order so net profit is computed on actuals.
