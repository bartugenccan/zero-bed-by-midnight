# Feature Specification: Stranded Guest Resolution (Lisbon Check-In Incident)

**Feature Branch**: `main` (spec kept on the default branch)

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "A multi-agent system that works through the 60 tickets from guests who could not check in to their Lisbon stay on 16 November 2026, and applies the AirCover Rebooking and Refund Rules so that every guest has a bed, a refund or a live safety agent before midnight."

## Context

On 16 November 2026, 60 guests could not check in to their Lisbon stays. Each one opened a support ticket. Policy and Payments issued a ruling, the **AirCover Rebooking and Refund Rules**, on what AirCover owes these guests. This spec restates that ruling as requirements and adds the triage decisions made while reviewing the tickets.

**Incident commitment**: every guest has a bed, a refund or a live safety agent before midnight on 16 November 2026.

Each ticket ends in exactly one of three outcomes:

| Outcome | Meaning |
|---|---|
| **Safety hand-off** | A live safety agent from Trust and Safety takes the case. No money or booking action happens first. |
| **Rebooking** | The guest is moved to a comparable open home for the whole remaining stay. |
| **Refund** | The guest gets money back, up to what they paid. The stay is closed. |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guests in danger reach a live safety agent first (Priority: P1)

A stranded guest describes a situation that makes them unsafe tonight: they are hurt or unwell, someone has threatened or followed them, they have nowhere safe to wait, they are under 18 and alone, or they are afraid of someone. The system hands the ticket to a live safety agent straight away, even if the guest only asked for money. It does not issue a refund or hold a booking first.

**Why this priority**: A wrong refund can be fixed later. A missed safety case cannot. This check runs before every other decision.

**Independent Test**: Run the triage step on all 60 tickets and check that exactly the tickets describing a safety condition are handed off, with no refund or hold on any of them before the hand-off.

**Acceptance Scenarios**:

1. **Given** a ticket where the guest asks only for a full refund but describes an injury, **When** the ticket is triaged, **Then** it is handed to a live safety agent and no refund is issued.
2. **Given** a ticket where the guest asks for a refund and describes being followed and watched by a stranger, **When** the ticket is triaged, **Then** it is handed to a live safety agent and no refund is issued.
3. **Given** a ticket where the guest asks only for a phone call but says they are 16, alone and their phone is almost dead, **When** the ticket is triaged, **Then** it is handed to a live safety agent.
4. **Given** a ticket where the guest is furious and uses dramatic language about how they feel but describes no injury, threat, minor or unsafe place, **When** the ticket is triaged, **Then** it is not handed off and continues to rebooking or refund.
5. **Given** a ticket where the guest asks for a phone call because they prefer to talk to a person, and describes no safety condition, **When** the ticket is triaged, **Then** it is not handed off and continues to rebooking or refund.

---

### User Story 2 - Guests who want a place to stay are moved to a comparable home (Priority: P2)

A qualifying guest who wants to keep their trip is offered an open Lisbon home that passes every comparable-home test, for the whole remaining stay. The home is held for them so no one else can take it.

**Why this priority**: Most guests (34 of 60) need a bed tonight. Rebooking is the remedy they asked for, and it uses the shared uplift budget, so it has to be done carefully.

**Independent Test**: For every rebooked ticket, check the chosen home against the five comparable-home tests and the uplift budget, using only the ticket and open-listings data.

**Acceptance Scenarios**:

1. **Given** a qualifying guest with an original nightly price of EUR 110.00, **When** the system looks for a home, **Then** a home at EUR 132.00 a night may be offered and a home at EUR 132.01 a night may not.
2. **Given** a home whose availability starts one day after the guest's check-in date, **When** the system checks it, **Then** it fails the dates test and is not offered.
3. **Given** a home that has just been held for another guest, **When** the system checks it for a second guest, **Then** it fails the "can be held now" test and is not offered.
4. **Given** two homes that both pass every test, one in the guest's neighbourhood and one across town, **When** the system chooses, **Then** it prefers the one in the same or a neighbouring neighbourhood.
5. **Given** a guest who turns down the first home offered, **When** they reply, **Then** they are offered another comparable home, or a full refund if they prefer.

---

### User Story 3 - Guests who want their money back get a correct refund (Priority: P3)

A qualifying guest who does not want another home, or for whom no comparable home exists, gets their money back. The refund never exceeds what they paid, and a refunded stay is not also rebooked.

**Why this priority**: These guests have already made other plans. They need a correct refund, not speed into a new booking. Mistakes here cost money but do not leave anyone without a bed.

**Independent Test**: For every refunded ticket, check that the amount is between EUR 0.01 and the ticket's total paid, and that no rebooking exists for the same nights.

**Acceptance Scenarios**:

1. **Given** a guest who declines rebooking and describes no safety condition, **When** the refund is issued, **Then** the amount is the full total paid.
2. **Given** a guest who booked with a promo code and asks to get back only the discounted amount they paid, **When** the refund is issued, **Then** the amount is the ticket's total paid and not the undiscounted price.
3. **Given** a guest who wants a home but no open listing passes every comparable-home test, **When** the search ends, **Then** the guest gets a full refund of total paid.
4. **Given** a guest who is upset and asks for extra compensation, **When** the refund is issued, **Then** the amount is still no more than total paid.

---

### Edge Cases

- **Money request with a safety condition**: the safety condition decides. The ticket is handed off, and the refund waits for the live safety agent.
- **Safety condition described without safety words**: the guest does not have to say "safety" or "emergency". The condition is read from what the guest describes.
- **Children travelling with adults**: a family with children is not an unaccompanied minor. Only a guest under 18 travelling or waiting without an adult counts.
- **Angry tone or hyperbole**: anger, swearing or dramatic exaggeration about how the guest feels are not a safety condition on their own. A real condition inside an angry message (for example, alone at night with a dead phone) still triggers a hand-off.
- **Request for a call**: asking to talk to a person is not a safety condition on its own. A call may be offered as normal service, but it does not delay or block the rebooking or refund.
- **Price exactly at the ceiling**: a home priced at exactly 1.20 × the original nightly price passes. One cent above fails.
- **Availability gap**: a home must be available for every night of the remaining stay with no gap.
- **Two guests competing for one home**: the first hold wins. The home is then `on_hold` and fails for the second guest.
- **Host replied, but before the guest's contact**: this still counts as host unreachable.
- **Host cancelled more than 30 days before check-in**: that condition does not apply, but the guest may still qualify through another condition.
- **Home above the 120% ceiling while budget remains**: it is still not offered on 16 November 2026, because the sign-off needed for it is not available that day.

## Requirements *(mandatory)*

### Functional Requirements

**Triage and safety**

- **FR-001**: The system MUST give every one of the 60 tickets exactly one outcome: safety hand-off, rebooking or refund.
- **FR-002**: The system MUST check every ticket for safety conditions before any rebooking or refund decision.
- **FR-003**: The system MUST read safety conditions from what the guest describes in their message, not from the type of request they selected, and not from keywords or emergency labels.
- **FR-004**: The system MUST treat a ticket as a safety ticket when the guest describes any one of these five conditions:

  | Condition | What the guest describes |
  |---|---|
  | Injury or medical need | Someone is hurt, unwell, pregnant, needs medication or needs a doctor |
  | Threat or violence | Someone has threatened, followed, shouted at or harmed them |
  | Nowhere safe to wait | Out on the street at night, phone dying, alone with luggage, nowhere to go |
  | Unaccompanied minor | A guest under 18 travelling or waiting without an adult |
  | Stated fear of a person | Afraid of the host, a neighbour, a stranger or someone in the party |

- **FR-005**: On a safety ticket, the only booking action the system MAY take before the hand-off is handing the case to a live safety agent (`handoff_to_safety_agent` in the policy). It MUST NOT issue a refund (`issue_refund`) or hold a booking (`hold_booking`) before the hand-off, even when the guest asks only for money.
- **FR-006**: After the hand-off, the system MUST leave every refund and booking decision on that ticket to the live safety agent.
- **FR-007**: The system MUST NOT treat anger, strong language or a request for a phone call as a safety condition on its own.

**Who qualifies**

- **FR-008**: A guest MUST qualify for support when any one of these is true:
  - No working access was provided at check-in (empty key box, wrong code, no one at the door).
  - The host is unreachable: there is no host reply, or the last host reply is not later than the guest's contact.
  - The host cancelled within 30 days before the check-in date.
- **FR-009**: Support MUST cover the whole remaining stay, from check-in date to check-out date, not only the first night.

**Rebooking**

- **FR-010**: The system MUST offer only homes that pass all five comparable-home tests:

  | Test | Rule |
  |---|---|
  | Dates covered | Available from on or before check-in, and available to on or after check-out, with no gap |
  | Fits the party | Maximum guests is at least the party size |
  | Enough bedrooms | Bedrooms are at least the original listing's bedrooms |
  | Can be held now | Status is `available` at the moment of the hold; `on_hold` and `booked` fail |
  | Price ceiling | Nightly price is at most 1.20 × the original nightly price (EUR 110.00 gives a ceiling of EUR 132.00) |

- **FR-010a**: A qualifying guest who has not asked for a refund (including guests who asked for a call or made another kind of request) MUST be offered rebooking first. They get a refund only if they decline rebooking or no home passes the comparable-home tests.
- **FR-011**: Among homes that pass, the system SHOULD prefer the same or a neighbouring Lisbon neighbourhood. Neighbourhood MUST NOT be used as a pass or fail test.
- **FR-012**: A rebooking MUST name a home from the open Lisbon listings (IDs LST-100001 to LST-100450). The guest's original listing (LST-200001 to LST-200060) MUST NOT be used.
- **FR-013**: The system MUST NOT offer a home priced above the 120% ceiling on 16 November 2026, even if budget remains.
- **FR-014**: A guest MAY decline an offered home. Declining MUST NOT end their right to another comparable home or to a full refund.

**Refunds**

- **FR-015**: The system MUST refund the full total paid when no open listing passes the comparable-home tests, or when the guest declines rebooking.
- **FR-016**: A refund MUST NOT exceed the ticket's total paid. Goodwill or "inconvenience" additions above total paid MUST NOT be issued. Any amount from EUR 0.01 up to total paid is within policy.
- **FR-017**: A refund MUST close the stay. A guest who is rebooked MUST NOT also receive a refund for the same nights.

**Uplift budget**

- **FR-018**: The system MUST track uplift for each rebooking: (new nightly price − original nightly price) × nights booked, counted only when the new price is higher.
- **FR-019**: Total uplift across all 60 tickets MUST NOT exceed EUR 9,000. The EUR 150 average per rebooked guest is a planning figure, not a per-guest cap.

**Commitment and record**

- **FR-020**: Every ticket MUST reach its outcome before midnight on 16 November 2026, Lisbon time.
- **FR-021**: For every ticket, the system MUST record the outcome and the reason for it (the safety condition found, the qualifying condition, the home chosen and the tests it passed, or the refund amount and why).

### Key Entities *(include if feature involves data)*

- **Ticket**: one stranded guest's reservation and request. Holds the guest's message, party size, original bedrooms, check-in and check-out dates, original nightly price, total paid, host cancellation and last-reply times, and the request type the guest selected.
- **Open listing**: a Lisbon home that may be offered. Holds its neighbourhood, bedrooms, maximum guests, availability window, nightly price and status (`available`, `on_hold`, `booked`).
- **Outcome**: the single result for a ticket: safety hand-off, rebooking (with the chosen listing and uplift) or refund (with the amount), plus the recorded reason.
- **Uplift budget**: the EUR 9,000 incident budget that rebooking uplift is drawn from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 60 of 60 tickets have exactly one outcome before midnight on 16 November 2026.
- **SC-002**: 6 of 6 tickets describing a safety condition are handed to a live safety agent, including the 2 where the guest asked only for a refund.
- **SC-003**: 0 refunds and 0 booking holds happen on a safety ticket before its hand-off.
- **SC-004**: 0 tickets are handed off because of anger or a call request alone.
- **SC-005**: 100% of rebookings pass all five comparable-home tests, and 0 are priced above 120% of the original nightly price.
- **SC-006**: 0 refunds exceed total paid, and 0 stays receive both a refund and a rebooking.
- **SC-007**: Total uplift across all rebookings is EUR 9,000 or less.
- **SC-008**: The triage category of every ticket matches the reviewed answer key for all 60 tickets (34 rebooking, 20 refund, 6 safety hand-off). A ticket triaged for rebooking may still end as a full refund under FR-015 if no comparable home passes.

## Assumptions

- **Data**: the ticket export (60 tickets) and the open-listings export (450 homes) are inputs supplied at run time. They contain guest details and are not stored in this public repository.
- **Answer key**: the reviewed outcome on each ticket is used only to check results. It is never an input to a decision.
- **Time zone**: all dates and "midnight" are Lisbon local time (UTC+0 in November).
- **Budget exhaustion**: the policy does not say what happens if a valid rebooking would push total uplift above EUR 9,000. This spec treats EUR 9,000 as a hard limit and sends such a case to a person instead of deciding for the guest.
- **Non-qualifying ticket**: the policy does not say what to do with a ticket that meets no qualifying condition. This spec sends such a ticket to a person instead of paying or rebooking it automatically.
- **Calls**: a guest who asks for a call may be called as normal service. The call does not change their outcome or hold up a rebooking or refund.
- **Scope**: this spec covers what the system must decide and why. How the work is split between agents, and which tools they use, belongs in the implementation plan.
