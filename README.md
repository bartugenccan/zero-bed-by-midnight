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

Spec and constitution are written. The implementation plan (agent design) is next.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14.

```bash
uv sync
uv run zero-bed-by-midnight
```

The ticket and open-listings exports contain guest details, so they are not in this repository. Supply them locally at run time.

## Spec Kit workflow

This project uses [GitHub Spec Kit](https://github.com/github/spec-kit). With Claude Code:

1. `/speckit-constitution`: project principles (done)
2. `/speckit-specify`: feature spec (done)
3. `/speckit-plan`: implementation plan
4. `/speckit-tasks`: task list
5. `/speckit-implement`: build
