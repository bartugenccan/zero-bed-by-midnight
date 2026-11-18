"""AirCover Rebooking and Refund Rules as plain functions (no MCP here)."""

from __future__ import annotations

from decimal import Decimal

from .models import Listing, ListingStatus, Ticket

PRICE_CEILING_FACTOR = Decimal("1.20")
UPLIFT_BUDGET = Decimal("9000.00")
MIN_REFUND = Decimal("0.01")
CENT = Decimal("0.01")


def price_ceiling(ticket: Ticket) -> Decimal:
    """120% of the ticket's original nightly price. EUR 110.00 gives EUR 132.00."""
    return (ticket.nightly_price * PRICE_CEILING_FACTOR).quantize(CENT)


def failed_tests(listing: Listing, ticket: Ticket) -> list[str]:
    """Names of the comparable-home tests this listing fails. Empty means comparable."""
    failed = []
    if not (
        listing.available_from <= ticket.check_in_date
        and listing.available_to >= ticket.check_out_date
    ):
        failed.append("dates_covered")
    if listing.max_guests < ticket.party_size:
        failed.append("fits_the_party")
    if listing.bedrooms < ticket.bedrooms:
        failed.append("enough_bedrooms")
    if listing.status != ListingStatus.available:
        failed.append("can_be_held_now")
    if listing.nightly_price > price_ceiling(ticket):
        failed.append("price_ceiling")
    return failed


def is_comparable(listing: Listing, ticket: Ticket) -> bool:
    return not failed_tests(listing, ticket)


def uplift(listing: Listing, ticket: Ticket) -> Decimal:
    """(new nightly price - original nightly price) x nights, never below zero."""
    per_night = max(Decimal("0"), listing.nightly_price - ticket.nightly_price)
    return (per_night * ticket.nights).quantize(CENT)


def rank_key(listing: Listing, ticket: Ticket) -> tuple[int, Decimal, str]:
    """Same neighbourhood first (a preference, not a test), then cheapest, then ID."""
    return (0 if listing.neighborhood == ticket.neighborhood else 1, listing.nightly_price, listing.listing_id)
