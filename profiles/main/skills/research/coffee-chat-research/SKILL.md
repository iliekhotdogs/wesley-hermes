---
name: coffee-chat-research
description: Use when preparing a sourced brief for a coffee chat.
version: 0.1.0
author: the owner, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Networking, Coffee Chats]
    related_skills: [grounded-citations]
---

# Coffee Chat Research

Prepare a short, respectful professional briefing for a conversation with a named person. Public work-relevant information only; this is not a dossier or a way to find private contact information.

## When to Use

- A user supplies a name and asks for background before a coffee chat, informational interview, or networking conversation.
- Do not use for investigating personal life, home address, private contact channels, sensitive traits, or unrelated associates.

## Procedure

1. **Disambiguate.** Record the supplied name, employer, team, location, or other identifying clue as *user-provided*, not verified. Search with `web_search` using name and employer together, then employer site, public professional profiles, published articles and talks. Try name variants only if they are clearly relevant. If multiple plausible matches remain, ask for a public profile URL or another distinguishing clue rather than merging them.
2. **Establish identity and freshness.** Prefer a dated current employer biography or an accessible public profile directly linking the full name and employer. Record the retrieval date and any publication/profile-update date separately. A search snippet may establish only what its text literally says, not that the role is current; label it *indexed snippet, full profile inaccessible*. A similarly named person at another organization is not a match. Assign high confidence only for a current first-party page, medium for an accessible person-controlled public profile, and provisional for search snippets or older third-party directories.
3. **Gather relevant facts.** Use `web_extract` or accessible pages for role, location, career path, education/credentials, areas of work, public writing, and recent professional activity. Two independent sources are useful for a consequential or disputed claim. Do not infer a department from an employer's service line or a person's degree; say when unconfirmed. Never use data-broker pages, leaked data, private social accounts, or automated login bypass.
4. **Ground claims.** Load `grounded-citations`; register retrieved URLs with its ledger before writing, distinguish snippet-only evidence from opened pages, and cite each sourced claim in the final brief. Flag unsupported assertions and source conflicts explicitly. Do not fabricate details to fill a sparse profile.
5. **Write a conversation-ready brief.** Include: identity confidence and why; up to 3–6 professional highlights *only as evidence allows* with source/date and snippet-vs-opened-page status; 2–4 possible discussion angles tied to verified work or clearly labeled firm-wide context; 4–6 open-ended questions that do not presume unverified facts; source links; and gaps/limitations. Distinguish employer-authored market commentary from the person's own views or deals. Label discussion angles as suggestions, not facts about interests or preferences. Avoid gratuitous personal details and a private contact section.

## Pitfalls

- MNP or other broad firms may have many practice lines; a user-supplied 'finance department' label requires direct corroboration.
- Search snippets, directory copies and inaccessible LinkedIn profiles are not proof of current position or degree. Attribute them narrowly and prefer first-party pages.
- Recent activity must have a publication date or be described as undated; a retrieval date alone does not make a role or article recent. When refreshing a prior brief, explicitly state what changed, what remains uncorroborated, and whether no newer person-specific evidence was found.
- If no person-specific source survives identity checks, report the search gap and offer general firm-informed questions without pretending to know the person.

## Verification

Check that every named professional claim points to a retrievable source (or is explicitly labeled snippet-only/unverified), that the subject is not conflated with a namesake, and that all suggested questions avoid unsupported premises. Run the grounded-citations ledger verifier when drafting to a file. The brief is successful even when the honest finding is insufficient public evidence.
