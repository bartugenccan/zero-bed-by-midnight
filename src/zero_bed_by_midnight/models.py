"""Typed records for the Lisbon check-in incident (16 November 2026)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

OPEN_LISTING_ID = r"^LST-1\d{5}$"
"""Open Lisbon listings are LST-100001 to LST-100450. Originals (LST-2xxxxx) never match."""

OpenListingId = Annotated[
    str,
    Field(
        pattern=OPEN_LISTING_ID,
        description="An open-listing ID from the listings export, e.g. LST-100123.",
    ),
]
TicketId = Annotated[
    str,
    Field(pattern=r"^LIS-TKT-\d{4}$", description="Ticket ID, e.g. LIS-TKT-0007."),
]
Money = Annotated[Decimal, Field(decimal_places=2)]


class ListingStatus(StrEnum):
    available = "available"
    on_hold = "on_hold"
    booked = "booked"


class SafetyCondition(StrEnum):
    """The five safety conditions in the AirCover rules."""

    injury_or_medical_need = "injury_or_medical_need"
    threat_or_violence = "threat_or_violence"
    nowhere_safe_to_wait = "nowhere_safe_to_wait"
    unaccompanied_minor = "unaccompanied_minor"
    stated_fear_of_person = "stated_fear_of_person"


class Ticket(BaseModel):
    """One row of the stranded-guest ticket export. Loaded server-side only."""

    ticket_id: str
    opened_at: datetime
    reservation_id: str
    guest_name: str
    guest_language: str
    original_listing_id: str
    original_listing_title: str
    neighborhood: str
    property_type: str
    bedrooms: int
    party_size: int
    check_in_date: date
    check_out_date: date
    nightly_price: Money
    total_paid: Money
    host_id: str
    host_cancelled_at: datetime | None
    host_last_reply_at: datetime | None
    guest_requested: str
    guest_message: str
    expected_outcome: str = Field(
        exclude=True,
        description="Reviewed answer key. Never returned by a tool and never used to decide.",
    )

    @property
    def nights(self) -> int:
        return (self.check_out_date - self.check_in_date).days


class Reservation(BaseModel):
    """What lookup_reservation returns. It has no answer-key field by design."""

    ticket_id: str
    reservation_id: str
    opened_at: datetime
    guest_name: str
    guest_language: str
    original_listing_id: str
    original_listing_title: str
    neighborhood: str
    property_type: str
    bedrooms: int
    party_size: int
    check_in_date: date
    check_out_date: date
    nights: int
    nightly_price: Money
    total_paid: Money
    price_ceiling: Money = Field(description="1.20 x the original nightly price.")
    host_id: str
    host_cancelled_at: datetime | None
    host_last_reply_at: datetime | None
    guest_requested: str
    guest_message: str
    case_state: Literal["open", "rebooked", "refunded", "handed_off"]


class Listing(BaseModel):
    """One open Lisbon listing from the export."""

    listing_id: OpenListingId
    host_id: str
    neighborhood: str
    bedrooms: int
    max_guests: int
    title: str
    nightly_price: Money
    available_from: date
    available_to: date
    status: ListingStatus
    instant_book: bool
    rating: float | None = None


class ListingMatch(BaseModel):
    """A listing that passed all five comparable-home tests for one ticket."""

    listing_id: OpenListingId
    neighborhood: str
    same_neighborhood: bool
    bedrooms: int
    max_guests: int
    title: str
    nightly_price: Money
    available_from: date
    available_to: date
    uplift_total: Money = Field(
        description="(nightly_price - original nightly_price) x nights, 0 if not higher."
    )


class HoldResult(BaseModel):
    ticket_id: str
    listing_id: OpenListingId
    nights: int
    nightly_price: Money
    uplift_total: Money
    uplift_budget_remaining: Money


class RefundResult(BaseModel):
    ticket_id: str
    amount: Money
    total_paid: Money
    stay_closed: bool = True


class HostMessageResult(BaseModel):
    ticket_id: str
    host_id: str
    delivered: Literal["simulated"] = "simulated"
    message: str


class HandoffResult(BaseModel):
    ticket_id: str
    conditions: list[SafetyCondition]
    summary: str
    status: Literal["handed_off"] = "handed_off"
    note: str = "A live safety agent from Trust and Safety now owns this case."
