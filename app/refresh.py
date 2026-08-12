import asyncio
from datetime import datetime
from sqlmodel import Session, select
from .db import engine
from .models import Listing
from .aggregator import normalize_and_dedupe
from .sources import ebay, gumtree, autotrader, facebook


async def refresh_all(query: str = "car"):
    """Fetch from every source, normalize, dedupe, upsert into DB.
    Runs sources concurrently and never lets one failing source kill the rest."""

    async def safe(coro, name):
        try:
            return await coro
        except Exception as e:
            print(f"[refresh] {name} failed: {e}")
            return []

    results = await asyncio.gather(
        safe(ebay.fetch_listings(query), "ebay"),
        safe(gumtree.fetch_listings(query), "gumtree"),
        safe(autotrader.fetch_listings(), "autotrader"),
        safe(facebook.fetch_listings(), "facebook"),
    )

    all_listings = [l for batch in results for l in batch]
    deduped = normalize_and_dedupe(all_listings)

    with Session(engine) as session:
        for listing in deduped:
            existing = session.exec(
                select(Listing).where(
                    Listing.source == listing.source,
                    Listing.source_id == listing.source_id,
                )
            ).first()
            if existing:
                existing.price = listing.price
                existing.last_seen = datetime.utcnow()
                session.add(existing)
            else:
                session.add(listing)
        session.commit()

    print(f"[refresh] done - {len(deduped)} listings after dedupe "
          f"(from {len(all_listings)} raw)")
    return deduped
