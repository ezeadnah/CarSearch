from contextlib import asynccontextmanager
from typing import Optional, List
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from .db import init_db, engine
from .models import Listing
from .refresh import refresh_all

load_dotenv()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # refresh every 30 min - tune this, especially down for facebook's sake
    scheduler.add_job(refresh_all, "interval", minutes=30, next_run_time=None)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="CarHuntr API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before shipping
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/listings", response_model=List[Listing])
def get_listings(
    make: Optional[str] = None,
    model: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    max_mileage: Optional[int] = None,
    fuel_type: Optional[str] = None,
    transmission: Optional[str] = None,
    body_type: Optional[str] = None,
    location: Optional[str] = None,
    seller_type: Optional[str] = None,
    source: Optional[str] = None,
    sort_by: str = "last_seen",
    sort_dir: str = "desc",
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    with Session(engine) as session:
        stmt = select(Listing)

        if make:
            stmt = stmt.where(Listing.make == make)
        if model:
            stmt = stmt.where(Listing.model == model)
        if min_price is not None:
            stmt = stmt.where(Listing.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Listing.price <= max_price)
        if min_year is not None:
            stmt = stmt.where(Listing.year >= min_year)
        if max_year is not None:
            stmt = stmt.where(Listing.year <= max_year)
        if max_mileage is not None:
            stmt = stmt.where(Listing.mileage <= max_mileage)
        if fuel_type:
            stmt = stmt.where(Listing.fuel_type == fuel_type)
        if transmission:
            stmt = stmt.where(Listing.transmission == transmission)
        if body_type:
            stmt = stmt.where(Listing.body_type == body_type)
        if location:
            stmt = stmt.where(Listing.location == location)
        if seller_type:
            stmt = stmt.where(Listing.seller_type == seller_type)
        if source:
            stmt = stmt.where(Listing.source == source)

        sort_col = getattr(Listing, sort_by, Listing.last_seen)
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.offset(offset).limit(limit)

        return session.exec(stmt).all()


@app.post("/refresh")
async def trigger_refresh(query: str = "car"):
    """Manually trigger a refresh instead of waiting for the schedule."""
    listings = await refresh_all(query)
    return {"refreshed": len(listings)}


@app.get("/health")
def health():
    return {"status": "ok"}
