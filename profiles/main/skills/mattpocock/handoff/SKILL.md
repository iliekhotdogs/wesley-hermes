---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

> **Hermes compatibility (local integration):** “Skill tool” means `skill_view(name)`; load named sibling skills with that tool. Read relative support files from this skill's directory using `read_file` or `skill_view`—do not assume Claude/Codex plugin paths exist. Use Hermes file/search/edit tools instead of raw shell equivalents. Sub-agent/background-agent requests follow the installed specialist routing and isolation rules; they do not authorize generic delegation. Use the active profile's scratch directory (`TMPDIR`) for temporary output. Upstream `disable-model-invocation` is not relied upon as a Hermes enforcement control. Installing this skill does not run its procedure or authorize tracker posts, repo configuration, infrastructure changes, or credential access; those stay within the current user's requested task and host security policy. Never collect passwords, card details, or verification codes in chat or tool logs. Supporting shell files are templates, not install hooks; inspect and tailor them before any user-authorized run.


Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows) - not the current workspace.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
