"""
eBay Browse API integration. This is the one source that's fully legit and stable -
no scraping, uses eBay's official public API.

Setup:
1. Register an app at https://developer.ebay.com/ (free)
2. Get your Client ID + Client Secret
3. Put them in backend/.env as EBAY_CLIENT_ID / EBAY_CLIENT_SECRET
"""
import os
import time
import httpx
from typing import List
from ..models import Listing

_token_cache = {"token": None, "expires_at": 0}


async def _get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    client_id = os.getenv("EBAY_CLIENT_ID")
    client_secret = os.getenv("EBAY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("EBAY_CLIENT_ID / EBAY_CLIENT_SECRET not set in .env")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            auth=(client_id, client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data["expires_in"]
        return _token_cache["token"]


async def fetch_listings(query: str = "car", limit: int = 50) -> List[Listing]:
    token = await _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
            },
            params={
                "q": query,
                "category_ids": "9801",  # eBay Motors > Cars
                "limit": limit,
            },
        )
        resp.raise_for_status()
        items = resp.json().get("itemSummaries", [])

    listings = []
    for item in items:
        price = item.get("price", {}).get("value")
        listings.append(
            Listing(
                source="ebay",
                source_id=item["itemId"],
                url=item.get("itemWebUrl", ""),
                title=item.get("title", ""),
                price=float(price) if price else None,
                location=item.get("itemLocation", {}).get("postalCode"),
                image_url=item.get("image", {}).get("imageUrl"),
            )
        )
    return listings
