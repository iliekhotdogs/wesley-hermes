# Designing data-driven maps and interactive 3D scenes

Use for scientific dashboards, digital twins, terrain viewers and scenario comparisons. This is a design workflow, not a validated simulation method.

## 1. Establish the decision and evidence

1. Ask what the user must understand or choose after the first short interaction. Distinguish geographic exploration, scenario comparison and cinematic storytelling; select one primary journey before picking effects.
2. Recover the actual source plan, preserving document-tab boundaries. Compare requirements across documents and repository plans; list conflicting renderer choices, site assumptions and scope rather than silently merging drafts.
3. Inspect a pinned repository tree before treating paths named in a PRD as existing code. Read the relevant files when present. Distinguish planned, implemented and exercised capabilities; a scaffold claim is not runtime evidence. Ask about other branches or local assets when the snapshot does not contain claimed implementation.
4. Clarify whether “3D model” means a website scene, a reusable modeled asset, or both. Ask for team strengths, target demo hardware, offline requirements and the backend's earliest deliverable. Reuse existing working assets when they materially reduce risk.

## 2. Choose one rendering approach

- Prefer a bounded local scene when the core task is selecting objects, inspecting overlays and comparing fixed scenarios.
- Prefer a geospatial viewer when regional exploration, terrain tiles and real-world location navigation are central, or demonstrated assets and team experience favor it.
- Choose one interactive renderer for the first deliverable; a locator image can provide regional context without a second live engine. Separate optional cinematic assets from the functioning analytical experience.
- Propose one prepared site before arbitrary-location ingestion. Add new sites only after one complete data-to-interface path works.

## 3. Compose the scene by responsibility

Separate terrain geometry, imagery/material, object or field boundaries, decorative instances, and analytical overlays. Use schematic decoration only where it improves understanding; hide it when it obscures analysis. An arbitrary photograph is not an elevation model or an automatically georeferenced texture.

Agree a shared fixture before parallel rendering/UI work: stable IDs, coordinate reference system, local origin, axes, elevation datum, units, raster orientation, pixel centres/corners, masks, timestamps and metadata. Consume backend calculations rather than inventing frontend physics. Confirm binary format definitions instead of implementing decoders from names alone.

Keep source resolution distinct from display mesh resolution. Label illustrative boundaries, assumed timing, modeled values and vertical exaggeration. A decorative slab is not a measured soil profile. Render missing data distinctly from valid zeroes. Do not show quantitative depth, flow direction, yield or savings unless the supplied outputs support those quantities.

## 4. Design the comparison before the spectacle

Hold camera, selected object, evaluation period, initial conditions and legend ranges constant across alternatives. Define the sign of difference overlays. Begin with one viewport plus an A/B toggle and a persistent comparison table; add synchronized split views after the basic comparison works. Separate seasonal or scenario time from animation playback time.

Show evidence, assumptions, trade-offs and missing evaluations alongside the scene. A result for one hazard does not establish an overall optimal decision. Include keyboard selection, a readable 2D/results equivalent and reduced-motion behavior.

## 5. Gate polish on real integration

Build in order: labeled fixture and readable controls → one real end-to-end result → 3D clarity and measured performance → optional replay and cinematic effects. Keep unsupported controls hidden or explicitly demonstrative. Package assets locally when offline delivery is required.

Test asymmetric geometry for axis/orientation errors, masked samples for false zeroes, display values against supplied results, A/B state synchronization, keyboard and WebGL fallback, and restart/reset with networking disabled. Benchmark on the intended machine and resolution; proposed frame-rate goals are not measurements. Report separately what was designed, built, visually inspected and actually tested.
