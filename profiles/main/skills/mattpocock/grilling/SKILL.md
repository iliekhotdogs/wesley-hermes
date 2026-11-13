---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

> **Hermes compatibility (local integration):** “Skill tool” means `skill_view(name)`; load named sibling skills with that tool. Read relative support files from this skill's directory using `read_file` or `skill_view`—do not assume Claude/Codex plugin paths exist. Use Hermes file/search/edit tools instead of raw shell equivalents. Sub-agent/background-agent requests follow the installed specialist routing and isolation rules; they do not authorize generic delegation. Use the active profile's scratch directory (`TMPDIR`) for temporary output. Upstream `disable-model-invocation` is not relied upon as a Hermes enforcement control. Installing this skill does not run its procedure or authorize tracker posts, repo configuration, infrastructure changes, or credential access; those stay within the current user's requested task and host security policy. Never collect passwords, card details, or verification codes in chat or tool logs. Supporting shell files are templates, not install hooks; inspect and tailor them before any user-authorized run.


Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
