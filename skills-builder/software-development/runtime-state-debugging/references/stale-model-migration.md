# Stale Model-State Migration Pattern

## Reproduction

A Council UI can display obsolete models even when current defaults are correct if `status.members` comes from an older three-seat run. Example stale response:

```json
{
  "members": [
    {"id":"strategist","model":"gpt-5.6-luna"},
    {"id":"analyst","model":"gpt-5.6-terra"},
    {"id":"risk-critic","model":"gpt-5.6-sol"}
  ]
}
```

## Canonicalization

Normalize against the current configured seat list, rather than mapping only the returned members:

1. iterate configured seats in canonical order;
2. merge matching runtime status/metrics;
3. migrate known legacy defaults to the seat's current model;
4. preserve non-legacy explicit custom models;
5. add omitted seats with queued/empty metrics;
6. keep approval and external-action safety fields explicit.

For the five-seat Council used in the originating case:

```text
strategist       nvidia/nemotron-3-ultra-550b-a55b:free
analyst          qwen/qwen3.8-flash
risk-critic      google/gemma-4-31b-it:free
cross-member     minimax/minimax-m3:free
final-judge      gpt-5.6-sol
```

## Verification

Test both the stale fixture and a custom override. Then run the client tests, backend tests, production build, and inspect the actual served process. A source search alone is insufficient when the symptom is runtime state.
