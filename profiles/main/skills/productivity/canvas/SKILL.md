---
name: canvas
description: Fetch Canvas LMS courses and assignments via API token.
version: 1.0.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [CANVAS_API_TOKEN, CANVAS_BASE_URL]
metadata:
  hermes:
    tags: [Canvas, LMS, Education, Courses, Assignments]
---

# Canvas LMS — Course & Assignment Access

Read-only access to Canvas LMS for listing courses and assignments.

## Scripts

- `scripts/canvas_api.py` — Python CLI for Canvas API calls

## Setup

1. Log in to your Canvas instance in a browser
2. Go to **Account → Settings** (click your profile icon, then Settings)
3. Scroll to **Approved Integrations** and click **+ New Access Token**
4. Name the token (e.g., "Hermes Agent"), set an optional expiry, and click **Generate Token**
5. Copy the token and add to `${HERMES_HOME:-~/.hermes}/.env`:

```
CANVAS_API_TOKEN=your_token_here
CANVAS_BASE_URL=https://yourschool.instructure.com
```

The base URL is whatever appears in your browser when you're logged into Canvas (no trailing slash).

## Usage

In Hermes Discord gateway terminal sessions on this Windows host, use the
installed read-only wrapper (the absolute path also works if `canvas` is not
on `PATH`):

```bash
/c/Users/YOUR_USER/AppData/Local/hermes/bin/canvas due
/c/Users/YOUR_USER/AppData/Local/hermes/bin/canvas due --start 2026-09-21 --end 2026-09-27
```

`due` checks every active Canvas course and returns assignments in the date
range with local due times, links, submission state, and any course-level
warnings. With no dates it covers today through seven days later in
`America/Vancouver`. For “this week,” pass the local Monday and Sunday.
Always read `warnings`; a nonempty list means the answer may be incomplete.
Undated assignments and work hosted only in external systems are outside
this dated Canvas list.

When a previously due assignment disappears from a dated list, read its course's `list_assignments COURSE_ID` output and match the exact assignment ID before interpreting the delta. A moved due date can remove work from the rolling window; absence does not prove submission or deletion. Preserve the prior and current due times, and label submission state unknown if the course-level response omits it.

Other course-level commands are available through the same wrapper:

```bash
# List all active courses
/c/Users/YOUR_USER/AppData/Local/hermes/bin/canvas list_courses --enrollment-state active

# List all courses (any state)
/c/Users/YOUR_USER/AppData/Local/hermes/bin/canvas list_courses

# List assignments for a specific course
/c/Users/YOUR_USER/AppData/Local/hermes/bin/canvas list_assignments 12345

# List assignments ordered by due date
/c/Users/YOUR_USER/AppData/Local/hermes/bin/canvas list_assignments 12345 --order-by due_at
```

## Output Format

**list_courses** returns:
```json
[{"id": 12345, "name": "Intro to CS", "course_code": "CS101", "workflow_state": "available", "start_at": "...", "end_at": "..."}]
```

**list_assignments** returns:
```json
[{"id": 67890, "name": "Homework 1", "due_at": "2025-02-15T23:59:00Z", "points_possible": 100, "submission_types": ["online_upload"], "html_url": "...", "description": "...", "course_id": 12345}]
```

Note: Assignment descriptions are truncated to 500 characters. The `html_url` field links to the full assignment page in Canvas.

## API Reference (curl)

```bash
# List courses
curl -s -H "Authorization: Bearer $CANVAS_API_TOKEN" \
  "$CANVAS_BASE_URL/api/v1/courses?enrollment_state=active&per_page=10"

# List assignments for a course
curl -s -H "Authorization: Bearer $CANVAS_API_TOKEN" \
  "$CANVAS_BASE_URL/api/v1/courses/COURSE_ID/assignments?per_page=10&order_by=due_at"
```

Canvas uses `Link` headers for pagination. The Python script handles pagination automatically.

## Rules

- This skill is **read-only** — it only fetches data, never modifies courses or assignments
- On first use, verify auth by running `$CANVAS list_courses` — if it fails with 401, guide the user through setup
- Canvas rate-limits to ~700 requests per 10 minutes; check `X-Rate-Limit-Remaining` header if hitting limits

## Textbook research and recovery

- Match the actual Canvas course's term, section, and instructor before applying a public outline or bookstore listing. Different sections can require entirely different books.
- Treat file-list HTTP 403 as a file-inventory limitation, not proof that individual syllabus files or module metadata are inaccessible. An authorized main recovery may use existing profile-scoped credentials for read-only GETs of explicitly linked file metadata or course modules; never change credentials or bypass an actual access denial. Preserve successful evidence and do not repeatedly retry denied inventories.
- Inspect syllabus-body hyperlinks even when their visible text is empty (image buttons). Course documents can be linked only by an image.
- Prefer the newest matching-section syllabus in Course Administration modules over an older/mismatched syllabus landing-page attachment. Download through the file metadata's URL without logging signed URLs; extract PDF text and hyperlink annotations separately. If PyMuPDF is absent, use an already installed PDF extractor such as pdfplumber before installing another package.
- Separate required electronic texts from optional homework platforms. A bookstore's absence of arranged materials does not mean no textbook is required; an ebook redirect price of $0 does not mean free access.
- Cross-check publisher ISBN, edition, and year against the syllabus. Preserve discrepancies explicitly rather than silently replacing the syllabus citation or declaring a candidate purchase an exact match.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Unauthorized | Token invalid or expired — regenerate in Canvas Settings |
| 403 Forbidden | Token lacks permission for this course |
| Empty course list | Try `--enrollment-state active` or omit the flag to see all states |
| Wrong institution | Verify `CANVAS_BASE_URL` matches the URL in your browser |
| Timeout errors | Check network connectivity to your Canvas instance |
