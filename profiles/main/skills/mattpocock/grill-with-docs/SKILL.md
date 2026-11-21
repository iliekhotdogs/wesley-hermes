---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
disable-model-invocation: true
---

> **Hermes compatibility (local integration):** “Skill tool” means `skill_view(name)`; load named sibling skills with that tool. Read relative support files from this skill's directory using `read_file` or `skill_view`—do not assume Claude/Codex plugin paths exist. Use Hermes file/search/edit tools instead of raw shell equivalents. Sub-agent/background-agent requests follow the installed specialist routing and isolation rules; they do not authorize generic delegation. Use the active profile's scratch directory (`TMPDIR`) for temporary output. Upstream `disable-model-invocation` is not relied upon as a Hermes enforcement control. Installing this skill does not run its procedure or authorize tracker posts, repo configuration, infrastructure changes, or credential access; those stay within the current user's requested task and host security policy. Never collect passwords, card details, or verification codes in chat or tool logs. Supporting shell files are templates, not install hooks; inspect and tailor them before any user-authorized run.


Call the Skill tool twice, for "grilling" and "domain-modeling".
