"""Policy behaviour of the six tools and the specialist tool allocation."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from zero_bed_by_midnight.permissions import ALL_TOOLS, SPECIALIST_TOOLS
from zero_bed_by_midnight.server import create_server

from .conftest import SMALL_LISTINGS, SMALL_TICKETS

HOLD = "hold_booking"
REFUND = "issue_refund"


async def call(c: Client, tool: str, **args):
    return (await c.call_tool(tool, args)).structured_content


# --- Tool surface ---


async def test_exactly_the_six_tools_with_policy_descriptions(small_client):
    tools = {t.name: t for t in await small_client.list_tools()}
    assert set(tools) == ALL_TOOLS
    d = {name: t.description for name, t in tools.items()}
    assert "only allowed booking tool call" in d["handoff_to_safety_agent"]
    assert "even when the guest asks only for a refund" in d["handoff_to_safety_agent"]
    assert "1.20 x original nightly_price" in d["search_open_listings"]
    assert "never exceeds" in d[REFUND] and "total_paid" in d[REFUND]
    assert "Forbidden on a safety ticket before handoff_to_safety_agent" in d[HOLD]
    assert "Forbidden on a safety ticket before handoff_to_safety_agent" in d[REFUND]
    assert "Simulated" in d["message_host"]


async def test_lookup_never_returns_the_answer_key(small_client):
    r = await call(small_client, "lookup_reservation", ticket_id="LIS-TKT-9004")
    assert "expected_outcome" not in r
    assert r["price_ceiling"] == "132.00"
    assert r["nights"] == 3


# --- Price ceiling and comparable-home tests at hold time ---


async def test_hold_at_exact_ceiling_passes_one_cent_over_fails(small_client):
    with pytest.raises(ToolError, match="price_ceiling"):
        await small_client.call_tool(HOLD, {"ticket_id": "LIS-TKT-9001", "listing_id": "LST-100902"})
    r = await call(small_client, HOLD, ticket_id="LIS-TKT-9001", listing_id="LST-100901")
    assert r["uplift_total"] == "66.00"  # (132.00 - 110.00) x 3 nights
    assert r["uplift_budget_remaining"] == "8934.00"


@pytest.mark.parametrize(
    ("listing_id", "failed"),
    [
        ("LST-100903", "dates_covered"),
        ("LST-100904", "can_be_held_now"),
        ("LST-100905", "fits_the_party"),
        ("LST-100906", "enough_bedrooms"),
        ("LST-100908", "can_be_held_now"),
    ],
)
async def test_hold_refuses_non_comparable_homes(small_client, listing_id, failed):
    with pytest.raises(ToolError, match=failed):
        await small_client.call_tool(HOLD, {"ticket_id": "LIS-TKT-9001", "listing_id": listing_id})


async def test_hold_over_budget_is_refused():
    async with Client(create_server(SMALL_LISTINGS, SMALL_TICKETS, uplift_budget=Decimal("10.00"))) as c:
        with pytest.raises(ToolError, match="budget"):
            await c.call_tool(HOLD, {"ticket_id": "LIS-TKT-9001", "listing_id": "LST-100901"})


# --- Refund cap ---


@pytest.mark.parametrize("amount", ["330.01", "0", "-5", "0.001"])
async def test_refund_outside_policy_is_refused(small_client, amount):
    with pytest.raises(ToolError):
        await small_client.call_tool(REFUND, {"ticket_id": "LIS-TKT-9001", "amount": amount})


async def test_full_refund_up_to_total_paid(small_client):
    r = await call(small_client, REFUND, ticket_id="LIS-TKT-9001", amount="330.00")
    assert r["amount"] == "330.00" and r["stay_closed"] is True


# --- One remedy per stay ---


async def test_refund_then_hold_is_refused(small_client):
    await call(small_client, REFUND, ticket_id="LIS-TKT-9001", amount="330.00")
    with pytest.raises(ToolError, match="one remedy per stay"):
        await small_client.call_tool(HOLD, {"ticket_id": "LIS-TKT-9001", "listing_id": "LST-100907"})


async def test_hold_then_refund_and_second_hold_are_refused(small_client):
    await call(small_client, HOLD, ticket_id="LIS-TKT-9001", listing_id="LST-100907")
    with pytest.raises(ToolError, match="One remedy per stay"):
        await small_client.call_tool(REFUND, {"ticket_id": "LIS-TKT-9001", "amount": "330.00"})
    with pytest.raises(ToolError, match="One remedy per stay"):
        await small_client.call_tool(HOLD, {"ticket_id": "LIS-TKT-9001", "listing_id": "LST-100901"})


# --- Safety hand-off ---


async def test_after_handoff_no_money_booking_or_host_contact(small_client):
    r = await call(
        small_client,
        "handoff_to_safety_agent",
        ticket_id="LIS-TKT-9004",
        conditions=["threat_or_violence", "stated_fear_of_person"],
        summary="Guest asked for a refund and describes being followed by a stranger.",
    )
    assert r["status"] == "handed_off"
    for tool, args in [
        (REFUND, {"amount": "330.00"}),
        (HOLD, {"listing_id": "LST-100901"}),
        ("search_open_listings", {}),
        ("message_host", {"message": "hello"}),
    ]:
        with pytest.raises(ToolError, match="live safety agent"):
            await small_client.call_tool(tool, {"ticket_id": "LIS-TKT-9004", **args})


async def test_handoff_needs_a_known_condition(small_client):
    with pytest.raises(ToolError):
        await small_client.call_tool(
            "handoff_to_safety_agent", {"ticket_id": "LIS-TKT-9004", "conditions": [], "summary": "x"}
        )
    with pytest.raises(ToolError):
        await small_client.call_tool(
            "handoff_to_safety_agent", {"ticket_id": "LIS-TKT-9004", "conditions": ["angry_guest"], "summary": "x"}
        )


# --- Specialist tool allocation (spec FR-022 to FR-025) ---


def test_specialists_cover_only_the_six_tools():
    assert set().union(*SPECIALIST_TOOLS.values()) == ALL_TOOLS
    assert set(SPECIALIST_TOOLS) == {"safety", "rebooking", "refund"}


def test_safety_specialist_cannot_refund_or_hold():
    assert SPECIALIST_TOOLS["safety"] == {"lookup_reservation", "handoff_to_safety_agent"}


def test_message_host_only_in_rebooking():
    assert [s for s, tools in SPECIALIST_TOOLS.items() if "message_host" in tools] == ["rebooking"]


def test_no_specialist_has_both_remedies():
    assert all(not {HOLD, REFUND} <= tools for tools in SPECIALIST_TOOLS.values())


def test_every_specialist_can_hand_off():
    assert all("handoff_to_safety_agent" in tools for tools in SPECIALIST_TOOLS.values())
