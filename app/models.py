from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Listing(SQLModel, table=True):
    """Unified schema every source gets normalized into."""
    id: Optional[int] = Field(default=None, primary_key=True)

    source: str                 # "ebay" | "gumtree" | "autotrader" | "facebook"
    source_id: str              # the listing's ID on its origin site
    url: str

    title: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    price: Optional[float] = None
    mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    location: Optional[str] = None
    seller_type: Optional[str] = None   # "private" | "dealer"

    image_url: Optional[str] = None
    description: Optional[str] = None

    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)

    # de-dup helper: same physical car posted on 2+ sites
    dedup_key: Optional[str] = None


class ListingFilter(SQLModel):
    make: Optional[str] = None
    model: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    max_mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_type: Optional[str] = None
    location: Optional[str] = None
    seller_type: Optional[str] = None
    source: Optional[str] = None        # filter to a single source if wanted
    sort_by: str = "last_seen"          # "price" | "mileage" | "year" | "last_seen"
    sort_dir: str = "desc"
