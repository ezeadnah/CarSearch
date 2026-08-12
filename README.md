# CarHuntr

Aggregates car listings from eBay, Gumtree, AutoTrader, and Facebook Marketplace
into one filterable Android app.

## How it's split

- `backend/` - Python (FastAPI) service. Pulls listings from all four sources,
  normalizes them into one schema, dedupes cars posted on multiple sites, and
  serves them over a REST API with filter query params.
- `android/` - Kotlin + Jetpack Compose app. Talks to your backend, shows a
  scrollable feed with a filter sheet (make, price, year, mileage, fuel,
  transmission, source), taps through to the original listing.

## Honest state of each source

| Source | Method | Reliability |
|---|---|---|
| eBay | Official Browse API | Solid. Set up API keys and it just works. |
| Gumtree | HTML scraping | Works today, will break when they change their site. No API exists. |
| AutoTrader | Playwright + headless browser | Fights Cloudflare/bot detection. Expect intermittent blocks. |
| Facebook Marketplace | Playwright + logged-in session | Most fragile. No API, requires manual login, Meta actively detects and blocks this pattern. Poll infrequently. |

Scraping Gumtree, AutoTrader, and Facebook all violate those platforms' Terms
of Service. This is legally gray territory (mostly a civil ToS matter, not
criminal), but it's worth knowing going in — accounts/IPs can get blocked,
and a cease-and-desist isn't unheard of for aggregators that get popular.
If you want a version with zero legal risk, run backend with only the eBay
source enabled.

## Backend setup

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# edit .env and add your eBay API keys from https://developer.ebay.com/

# one-time: log into Facebook so the scraper has a session to reuse
python -m app.sources.facebook_login

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Trigger a manual refresh (instead of waiting for the 30-min schedule):
```bash
curl -X POST "http://localhost:8000/refresh?query=BMW"
```

Check it worked:
```bash
curl "http://localhost:8000/listings?make=BMW&max_price=15000"
```

## Android setup

1. Open `android/` in Android Studio (Koala or newer).
2. Let Gradle sync — it'll pull the dependencies.
3. If running on the emulator, `10.0.2.2:8000` (already set in `Api.kt`)
   reaches your machine's localhost automatically.
4. If running on a physical phone, change `BASE_URL` in
   `android/app/src/main/java/com/carhuntr/data/Api.kt` to your machine's
   LAN IP (e.g. `http://192.168.1.50:8000`), and make sure your phone and
   dev machine are on the same network.
5. Run the app.

## Sensible next steps once this is running

- Swap SQLite for Postgres if you deploy the backend somewhere persistent.
- Add push notifications for "saved search" alerts (new listing matches your filters).
- Add proper pagination/infinite scroll in the Android list.
- Consider a paid scraping proxy for AutoTrader/Facebook if you want fewer blocks —
  much more reliable than raw Playwright long-term.
- Add photos carousel + full listing detail screen instead of just linking out.
