import re
from typing import List
from rapidfuzz import fuzz
from .models import Listing

MAKES = [
    "ford", "vauxhall", "volkswagen", "vw", "bmw", "audi", "mercedes",
    "toyota", "honda", "nissan", "hyundai", "kia", "peugeot", "renault",
    "skoda", "seat", "mini", "land rover", "range rover", "volvo", "mazda",
    "fiat", "jaguar", "porsche", "tesla", "citroen",
]


def normalize(listing: Listing) -> Listing:
    """Extract make/year/etc from free-text titles when the source didn't
    give structured fields (common with Gumtree/Facebook)."""
    title_lower = listing.title.lower()

    if not listing.make:
        for make in MAKES:
            if make in title_lower:
                listing.make = make.title()
                break

    if not listing.year:
        match = re.search(r"\b(19[5-9]\d|20[0-3]\d)\b", listing.title)
        if match:
            listing.year = int(match.group(1))

    if not listing.mileage:
        match = re.search(r"([\d,]+)\s*(miles|mi\b)", title_lower)
        if match:
            listing.mileage = int(match.group(1).replace(",", ""))

    listing.dedup_key = f"{listing.make}|{listing.year}|{round(listing.price or 0, -2)}"
    return listing


def dedupe(listings: List[Listing], title_threshold: int = 85) -> List[Listing]:
    """Collapse the same physical car posted across multiple sites into one
    entry (keeps the first one seen, tags nothing extra - simple by design).
    Groups by dedup_key first (cheap), then fuzzy-matches titles within
    each group (accurate but O(n^2), fine at this scale)."""
    groups: dict[str, List[Listing]] = {}
    for l in listings:
        groups.setdefault(l.dedup_key or "unknown", []).append(l)

    result: List[Listing] = []
    for group in groups.values():
        kept: List[Listing] = []
        for candidate in group:
            is_dupe = any(
                fuzz.token_sort_ratio(candidate.title, k.title) >= title_threshold
                for k in kept
            )
            if not is_dupe:
                kept.append(candidate)
        result.extend(kept)
    return result


def normalize_and_dedupe(listings: List[Listing]) -> List[Listing]:
    normalized = [normalize(l) for l in listings]
    return dedupe(normalized)
