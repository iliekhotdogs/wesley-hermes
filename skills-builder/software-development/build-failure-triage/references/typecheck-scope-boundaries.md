# Typecheck Scope Boundaries

## Compact reporting template

```text
Target repair:
- File:
- Root diagnostic:
- Minimal change:

Verification:
- Command:
- Exit status:
- Original diagnostic gone: yes/no

Remaining workspace failures:
- In target file:
- In unrelated files:
- Later stages skipped because:
```

## Parser-first example

If a compiler reports a malformed object literal such as a missing property colon, first repair that literal and any immediately adjacent properties using the same invalid `=` form. Then rerun the project's canonical typecheck. If the parser errors disappear but module-resolution and semantic errors remain, report the syntax repair as complete and the workspace check as failing; do not claim a green typecheck.

## Scope rule

A narrow syntax fix should not become an unrequested implementation of a larger, incomplete feature scaffold. Completing the scaffold is a separate task with its own acceptance criteria and test plan.
