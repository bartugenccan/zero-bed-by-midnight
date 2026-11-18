# Zero Bed by Midnight

A multi-agent system for the Lisbon check-in incident on 16 November 2026. Sixty guests could not check in to their stays. The system works through their tickets and applies the AirCover Rebooking and Refund Rules, so that every guest has **a bed, a refund or a live safety agent before midnight**.

A Learning with Zero project.

## Start here

| Document | What it covers |
|---|---|
| [Feature spec](specs/001-stranded-guest-resolution/spec.md) | The full rules as requirements: who qualifies, comparable homes, refunds, the uplift budget and safety hand-off |
| [Constitution](.specify/memory/constitution.md) | The five non-negotiable principles every agent follows |
| [Spec quality checklist](specs/001-stranded-guest-resolution/checklists/requirements.md) | Validation of the spec before planning |

## The rules in short

- **Safety first.** If a guest describes an injury or medical need, a threat, nowhere safe to wait, being under 18 and alone, or fear of someone, the ticket goes to a live safety agent. The only allowed action is `handoff_to_safety_agent`. No `issue_refund` or `hold_booking` before the hand-off, even if the guest asked only for money.
- **What the guest describes decides, not their tone.** Anger or a request for a call is not a safety case on its own.
- **Rebooking** covers the whole remaining stay, in a home that passes all five tests: dates, party size, bedrooms, `available` status, and at most 120% of the original nightly price.
- **Refunds** never exceed what the guest paid. One remedy per stay.
- **Uplift budget**: EUR 9,000 across all 60 tickets.

## Status

Spec and constitution are written. The FastMCP tool server is built and tested. The supervisor and the three specialist agents are next.

## Tool server

A [FastMCP](https://gofastmcp.com) server ([src/zero_bed_by_midnight/server.py](src/zero_bed_by_midnight/server.py)) exposes six typed tools over the exports. Each tool's description is written in the words of the rules.

| Tool | Does | Used by |
|---|---|---|
| `lookup_reservation` | Reads a ticket's reservation (never the answer key) | safety, rebooking, refund |
| `search_open_listings` | Returns only export listings that pass all five comparable-home tests | rebooking |
| `hold_booking` | Holds a comparable home; enforces the tests, the budget and one remedy per stay | rebooking |
| `issue_refund` | Refunds EUR 0.01 up to `total_paid`; closes the stay | refund |
| `message_host` | Messages the original host (simulated: recorded, not delivered) | rebooking |
| `handoff_to_safety_agent` | Hands the case to a live safety agent; blocks refunds and holds after it | safety, rebooking, refund |

### Printed tool list

Output of `uv run python -m zero_bed_by_midnight.list_tools`, the descriptions agents see:

- **`lookup_reservation(ticket_id)`**: Look up a stranded guest's reservation by ticket ID: dates, party size, original bedrooms, original nightly_price, total_paid, host cancellation and last-reply times, what the guest requested, and guest_message. Read the safety conditions from what the guest describes in guest_message, not from guest_requested. Also returns price_ceiling (1.20 x the original nightly_price) and the case state.
- **`search_open_listings(ticket_id)`**: Search the open Lisbon listings export for comparable homes for this ticket's whole remaining stay (check_in_date to check_out_date). Returns only listings that pass every test: dates covered with no gap (available_from <= check_in_date and available_to >= check_out_date), fits the party (max_guests >= party_size), enough bedrooms (bedrooms >= original bedrooms), can be held now (status = available), and price ceiling (nightly_price <= 1.20 x original nightly_price). Same neighbourhood is listed first as a preference, not a test. Every listing_id returned comes from the export (LST-100001 to LST-100450). An empty list means no comparable home: the guest is due a full refund of total_paid.
- **`hold_booking(ticket_id, listing_id)`**: Hold a comparable home for the guest's whole remaining stay once they accept it. The listing_id must come from the open listings export (LST-100001 to LST-100450), never the original listing. The home must pass every comparable-home test at the time of the hold, including status = available; on_hold and booked fail. Uplift ((nightly_price - original nightly_price) x nights) is drawn from the EUR 9,000 incident budget; a hold that would exceed it is refused and goes to a person. One remedy per stay: refused if the stay was refunded or already has a hold. Forbidden on a safety ticket before handoff_to_safety_agent, and refused after it.
- **`issue_refund(ticket_id, amount)`**: Forbidden on a safety ticket before handoff_to_safety_agent, and refused after it, even when the guest asks only for money. Refund a guest who declines rebooking or for whom no open listing passes the comparable-home test (then the full total_paid is due). The refund never exceeds the ticket's total_paid: no goodwill or inconvenience additions. Any amount from EUR 0.01 up to total_paid is within policy. A refund closes the stay and is not combined with a rebooking for the same nights.
- **`message_host(ticket_id, message)`**: Message the host of the guest's original listing, for example to check whether working access can still be provided. A host is unreachable when host_last_reply_at is empty or not after the guest's contact. Simulated in this build: the message is recorded, not delivered. Not for safety tickets: after hand-off the live safety agent decides any contact.
- **`handoff_to_safety_agent(ticket_id, conditions, summary)`**: Hand the ticket to a live safety agent from Trust and Safety. Call this when the guest describes any one of the five safety conditions: injury_or_medical_need (someone is hurt, unwell, pregnant, needs medication or a doctor), threat_or_violence (someone has threatened, followed, shouted at or harmed them), nowhere_safe_to_wait (out on the street at night, phone dying, alone with luggage, nowhere to go), unaccompanied_minor (a guest under 18 travelling or waiting without an adult), stated_fear_of_person (afraid of the host, a neighbour, a stranger or someone in the party). This applies even when the guest asks only for a refund; the guest does not need to say 'safety'. On a safety ticket this is the only allowed booking tool call. After hand-off the live safety agent decides any refund or booking.

The specialist allocation lives in [src/zero_bed_by_midnight/permissions.py](src/zero_bed_by_midnight/permissions.py). All three specialists must share one server instance, because holds, refunds, hand-offs and the uplift budget are kept in that instance's memory. The export files are only read, never written.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
uv sync
uv run zero-bed-by-midnight   # runs the MCP server over stdio
uv run pytest                 # runs the tests
```

The ticket and open-listings exports contain guest details, so they are not in this repository. Put them in the project root, or point `ZBM_TICKETS_CSV` and `ZBM_LISTINGS_CSV` at them. Without them, the tests still run on the synthetic fixtures in `tests/fixtures/`, and the tests on the real 60 tickets are skipped.

## Spec Kit workflow

This project uses [GitHub Spec Kit](https://github.com/github/spec-kit). With Claude Code:

1. `/speckit-constitution`: project principles (done)
2. `/speckit-specify`: feature spec (done)
3. `/speckit-plan`: implementation plan
4. `/speckit-tasks`: task list
5. `/speckit-implement`: build
