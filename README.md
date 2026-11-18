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
