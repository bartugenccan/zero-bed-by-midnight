"""Which of the six tools each specialist may call (spec FR-022 to FR-025).

The supervisor routes every ticket to one of these three specialists.
"""

from __future__ import annotations

ALL_TOOLS = frozenset(
    {
        "lookup_reservation",
        "search_open_listings",
        "hold_booking",
        "issue_refund",
        "message_host",
        "handoff_to_safety_agent",
    }
)

SPECIALIST_TOOLS: dict[str, frozenset[str]] = {
    "safety": frozenset({"lookup_reservation", "handoff_to_safety_agent"}),
    "rebooking": frozenset(
        {
            "lookup_reservation",
            "search_open_listings",
            "hold_booking",
            "message_host",
            "handoff_to_safety_agent",
        }
    ),
    "refund": frozenset({"lookup_reservation", "issue_refund", "handoff_to_safety_agent"}),
}
