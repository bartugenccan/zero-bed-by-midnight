"""Load the incident exports. The files are read once and never written to."""

from __future__ import annotations

import csv
import os
from pathlib import Path

from .models import Listing, Ticket

DEFAULT_LISTINGS = "Lisbon Open Listings Export (16 Nov 2026).csv"
DEFAULT_TICKETS = "Lisbon Stranded Guest Tickets (16 Nov 2026).csv"


def default_listings_path() -> Path:
    return Path(os.environ.get("ZBM_LISTINGS_CSV", DEFAULT_LISTINGS))


def default_tickets_path() -> Path:
    return Path(os.environ.get("ZBM_TICKETS_CSV", DEFAULT_TICKETS))


def _blank_to_none(row: dict[str, str]) -> dict[str, str | None]:
    return {k: (v if v.strip() != "" else None) for k, v in row.items()}


def load_listings(path: Path) -> dict[str, Listing]:
    with open(path, encoding="utf-8", newline="") as f:
        listings = [Listing.model_validate(_blank_to_none(r)) for r in csv.DictReader(f)]
    by_id = {l.listing_id: l for l in listings}
    if len(by_id) != len(listings):
        raise ValueError(f"Duplicate listing_id in {path}")
    return by_id


def load_tickets(path: Path) -> dict[str, Ticket]:
    with open(path, encoding="utf-8", newline="") as f:
        tickets = [Ticket.model_validate(_blank_to_none(r)) for r in csv.DictReader(f)]
    by_id = {t.ticket_id: t for t in tickets}
    if len(by_id) != len(tickets):
        raise ValueError(f"Duplicate ticket_id in {path}")
    return by_id
