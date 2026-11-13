---
name: travel-planning
description: Use when comparing group trips, flights, and hotels.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [travel, flights, hotels, group-travel]
    related_skills: [grounded-citations]
---

# Travel planning and price comparison

## When to Use

Use for destination shortlists, live flight or lodging comparisons, and group-trip budgets. Distinguish inspiration from date-specific bookable prices.

## Workflow

1. Establish departure airport, travel dates/flexibility, traveler count and ages, room configuration/occupancy, destination preferences, and currency. Ask only for missing facts that change the search. For a flexible return date, search each candidate date rather than assuming one is better.
2. Translate “value” into **whole-group trip cost and usable vacation time**, not the cheapest advertised fare. When the traveler asks for name-brand flights, prioritize established carriers and show low-cost alternatives only if relevant and clearly labeled.
3. Search live round-trip itineraries with the exact passenger count. Record airline/operator, stop count, local times (both directions when available), fare type, baggage and seat-selection terms, taxes, currency, retrieval time, and direct search/booking URL. Confirm the quote at selection/checkout where possible; a search-result fare is not a guaranteed bookable price.
4. Search lodging for the same dates and **the full party**. Price the requested number of rooms or a suite explicitly permitted to sleep the whole group; never multiply a one-room/two-guest teaser rate without checking occupancy, inventory, taxes, fees, and cancellation terms. Compare different stay lengths when return dates differ.
5. Calculate the flight-plus-lodging total for the group, then assess convenience, holiday suitability, transfers, late arrivals, and whether an extra night is worth its cost. Use tools for all arithmetic and current facts. Rank only destinations with comparable verified totals; otherwise label a flight-only ranking and state which lodging or return-date comparisons remain unverified.
6. Present 2–4 concise options with total and per-person figures where verified, exact dates, links, important exclusions, and a recommendation conditioned on the traveler’s priorities. If live booking sites block a quote, give verified partial findings and a direct search link without inventing hotel prices or calling an incomplete comparison the best overall value.

## Efficiency pitfalls

- Bound exploratory research early: check a few promising destinations and narrow to the best evidenced options; prolonged searching without a usable hotel quote delays the user's decision.
- Treat search-engine snippets with generic nightly prices as leads, not date-specific group quotes; their dates, occupancy, and currency may differ.
- Validate copied deep links and fare details before sending them; long encoded travel URLs are easy to corrupt, and localized pages can display a different currency from the original search.
