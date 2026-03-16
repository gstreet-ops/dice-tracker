# dice-tracker

Global price tracker for premium 50mm gold dice.
Scrapes eBay, Google Shopping, AliExpress, and Chessex on a cron schedule.
Stores results in Supabase. Sends Gmail alerts on matches. Dashboard on GitHub Pages.

## Project Info
- **Repo:** https://github.com/gstreet-ops/dice-tracker
- **Local:** C:\Users\brian\projects\dice-tracker
- **Dashboard:** https://gstreet-ops.github.io/dice-tracker
- **Supabase:** Account 4 — brian+tracker@globestreet.com
- **Supabase URL:** https://zziindzdwzlmnkccenfx.supabase.co
- **Supabase Project ID:** zziindzdwzlmnkccenfx

## Stack
- Python 3.11 — scraper + alert logic
- Supabase (Postgres) — products + price_history tables
- GitHub Actions — cron scheduler (every 6 hours)
- GitHub Pages — static HTML dashboard (regenerated each run)
- Gmail SMTP — email alerts on price match or drop

## Local Setup
```bash
cd C:\Users\brian\projects\dice-tracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env.local
# Fill in .env.local with real credentials
python scrapers/run.py
```

## Environment Variables
See `.env.example` for all required variables.
Locally: `.env.local` (never committed)
Production: GitHub Actions secrets

## GitHub Actions Secrets Required
| Secret | Description |
|--------|-------------|
| SUPABASE_URL | https://zziindzdwzlmnkccenfx.supabase.co |
| SUPABASE_ANON_KEY | From Project Settings → API |
| SUPABASE_SERVICE_KEY | From Project Settings → API (secret key) |
| GMAIL_ADDRESS | Gmail account used to SEND alerts (needs App Password) |
| GMAIL_APP_PASSWORD | 16-char app password from Google Account → Security |
| ALERT_TO_EMAIL | Email address to RECEIVE alerts (any email) |

## Project Structure
```
dice-tracker/
├── .github/workflows/
│   ├── scrape.yml        # Main cron scraper (every 6h)
│   └── keepalive.yml     # Supabase ping (every 3 days)
├── scrapers/
│   ├── run.py            # Entry point — runs all scrapers
│   ├── base.py           # Base scraper class
│   ├── chessex.py        # Chessex direct scraper
│   ├── ebay.py           # eBay worldwide scraper
│   ├── google_shopping.py # Google Shopping via SerpAPI
│   └── aliexpress.py     # AliExpress scraper
├── dashboard/
│   └── generate.py       # Generates index.html for GitHub Pages
├── supabase/
│   └── schema.sql        # DB migration — run once to set up tables
├── alerts/
│   └── email.py          # Gmail SMTP alert sender
├── filters.py            # Product filter/scoring logic
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

## Search Criteria (Dice Spec)
- Size: ≥ 50mm (2 inches)
- Finish: Gold body (metallic, solid, polished) — NOT gold pips on dark body
- Pips: Engraved/etched — NOT printed or sticker
- Material: Solid metal, heavy resin, or weighted — NOT hollow plastic, foam, acrylic
- Set: Matching set of 2 or 3
- Exclude: glitter, translucent, cheap acrylic, foam
- Price: Best value — no hard cap
- Sources: eBay worldwide, Google Shopping, AliExpress, Chessex, Etsy

## Pending: eBay Official API Integration
- eBay developer account created: username `gstreetops` at developer.ebay.com
- **Account pending approval — expect email within 1 business day**
- Once approved: log in → My Account → Application Access Keys → Create app → get Client ID + Client Secret
- Add as GitHub secrets: `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`
- Then ask Claude Code to: replace scrapers/ebay.py with eBay Browse API (endpoint: https://api.ebay.com/buy/browse/v1/item_summary/search)
- Current ebay.py scraper gets blocked by anti-bot in GitHub Actions → returns 0 results
- Watchlist items also get 0 results for the same reason — API fix resolves both

## Supabase Keep-Alive
The scraper runs every 6h and writes to Supabase — this prevents the free tier pause.
A separate keepalive.yml workflow also pings every 3 days as a safety net.
