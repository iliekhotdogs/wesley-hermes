# Cross-Layer Council Checklist

## Contract

- [ ] Five configured seats exist in the UI and service defaults.
- [ ] Role IDs are stable and safe: `strategist`, `analyst`, `risk-critic`, `cross-member-critic`, `final-judge`.
- [ ] Models are exact and literal:
  - Strategist: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - Analyst: `qwen/qwen3.8-flash`
  - Risk critic: `google/gemma-4-31b-it:free`
  - Cross-member critic: `minimax/minimax-m3:free`
  - Final judge: `gpt-5.6-sol`
- [ ] Partial overrides merge onto all five seats.
- [ ] Explicit model and instruction overrides survive normalization.
- [ ] `approvalRequired` is true and `externalActions` is empty.

## Execution seams

- [ ] UI request builder.
- [ ] API/RPC adapter.
- [ ] Gateway/service normalization.
- [ ] Member executor calls.
- [ ] Cross-member critique executor call.
- [ ] Final judge executor call.
- [ ] Discord/platform ingress and progress updates.
- [ ] Status/audit snapshots.

## Evidence

| Layer | Evidence to capture |
|---|---|
| UI | Source/served heading and model controls |
| Request | Serialized member IDs/models |
| Service | Normalized five-seat snapshot |
| Executor | Stage, role, model, instruction arguments |
| Platform | Route test and non-route regression |
| Tests | Focused red/green plus full relevant suites |
| Build | Production build output |

Historical caches, audit artifacts, and transcripts are not runtime config
unless the application explicitly reads them.
