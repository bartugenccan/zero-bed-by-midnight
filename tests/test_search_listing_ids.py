"""Proof that search_open_listings only returns real listing_ids from the export.

The expected sets are recomputed here from the raw CSV with the csv module and the
written rules. Nothing is imported from the server's loader or rules module, so the
check does not just repeat the code it is checking.
"""

from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from zero_bed_by_midnight.server import create_server

from .conftest import REAL_LISTINGS, REAL_TICKETS, SMALL_LISTINGS, SMALL_TICKETS, real_data

ID_PATTERN = re.compile(r"^LST-1\d{5}$")


def read_rows(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def export_ids(path: Path) -> set[str]:
    return {r["listing_id"] for r in read_rows(path)}


def expected_ids(listings_path: Path, tickets_path: Path, ticket_id: str) -> set[str]:
    """The five comparable-home tests, written out again from the policy text."""
    t = next(r for r in read_rows(tickets_path) if r["ticket_id"] == ticket_id)
    check_in, check_out = date.fromisoformat(t["check_in_date"]), date.fromisoformat(t["check_out_date"])
    ceiling = Decimal(t["nightly_price"]) * Decimal("1.20")
    return {
        l["listing_id"]
        for l in read_rows(listings_path)
        if date.fromisoformat(l["available_from"]) <= check_in
        and date.fromisoformat(l["available_to"]) >= check_out
        and int(l["max_guests"]) >= int(t["party_size"])
        and int(l["bedrooms"]) >= int(t["bedrooms"])
        and l["status"] == "available"
        and Decimal(l["nightly_price"]) <= ceiling
    }


async def search(client: Client, ticket_id: str) -> list[str]:
    result = await client.call_tool("search_open_listings", {"ticket_id": ticket_id})
    return [m["listing_id"] for m in result.structured_content["result"]]


# --- 1. Real export: every ID returned is in the export, and the set is exactly right ---

REAL_TICKET_IDS = [r["ticket_id"] for r in read_rows(REAL_TICKETS)] if REAL_TICKETS.exists() else []


@real_data
async def test_real_export_has_450_unique_open_ids():
    rows = read_rows(REAL_LISTINGS)
    ids = [r["listing_id"] for r in rows]
    assert len(ids) == 450 == len(set(ids))
    assert all(ID_PATTERN.match(i) for i in ids)


@real_data
@pytest.mark.parametrize("ticket_id", REAL_TICKET_IDS)
async def test_real_search_returns_only_export_ids(real_client, ticket_id):
    returned = await search(real_client, ticket_id)
    real_ids = export_ids(REAL_LISTINGS)
    original = next(r["original_listing_id"] for r in read_rows(REAL_TICKETS) if r["ticket_id"] == ticket_id)

    assert len(returned) == len(set(returned)), "no duplicates"
    assert set(returned) <= real_ids, "subset of the export"
    assert original not in returned, "never the original listing"
    assert all(ID_PATTERN.match(i) for i in returned)
    assert set(returned) == expected_ids(REAL_LISTINGS, REAL_TICKETS, ticket_id), "exactly the comparable set"


@real_data
async def test_real_search_covers_all_60_tickets(real_client):
    assert len(REAL_TICKET_IDS) == 60
    returned = set()
    for ticket_id in REAL_TICKET_IDS:
        returned |= set(await search(real_client, ticket_id))
    assert returned <= export_ids(REAL_LISTINGS)


# --- 2. Swapped export: results follow whatever file the server is given ---


async def test_swapped_export_only_returns_ids_from_that_file(small_client):
    small_ids = export_ids(SMALL_LISTINGS)
    for ticket_id in ("LIS-TKT-9001", "LIS-TKT-9002", "LIS-TKT-9003", "LIS-TKT-9004"):
        returned = await search(small_client, ticket_id)
        assert set(returned) <= small_ids
        assert set(returned) == expected_ids(SMALL_LISTINGS, SMALL_TICKETS, ticket_id)


async def test_swapped_export_exact_result_and_order(small_client):
    # 132.00 at the 110.00 ceiling passes; 132.01, late start, on_hold, too small,
    # too few bedrooms and booked all fail. Same neighbourhood is listed first.
    assert await search(small_client, "LIS-TKT-9001") == ["LST-100901", "LST-100907"]


async def test_no_match_returns_empty_list(small_client):
    assert await search(small_client, "LIS-TKT-9002") == []  # party of 10
    assert await search(small_client, "LIS-TKT-9003") == []  # ceiling 60.00, nothing that cheap


async def test_held_listing_is_not_returned_again(small_client):
    await small_client.call_tool("hold_booking", {"ticket_id": "LIS-TKT-9001", "listing_id": "LST-100901"})
    assert "LST-100901" not in await search(small_client, "LIS-TKT-9004")


# --- 3. Schema and negatives ---


async def test_output_schema_constrains_listing_id(small_client):
    tool = next(t for t in await small_client.list_tools() if t.name == "search_open_listings")
    item = tool.output_schema["properties"]["result"]["items"]
    assert item["properties"]["listing_id"]["pattern"] == ID_PATTERN.pattern


@pytest.mark.parametrize("bad_id", ["LST-999999", "LST-200001", "LST-100450", "lst-100901", "LST-1009010"])
async def test_hold_rejects_ids_not_in_export(small_client, bad_id):
    # LST-100450 is a real-looking ID but not in this export; the others fail the pattern.
    with pytest.raises(ToolError):
        await small_client.call_tool("hold_booking", {"ticket_id": "LIS-TKT-9001", "listing_id": bad_id})


async def test_export_file_is_never_written(tmp_path):
    copy = tmp_path / "listings.csv"
    copy.write_bytes(SMALL_LISTINGS.read_bytes())
    before = copy.read_bytes()
    async with Client(create_server(copy, SMALL_TICKETS)) as c:
        await c.call_tool("hold_booking", {"ticket_id": "LIS-TKT-9001", "listing_id": "LST-100901"})
    assert copy.read_bytes() == before
