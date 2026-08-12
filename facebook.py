"""
Facebook Marketplace: the hardest source by a wide margin.

Reality check before you build around this:
- No public API for Marketplace listings.
- Requires an authenticated session (you log in as yourself/a dedicated
  account) - there is no logged-out way to browse Marketplace search results.
- Meta's ToS explicitly bans automated data collection, and their bot
  detection is aggressive: expect checkpoints, temporary blocks, or the
  account getting flagged if you poll frequently.
- Because of the above, treat this module as "works today, may stop working
  tomorrow" rather than production infrastructure. Poll it rarely (e.g. once
  every few hours, not every few minutes).

Setup:
1. Run once interactively to log in and save a session:
     python -m app.sources.facebook_login
   This opens a real browser window - log in manually, solve any 2FA,
   then the session cookies get saved to fb_session.json.
2. fetch_listings() below reuses that saved session headlessly.
"""
import os
import json
from typing import List
from playwright.async_api import async_playwright
from ..models import Listing

SESSION_FILE = os.path.join(os.path.dirname(__file__), "fb_session.json")
MARKETPLACE_URL = "https://www.facebook.com/marketplace/category/vehicles"


async def fetch_listings(location: str = "london", limit: int = 30) -> List[Listing]:
    if not os.path.exists(SESSION_FILE):
        print("[facebook] no saved session - run facebook_login.py first")
        return []

    listings: List[Listing] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=SESSION_FILE)
        page = await context.new_page()
        try:
            await page.goto(MARKETPLACE_URL, timeout=25000)
            await page.wait_for_timeout(3000)  # let dynamic content settle
            await page.wait_for_selector("a[href*='/marketplace/item/']", timeout=15000)

            cards = await page.query_selector_all("a[href*='/marketplace/item/']")
            seen_ids = set()
            for card in cards[: limit * 2]:  # over-fetch, dedupe below
                try:
                    href = await card.get_attribute("href")
                    source_id = href.split("/marketplace/item/")[1].split("/")[0].split("?")[0]
                    if source_id in seen_ids:
                        continue
                    seen_ids.add(source_id)

                    text = await card.inner_text()
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    price = _parse_price(lines[0]) if lines else None
                    title = lines[1] if len(lines) > 1 else ""

                    img_el = await card.query_selector("img")
                    img = await img_el.get_attribute("src") if img_el else None

                    listings.append(
                        Listing(
                            source="facebook",
                            source_id=source_id,
                            url=f"https://www.facebook.com/marketplace/item/{source_id}",
                            title=title,
                            price=price,
                            image_url=img,
                            location=location,
                            seller_type="private",
                        )
                    )
                    if len(listings) >= limit:
                        break
                except Exception:
                    continue
        except Exception as e:
            print(f"[facebook] fetch failed or was blocked: {e}")
        finally:
            await browser.close()

    return listings


def _parse_price(text: str):
    digits = "".join(c for c in text if c.isdigit())
    return float(digits) if digits else None
