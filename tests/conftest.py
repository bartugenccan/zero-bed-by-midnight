from __future__ import annotations

from pathlib import Path

import pytest
from fastmcp import Client

from zero_bed_by_midnight.server import create_server

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SMALL_LISTINGS = FIXTURES / "listings_small.csv"
SMALL_TICKETS = FIXTURES / "tickets_small.csv"
REAL_LISTINGS = ROOT / "Lisbon Open Listings Export (16 Nov 2026).csv"
REAL_TICKETS = ROOT / "Lisbon Stranded Guest Tickets (16 Nov 2026).csv"

real_data = pytest.mark.skipif(
    not (REAL_LISTINGS.exists() and REAL_TICKETS.exists()),
    reason="Real incident exports are git-ignored and not present.",
)


@pytest.fixture
async def small_client():
    async with Client(create_server(SMALL_LISTINGS, SMALL_TICKETS)) as c:
        yield c


@pytest.fixture
async def real_client():
    async with Client(create_server(REAL_LISTINGS, REAL_TICKETS)) as c:
        yield c
