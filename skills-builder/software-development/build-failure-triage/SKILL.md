---
name: build-failure-triage
description: "Use when a repository build, typecheck, or lint fails."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [builds, typecheck, lint, compiler-errors, debugging, verification]
---

# Build Failure Triage

## Purpose

Use this skill when a repository build, compiler, typecheck, lint, or check command fails. The goal is not merely to make one error disappear: it is to identify the first actionable root diagnostic, apply the narrowest correct change, and distinguish a repaired target from a still-failing workspace.

## Core Rules

- Run the repository's canonical check before editing whenever possible.
- Read the complete diagnostic output, including the first error and the files it names.
- Fix parser/syntax errors before semantic errors; parser failures often hide later diagnostics.
- Change one root cause at a time. Adjacent instances of the same malformed syntax in the same expression are part of one repair, not permission for an unrelated refactor.
- Re-run the same canonical command after the edit.
- Never report a repository check as passing when it exited nonzero.
- If uncommitted or newly added work introduces a larger scaffold of failures, preserve scope: report the target-file repair separately from the workspace-level failure unless the user explicitly asks to complete the scaffold.

## Workflow

### 1. Establish the failing loop

Identify the exact command used by the project (`npm run typecheck`, `npm run check`, `pnpm lint`, `cargo check`, etc.). Run it from the correct package/workspace directory and retain its exit status and diagnostics.

Prefer the canonical command over a hand-written substitute. A narrower command can supplement it for fast iteration, but cannot replace final verification.

### 2. Classify diagnostics

Group errors into:

1. **Parser/syntax** — missing punctuation, malformed object literals, invalid JSX, unterminated strings.
2. **Resolution** — missing modules, exports, path aliases, generated files, or dependencies.
3. **Semantic/type** — invalid types, implicit `any`, incompatible props, unreachable code.
4. **Integration/test** — runtime, fixture, environment, or cross-package failures.

Fix the earliest class that prevents later classes from being observed. After each repair, compare diagnostics by file and category rather than assuming all remaining errors are caused by the edit.

### 3. Inspect local patterns before editing

Read the target file and nearby working examples. Check the actual exports and dependency names instead of importing APIs from a different framework or an old scaffold. For TypeScript/React work, verify hook imports, component exports, icon package names, and path aliases against the current repository.

### 4. Make the minimum repair

For a syntax report, correct only the malformed syntax and directly adjacent copies of the same pattern. Do not silently implement unrelated missing UI primitives or redesign the feature while fixing a compiler blocker.

For a resolution or semantic error, expand scope only when the user requested a fully passing check or the missing dependency is clearly part of the same root cause.

### 5. Verify and report boundaries

Run the canonical check again. Report:

- The file and root cause repaired.
- The exact command run and exit status.
- Whether the original diagnostic disappeared.
- Remaining diagnostics, grouped by whether they are in scope or unrelated.
- Which later stages did not run because an earlier stage failed.

A statement such as “syntax fixed” is not equivalent to “typecheck passes.” Keep those claims separate.

## Common Pitfalls

- Stopping after the first parser error without rerunning the full check.
- Treating all newly exposed errors as regressions from the small fix.
- Completing an unrelated scaffold merely because it is included by the compiler.
- Saying “tests pass” when the check stopped before tests executed.
- Running the command from a sibling project or wrong workspace.
- Normalizing or guessing package names instead of inspecting current exports.

## Verification Checklist

- [ ] Canonical failing command captured.
- [ ] Target source and neighboring patterns inspected.
- [ ] Root diagnostic classified.
- [ ] Smallest correct change applied.
- [ ] Same canonical command rerun.
- [ ] Original error disappearance confirmed.
- [ ] Remaining failures classified by scope.
- [ ] Final report includes exit status and skipped stages.

See `references/typecheck-scope-boundaries.md` for a compact reporting template and parser-first triage example.
