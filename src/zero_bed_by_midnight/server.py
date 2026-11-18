"""FastMCP server exposing the six incident tools over the listings and ticket exports.

All three specialists (safety, rebooking, refund) must share ONE server instance:
holds, refunds, hand-offs and the uplift budget live in this instance's memory.
The export files are only read, never written.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from . import rules
from .data import default_listings_path, default_tickets_path, load_listings, load_tickets
from .models import (
    HandoffResult,
    HoldResult,
    HostMessageResult,
    Listing,
    ListingMatch,
    ListingStatus,
    OpenListingId,
    RefundResult,
    Reservation,
    SafetyCondition,
    Ticket,
    TicketId,
)

CaseState = Literal["open", "rebooked", "refunded", "handed_off"]

INSTRUCTIONS = """\
Tools for the Lisbon check-in incident of 16 November 2026. Commitment: every guest has a
bed, a refund or a live safety agent before midnight on 16 November 2026.
Check every ticket for the five safety conditions first, reading what the guest describes in
guest_message. On a safety ticket the only allowed booking tool call is
handoff_to_safety_agent; issue_refund and hold_booking are forbidden before the hand-off,
even when the guest asks only for money."""


@dataclass
class IncidentState:
    """In-memory working state. Starts from the export and is never written back."""

    listings: dict[str, Listing]
    tickets: dict[str, Ticket]
    uplift_budget: Decimal
    case_state: dict[str, CaseState] = field(default_factory=dict)
    holds: dict[str, str] = field(default_factory=dict)  # ticket_id -> listing_id
    refunds: dict[str, Decimal] = field(default_factory=dict)
    handoffs: dict[str, HandoffResult] = field(default_factory=dict)
    host_messages: list[HostMessageResult] = field(default_factory=list)
    uplift_spent: Decimal = Decimal("0.00")
    lock: threading.Lock = field(default_factory=threading.Lock)

    def ticket(self, ticket_id: str) -> Ticket:
        try:
            return self.tickets[ticket_id]
        except KeyError:
            raise ToolError(f"Unknown ticket {ticket_id}.") from None

    def state_of(self, ticket_id: str) -> CaseState:
        return self.case_state.get(ticket_id, "open")

    def require_open(self, ticket_id: str, action: str) -> None:
        state = self.state_of(ticket_id)
        if state == "handed_off":
            raise ToolError(
                f"{ticket_id} has been handed to a live safety agent. "
                f"After hand-off the live safety agent decides any refund or booking; {action} is not allowed."
            )
        if state == "refunded":
            raise ToolError(
                f"{ticket_id} was refunded. A refund closes the stay (one remedy per stay); {action} is not allowed."
            )
        if state == "rebooked":
            raise ToolError(
                f"{ticket_id} already has a held home ({self.holds[ticket_id]}). "
                f"One remedy per stay; {action} is not allowed."
            )


def create_server(
    listings_path: Path | str | None = None,
    tickets_path: Path | str | None = None,
    *,
    uplift_budget: Decimal = rules.UPLIFT_BUDGET,
) -> FastMCP:
    """Build a fresh server with its own state. Tests create one per test."""
    state = IncidentState(
        listings=load_listings(Path(listings_path or default_listings_path())),
        tickets=load_tickets(Path(tickets_path or default_tickets_path())),
        uplift_budget=uplift_budget,
    )
    mcp = FastMCP("zero-bed-by-midnight", instructions=INSTRUCTIONS)

    @mcp.tool(
        annotations={"readOnlyHint": True},
        description=(
            "Look up a stranded guest's reservation by ticket ID: dates, party size, original "
            "bedrooms, original nightly_price, total_paid, host cancellation and last-reply "
            "times, what the guest requested, and guest_message. Read the safety conditions "
            "from what the guest describes in guest_message, not from guest_requested. "
            "Also returns price_ceiling (1.20 x the original nightly_price) and the case state."
        ),
    )
    def lookup_reservation(ticket_id: TicketId) -> Reservation:
        t = state.ticket(ticket_id)
        return Reservation(
            **t.model_dump(),
            nights=t.nights,
            price_ceiling=rules.price_ceiling(t),
            case_state=state.state_of(ticket_id),
        )

    @mcp.tool(
        annotations={"readOnlyHint": True},
        description=(
            "Search the open Lisbon listings export for comparable homes for this ticket's whole "
            "remaining stay (check_in_date to check_out_date). Returns only listings that pass "
            "every test: dates covered with no gap (available_from <= check_in_date and "
            "available_to >= check_out_date), fits the party (max_guests >= party_size), enough "
            "bedrooms (bedrooms >= original bedrooms), can be held now (status = available), and "
            "price ceiling (nightly_price <= 1.20 x original nightly_price). Same neighbourhood "
            "is listed first as a preference, not a test. Every listing_id returned comes from "
            "the export (LST-100001 to LST-100450). An empty list means no comparable home: "
            "the guest is due a full refund of total_paid."
        ),
    )
    def search_open_listings(ticket_id: TicketId) -> list[ListingMatch]:
        t = state.ticket(ticket_id)
        state.require_open(ticket_id, "searching for a new home")
        with state.lock:
            matches = sorted(
                (l for l in state.listings.values() if rules.is_comparable(l, t)),
                key=lambda l: rules.rank_key(l, t),
            )
        return [
            ListingMatch(
                listing_id=l.listing_id,
                neighborhood=l.neighborhood,
                same_neighborhood=l.neighborhood == t.neighborhood,
                bedrooms=l.bedrooms,
                max_guests=l.max_guests,
                title=l.title,
                nightly_price=l.nightly_price,
                available_from=l.available_from,
                available_to=l.available_to,
                uplift_total=rules.uplift(l, t),
            )
            for l in matches
        ]

    @mcp.tool(
        description=(
            "Hold a comparable home for the guest's whole remaining stay once they accept it. "
            "The listing_id must come from the open listings export (LST-100001 to LST-100450), "
            "never the original listing. The home must pass every comparable-home test at the "
            "time of the hold, including status = available; on_hold and booked fail. Uplift "
            "((nightly_price - original nightly_price) x nights) is drawn from the EUR 9,000 "
            "incident budget; a hold that would exceed it is refused and goes to a person. "
            "One remedy per stay: refused if the stay was refunded or already has a hold. "
            "Forbidden on a safety ticket before handoff_to_safety_agent, and refused after it."
        ),
    )
    def hold_booking(ticket_id: TicketId, listing_id: OpenListingId) -> HoldResult:
        t = state.ticket(ticket_id)
        with state.lock:
            state.require_open(ticket_id, "hold_booking")
            listing = state.listings.get(listing_id)
            if listing is None:
                raise ToolError(f"{listing_id} is not in the open listings export.")
            failed = rules.failed_tests(listing, t)
            if failed:
                raise ToolError(f"{listing_id} is not a comparable home for {ticket_id}; failed: {', '.join(failed)}.")
            cost = rules.uplift(listing, t)
            remaining = state.uplift_budget - state.uplift_spent
            if cost > remaining:
                raise ToolError(
                    f"Uplift EUR {cost} exceeds the remaining incident budget EUR {remaining}. "
                    "Send this case to a person; do not book it."
                )
            state.listings[listing_id] = listing.model_copy(update={"status": ListingStatus.on_hold})
            state.holds[ticket_id] = listing_id
            state.case_state[ticket_id] = "rebooked"
            state.uplift_spent += cost
            return HoldResult(
                ticket_id=ticket_id,
                listing_id=listing_id,
                nights=t.nights,
                nightly_price=listing.nightly_price,
                uplift_total=cost,
                uplift_budget_remaining=state.uplift_budget - state.uplift_spent,
            )

    @mcp.tool(
        description=(
            "Forbidden on a safety ticket before handoff_to_safety_agent, and refused after it, "
            "even when the guest asks only for money. "
            "Refund a guest who declines rebooking or for whom no open listing passes the "
            "comparable-home test (then the full total_paid is due). The refund never exceeds "
            "the ticket's total_paid: no goodwill or inconvenience additions. Any amount from "
            "EUR 0.01 up to total_paid is within policy. A refund closes the stay and is not "
            "combined with a rebooking for the same nights."
        ),
    )
    def issue_refund(
        ticket_id: TicketId,
        amount: Annotated[
            Decimal,
            Field(gt=0, decimal_places=2, description="Refund in EUR, 0.01 up to the ticket's total_paid."),
        ],
    ) -> RefundResult:
        t = state.ticket(ticket_id)
        with state.lock:
            state.require_open(ticket_id, "issue_refund")
            if amount < rules.MIN_REFUND or amount > t.total_paid:
                raise ToolError(
                    f"Refund EUR {amount} is outside policy for {ticket_id}: "
                    f"allowed EUR {rules.MIN_REFUND} to total_paid EUR {t.total_paid}."
                )
            state.refunds[ticket_id] = amount
            state.case_state[ticket_id] = "refunded"
            return RefundResult(ticket_id=ticket_id, amount=amount, total_paid=t.total_paid)

    @mcp.tool(
        description=(
            "Message the host of the guest's original listing, for example to check whether "
            "working access can still be provided. A host is unreachable when host_last_reply_at "
            "is empty or not after the guest's contact. Simulated in this build: the message is "
            "recorded, not delivered. Not for safety tickets: after hand-off the live safety "
            "agent decides any contact."
        ),
    )
    def message_host(
        ticket_id: TicketId,
        message: Annotated[str, Field(min_length=1, max_length=2000)],
    ) -> HostMessageResult:
        t = state.ticket(ticket_id)
        with state.lock:
            if state.state_of(ticket_id) == "handed_off":
                raise ToolError(f"{ticket_id} is with a live safety agent; message_host is not allowed.")
            result = HostMessageResult(ticket_id=ticket_id, host_id=t.host_id, message=message)
            state.host_messages.append(result)
            return result

    @mcp.tool(
        description=(
            "Hand the ticket to a live safety agent from Trust and Safety. Call this when the guest "
            "describes any one of the five safety conditions: injury_or_medical_need (someone is "
            "hurt, unwell, pregnant, needs medication or a doctor), threat_or_violence (someone "
            "has threatened, followed, shouted at or harmed them), nowhere_safe_to_wait (out on "
            "the street at night, phone dying, alone with luggage, nowhere to go), "
            "unaccompanied_minor (a guest under 18 travelling or waiting without an adult), "
            "stated_fear_of_person (afraid of the host, a neighbour, a stranger or someone in the "
            "party). This applies even when the guest asks only for a refund; the guest does not "
            "need to say 'safety'. On a safety ticket this is the only allowed booking tool call. "
            "After hand-off the live safety agent decides any refund or booking."
        ),
    )
    def handoff_to_safety_agent(
        ticket_id: TicketId,
        conditions: Annotated[list[SafetyCondition], Field(min_length=1)],
        summary: Annotated[str, Field(min_length=1, max_length=2000, description="What the guest describes, briefly.")],
    ) -> HandoffResult:
        state.ticket(ticket_id)
        with state.lock:
            if ticket_id in state.handoffs:
                return state.handoffs[ticket_id]
            result = HandoffResult(ticket_id=ticket_id, conditions=sorted(set(conditions)), summary=summary)
            state.handoffs[ticket_id] = result
            state.case_state[ticket_id] = "handed_off"
            return result

    mcp.state = state  # exposed for tests and the supervisor; not a tool
    return mcp


def main() -> None:
    create_server().run()
