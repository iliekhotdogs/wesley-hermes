# lib-memory-format

**Audience:** lib (and main when proposing memory entries for lib to store)

**Purpose:** Define a token-efficient, Karpathy-flavored format for how lib stores durable memories. This is the canonical format; all memory entries lib writes should follow it.

---

## Design goals

1. **Karpathy-flavored:** atomic self-contained notes, first-principles layering, sparse linking, context over raw fact.
2. **Token-efficient:** extra structure only on entries that deserve it; facts stay cheap.
3. **Queryable without a graph:** topic-based grouping + layer filter replaces explicit back-link maintenance.

---

## Entry structure

Every memory entry is a single content string with this shape:

```
[topic: <topic-slug>] [layer: principle|fact|heuristic|lesson] <short title>
<1-3 sentence body>
[links: <topic-slug>, <topic-slug>]   ← optional, only genuine cross-topic relationships
[source: <where this came from>]       ← optional, only when useful for verification or user correction
```

### Field rules

| Field | Required | Notes |
|-------|----------|-------|
| `topic` | Yes | Short slug, lowercase-hyphenated. Same topic across entries = implicit relationship. |
| `layer` | Yes | One of `principle`, `fact`, `heuristic`, `lesson`. Controls how much context to store. |
| `title` | Yes | Short, descriptive, sentence-case. |
| `body` | Yes | See layer guidelines below. |
| `links` | No | Only when the relationship is genuinely useful at retrieval time. Not for every entry. |
| `source` | No | Only for contested facts, user-correctable claims, or entries where provenance matters. |

### Topic slugs

- Lowercase, hyphenated, no spaces.
- General enough to be reused, specific enough to be meaningful.
- Examples: `memory-routing`, `discord-delivery`, `toolset-config`, `kanban-workflow`, `user-style`, `calibration-failure`
- When in doubt, pick the broader topic; create a new slug only when the topic is genuinely distinct.

---

## Layer guidelines

### `principle` — spend tokens here

What something fundamentally is or how it works. Stable, revisited often, worth re-deriving from.

- Body: 2-3 sentences. What it is + why it works that way + any key constraint.
- Store once per concept. Other entries reference the topic; they don't duplicate the principle text.
- Example:
  ```
  [topic: memory-routing] [layer: principle] How durable memory routing works
  main decides what merits remembering; lib decides placement/form and alone writes MEMORY.md, USER.md,
  and the second brain across sessions. main never writes these files directly. Memory/log/storage
  requests route through lib. The split exists so durable user-state stays in one authoritative writer.
  ```

### `fact` — keep cheap

An established datum. No derivation needed; link back to a principle topic if one exists.

- Body: 1 sentence, ideally shorter. What happened / what is true.
- If a principle topic exists for this area, mention it in `links:` or in the body as a phrase — don't re-explain.
- Example:
  ```
  [topic: memory-routing] [layer: fact] Routing preference stored in lib's MEMORY.md
  Stored at C:/Users/wesle/AppData/Local/hermes/profiles/lib/memories/MEMORY.md, line 7.
  Confirmed on disk 2026-09-26. Links: memory-routing.
  ```

### `heuristic` — rule of thumb with context

A practical rule that usually holds but has boundaries.

- Body: the rule + the main caveat/boundary in the same sentence or two.
- Don't store a heuristic without its failure mode or scope.
- Example:
  ```
  [topic: toolset-config] [layer: heuristic] Hermes toolsets take effect on /reset
  After enabling a toolset via CLI, a fresh session is the cleanest confirmation path. Same-session
  enablement may not be visible until reset. Caveat: emergency re-enables can sometimes be polled, but
  don't rely on it.
  ```

### `lesson` — what failed or succeeded, and why

A learning from a specific event. The value is in the *why*, not just the conclusion.

- Body: what happened + why it happened + what to do differently. 2-3 sentences.
- Prefer storing the failure mode over the generic "don't do X."
- Example:
  ```
  [topic: memory-routing] [layer: lesson] Don't route memory writes through main
  Attempting to write lib's MEMORY.md from main's session silently failed — main lacks write access to
  lib's memory files. No error was surfaced; the write just didn't land. Correct path: main proposes the
  content, lib writes it. Cost of getting this wrong: silent no-op, not a visible error.
  ```

---

## Linking discipline

- **Topic tags are the primary link mechanism.** Two entries sharing `topic: memory-routing` are implicitly related. No explicit link needed for same-topic entries.
- **`links:` is for cross-topic relationships only.** Use it when an entry genuinely depends on or relates to a different topic area.
- **Be sparse.** If you're unsure whether a link helps retrieval, leave it out. Over-linking creates noise.
- **Don't maintain a graph.** There are no entry IDs to link by. Links are topic-to-topic, not entry-to-entry.

---

## Source discipline

- Include `[source: ...]` when the entry records something the user said, a specific event, or a claim that could be wrong and should be verifiable.
- Skip it for obvious facts, self-evident procedural notes, or entries where provenance adds no value.
- Format: be specific but brief. E.g. `source: user via Discord thread 1553541148813951027 (2026-09-26)`.

---

## Token budget checklist

Before writing an entry, mentally check:

- [ ] Is this a `principle` or `lesson`? If yes, the extra sentences are justified.
- [ ] Is this a `fact` or `heuristic`? Keep the body to 1-2 sentences.
- [ ] Am I re-explaining a principle that already exists under this topic? If yes, drop it and link instead.
- [ ] Do I need `links:`? Only if it's a cross-topic relationship. Same-topic = no link needed.
- [ ] Do I need `source:`? Only if provenance matters for this entry.

---

## Migration note

When lib adopts this format, existing flat entries don't need to be rewritten all at once. New entries follow the format; old entries are gradually replaced or augmented as topics come up again. Don't do a bulk rewrite — it wastes tokens and the old entries may still be accurate.

---

## Summary of improvements over the flat store

| Aspect | Before | After |
|--------|--------|-------|
| Structure | Free-text, no fields | Topic + layer + body + optional links/source |
| First-principles layering | None — all entries look the same | `principle` entries are explicitly distinguished and can be elaborated without duplication |
| Linking | None | Topic-based grouping (implicit) + sparse explicit cross-topic links |
| Retrieval | Linear dump of everything | Query by topic + layer; principles surface first |
| Token usage | Uniform per entry | Cheap for facts/heuristics, richer only for principles/lessons where it pays off |
| Context | What, rarely why | Why stored for principles and lessons; facts reference principles instead of re-explaining |
| Maintenance | None needed (but also none available) | No graph to maintain; topic tags are self-maintaining |

**Net effect:** same or lower token cost for typical fact entries, meaningfully better retrieval and reasoning support for the entries that matter most.
