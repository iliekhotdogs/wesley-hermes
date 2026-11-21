---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

> **Hermes compatibility (local integration):** “Skill tool” means `skill_view(name)`; load named sibling skills with that tool. Read relative support files from this skill's directory using `read_file` or `skill_view`—do not assume Claude/Codex plugin paths exist. Use Hermes file/search/edit tools instead of raw shell equivalents. Sub-agent/background-agent requests follow the installed specialist routing and isolation rules; they do not authorize generic delegation. Use the active profile's scratch directory (`TMPDIR`) for temporary output. Upstream `disable-model-invocation` is not relied upon as a Hermes enforcement control. Installing this skill does not run its procedure or authorize tracker posts, repo configuration, infrastructure changes, or credential access; those stay within the current user's requested task and host security policy. Never collect passwords, card details, or verification codes in chat or tool logs. Supporting shell files are templates, not install hooks; inspect and tailor them before any user-authorized run.


Implement the work described by the user in the spec or tickets.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Call the Skill tool with "tdd" where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, call the Skill tool with "code-review" to review the work.

Commit your work to the current branch.
