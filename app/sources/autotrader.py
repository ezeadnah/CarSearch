"""
AutoTrader UK has no public API and actively fingerprints/blocks scrapers
(Cloudflare + bot detection). A plain httpx GET like the Gumtree module will
likely get a 403 or a challenge page rather than real HTML.

Realistic options, in order of reliability:
1. Playwright with a real headless browser (slower, works more often)
2. A commercial scraping proxy service (Bright Data, ScraperAPI, etc.) that
   handles the anti-bot layer for you
3. Accept AutoTrader as the weakest link and show fewer results from it

This module uses Playwright so it at least has a fighting chance. Requires:
    playwright install chromium
"""
from typing import List
from playwright.async_api import async_playwright
from ..models import Listing

SEARCH_URL = "https://www.autotrader.co.uk/car-search"


async def fetch_listings(postcode: str = "SW1A1AA", limit: int = 30) -> List[Listing]:
    listings: List[Listing] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0 Safari/537.36"
        )
        try:
            await page.goto(f"{SEARCH_URL}?postcode={postcode}", timeout=20000)
            await page.wait_for_selector("[data-testid='search-result']", timeout=10000)

            cards = await page.query_selector_all("[data-testid='search-result']")
            for card in cards[:limit]:
                try:
                    title_el = await card.query_selector("h3")
                    price_el = await card.query_selector("[data-testid='search-result-price']")
                    link_el = await card.query_selector("a[href]")
                    img_el = await card.query_selector("img")

                    if not title_el or not link_el:
                        continue

                    href = await link_el.get_attribute("href")
                    title = await title_el.inner_text()
                    price_text = await price_el.inner_text() if price_el else None
                    img = await img_el.get_attribute("src") if img_el else None

                    source_id = href.rstrip("/").split("/")[-1]
                    listings.append(
                        Listing(
                            source="autotrader",
                            source_id=source_id,
                            url=href if href.startswith("http") else f"https://www.autotrader.co.uk{href}",
                            title=title.strip(),
                            price=_parse_price(price_text) if price_text else None,
                            image_url=img,
                        )
                    )
                except Exception:
                    continue
        except Exception as e:
            # Most common outcome first run: a bot-check page instead of results.
            print(f"[autotrader] fetch failed or was blocked: {e}")
        finally:
            await browser.close()

    return listings


def _parse_price(text: str):
    digits = "".join(c for c in text if c.isdigit())
    return float(digits) if digits else None
