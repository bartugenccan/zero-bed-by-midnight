<!--
Sync Impact Report
- Version: template -> 1.0.0 (first ratified version)
- Principles added: I. Safety Before Money, II. Read What the Guest Describes,
  III. Never Pay More Than Was Paid, IV. Only Comparable Homes, V. Every Decision Is Explained
- Sections added: Data Handling, Development Workflow, Governance
- Templates: no changes needed (plan, spec and tasks templates read this file at runtime)
-->

# Zero Bed by Midnight Constitution

These principles apply to every agent, tool and change in this project. They come from the AirCover Rebooking and Refund Rules for the Lisbon check-in incident on 16 November 2026. The full requirements are in [specs/001-stranded-guest-resolution/spec.md](../../specs/001-stranded-guest-resolution/spec.md).

## Core Principles

### I. Safety Before Money (NON-NEGOTIABLE)

Every ticket is checked for the five safety conditions before anything else: injury or medical need, threat or violence, nowhere safe to wait, unaccompanied minor, and stated fear of a person. On a safety ticket, the only allowed booking action is `handoff_to_safety_agent`. `issue_refund` and `hold_booking` are forbidden before the hand-off, even when the guest asks only for money. After the hand-off, the live safety agent decides.

### II. Read What the Guest Describes

Outcomes come from what the guest describes in their message. The request type they selected, the words they use and their tone do not decide the outcome. A calm refund request can be a safety case. An angry message or a request for a call is not a safety case on its own.

### III. Never Pay More Than Was Paid

A refund is never more than the ticket's total paid, with no goodwill additions. One remedy per stay: a refunded stay is not also rebooked, and a rebooked stay is not also refunded. Total rebooking uplift stays within the EUR 9,000 incident budget.

### IV. Only Comparable Homes

A guest is only offered an open listing that passes all five tests: dates covered with no gap, fits the party, enough bedrooms, `available` at the moment of the hold, and priced at no more than 1.20 × the original nightly price. On 16 November 2026, nothing above that ceiling is offered.

### V. Every Decision Is Explained

Each ticket ends with exactly one outcome (safety hand-off, rebooking or refund) and a recorded reason. A case the policy does not cover goes to a person. It is not guessed.

## Data Handling

This repository is public. Guest data (the ticket export and the open-listings export) is supplied at run time and is never committed. Code, tests, logs and docs use ticket IDs, not guest names or verbatim guest messages.

## Development Workflow

- Specs, plans and tasks follow the Spec Kit flow: specify, plan, tasks, implement.
- Every principle above MUST have an automated check against the 60 incident tickets before a change is accepted.
- The reviewed outcome on each ticket is used only to check results, never as an input to a decision.

## Governance

This constitution overrides other project guidance. A change to a principle needs a written reason and a version bump: MAJOR for removing or redefining a principle, MINOR for adding one, PATCH for wording.

**Version**: 1.0.0 | **Ratified**: 2026-11-18 | **Last Amended**: 2026-11-18
