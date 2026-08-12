"""
Gumtree has no public API. This is a best-effort HTML scraper.

CAVEATS (read before relying on this):
- Scraping Gumtree violates their Terms of Service. Use at your own risk,
  keep request volume low, and expect to get IP-blocked if you hit it hard.
- CSS selectors below WILL break when Gumtree redesigns their site. Treat
  this as a starting point you maintain, not a fire-and-forget module.
- Consider adding a random delay + rotating user-agent if running this
  on a schedule, and cache aggressively so you're not re-fetching often.
"""
import httpx
from bs4 import BeautifulSoup
from typing import List
from ..models import Listing

BASE_URL = "https://www.gumtree.com/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}


async def fetch_listings(query: str = "car", location: str = "uk", limit: int = 30) -> List[Listing]:
    params = {"search_category": "cars", "q": query}
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

    listings = []
    # NOTE: selector guesses based on Gumtree's typical listing card structure
    # as of mid-2026. Inspect the live page and adjust if this returns nothing.
    cards = soup.select("article[data-q='search-result']")[:limit]
    for card in cards:
        try:
            title_el = card.select_one("[data-q='tile-title']")
            price_el = card.select_one("[data-q='tile-price']")
            link_el = card.select_one("a[href]")
            img_el = card.select_one("img")

            if not title_el or not link_el:
                continue

            href = link_el["href"]
            source_id = href.rstrip("/").split("/")[-1]

            listings.append(
                Listing(
                    source="gumtree",
                    source_id=source_id,
                    url=href if href.startswith("http") else f"https://www.gumtree.com{href}",
                    title=title_el.get_text(strip=True),
                    price=_parse_price(price_el.get_text(strip=True)) if price_el else None,
                    image_url=img_el.get("src") if img_el else None,
                    location=location,
                )
            )
        except Exception:
            # one bad card shouldn't kill the whole batch
            continue

    return listings


def _parse_price(text: str):
    digits = "".join(c for c in text if c.isdigit())
    return float(digits) if digits else None
