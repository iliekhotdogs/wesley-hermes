---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

> **Hermes compatibility (local integration):** “Skill tool” means `skill_view(name)`; load named sibling skills with that tool. Read relative support files from this skill's directory using `read_file` or `skill_view`—do not assume Claude/Codex plugin paths exist. Use Hermes file/search/edit tools instead of raw shell equivalents. Sub-agent/background-agent requests follow the installed specialist routing and isolation rules; they do not authorize generic delegation. Use the active profile's scratch directory (`TMPDIR`) for temporary output. Upstream `disable-model-invocation` is not relied upon as a Hermes enforcement control. Installing this skill does not run its procedure or authorize tracker posts, repo configuration, infrastructure changes, or credential access; those stay within the current user's requested task and host security policy. Never collect passwords, card details, or verification codes in chat or tool logs. Supporting shell files are templates, not install hooks; inspect and tailor them before any user-authorized run.


Spin up a **background agent** to do the research, so you keep working while it reads. Start it with a fresh context window.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.
