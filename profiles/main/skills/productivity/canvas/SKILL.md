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

## Semester-wide deadline and study plans

1. Confirm the user's intended LMS first; when they correct the source, switch to that system rather than combining unverified dates. List active courses, distinguish term courses from orientation shells, and retrieve the entire remaining-term `due` window. Check `courses_checked`, warnings, and the returned assignment count before treating it as complete.
2. Fetch `list_assignments COURSE_ID --per-page 100 --order-by due_at` for each term course to catch undated exams, presentations, and assignments. Keep exact Canvas links and convert UTC timestamps to the user's local timezone; distinguish due time from exam start time.
3. Read each course syllabus, schedule, and relevant module/calendar notices for in-class exams and work not represented as dated Canvas assignments. If the syllabus body links a PDF, retrieve its file metadata and download URL with authorized read-only API calls, then extract the PDF text. Cross-check against the institution's official final-exam timetable; match **course and section**, not just course code. State exact dates from authoritative records and label week-level or inferred dates as unconfirmed.
4. For a study guide, inventory the actual accessible lecture slides, notes, assignment instructions, practice tests, and module pages **course by course** before selecting study topics. Read their content, not just filenames; map each topic/section to its assessment and cite the source. The short `list_assignments` description is truncated, so fetch full authorized assignment details when scope matters. If a course file inventory returns 403, use individually linked files in authorized modules/syllabus; describe remaining coverage gaps rather than pretending to have read every slide. Extract PDF text with a local PDF reader and Office slide/document text from OOXML when available. Before fan-out, verify the target specialist actually has read and write tools for its staged workspace; Docker mounts alone do not grant model tool permissions. When delegating to isolated research workers, stage only task-relevant nonsecret source material in their authorized workspace, not credentials or profile homes; request one course-specific handoff per worker and synthesize only after checking all handoffs. If all workers block on the same capability, resolve that cause once or take over the existing cards rather than retrying them unchanged.
5. Ask for a realistic **total daily study capacity across all courses** and any unavailable days; use that shared budget, not the same hours separately for each subject. Build the plan through the latest identified assessment, or through the published examination period if a final date remains unknown. Present a complete confirmed deadline/exam checklist separately from unconfirmed/undated work, then one entry for **every local calendar day** with concrete material and practice/correction targets, submission buffers, and lighter recovery days. Programmatically check day coverage and dated-item inclusion. Flag external homework systems and unposted course work for rechecking; a suggestion to study an undated item must not masquerade as a deadline.
6. Treat Canvas submission status as a snapshot, not proof of future completion. Keep operational verification chatter separate from the requested student-facing plan; a script compile/data-staging check does not verify that the assessment inventory or study guide is complete.

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

## Prior-session recall and shared-slide access

- Before redoing assignment prep from scratch, run `session_search` (via `tool_search`/`tool_call` if not directly listed) with specific class/topic keywords (course code, chapter numbers, assignment name) rather than a vague term like "cheat sheet" — vague queries surface the most recent or most topically-similar unrelated session instead of the one the user means. If the first result doesn't match, inspect the other returned matches before asking the user to re-explain.
- The browser automation tool drives an isolated dedicated-profile browser, not the user's real logged-in Chrome, and is useless for any site requiring the user's own login (Canva, Google Docs, etc.) — don't suggest "I'll use your Chrome," since there is no access to it. Instead, ask the user to generate a public/share link or export (PDF/PNG) from the source app and send that.
- For Canva specifically: a `/design/.../edit` URL hits a login wall via both `web_extract` and the browser tool. A `canva.link/...` share link (Share → "Share this design" style short link) is viewable via `web_extract` without login and returns the slide text content directly — ask the user for that link format when they need slide content pulled.
- When building a fill-in-the-blank assignment template from a source presentation's structure, mirror the deck's actual section headings (e.g., Introduction/Analysis/Recommendation/Implementation/Appendix) rather than generic "Page 1/Page 2" labels — match the structure the user is expected to follow.
- `write_file` refuses to overwrite a file not freshly read in full this task (stale-write guard). If an edit is quick and the file is small, write to a new filename instead of re-reading+rewriting just to satisfy the guard.

## Locating and extracting large course textbooks

- A course textbook PDF may live outside Canvas, e.g. in a shared Google Drive inbox folder the user uploads materials to. Search that folder (`drive search "'<folder_id>' in parents" --raw-query`) by filename keywords (course title words, author) rather than assuming it's only on Canvas.

## Downloading a whole module's files ("prep me for this week", "download these and add to drive")

- Don't `source` the profile `.env` to read `CANVAS_API_TOKEN`/`CANVAS_BASE_URL` in bash — a UTF-8 BOM at the top of the file makes bash try to execute the BOM bytes as a command and fail. Instead extract values directly: `TOK=$(grep CANVAS_API_TOKEN .env | cut -d= -f2 | tr -d '\r')` (same pattern for BASE), then use `$TOK`/`$BASE` in curl calls.
- To bulk-download every file attached to one module (e.g. a "Week N" screenshot naming several PDFs): fetch `GET /courses/COURSE_ID/modules?per_page=100&include[]=items` once, find the module by name, collect each `File` item's `content_id`, then loop `GET /files/CONTENT_ID` for metadata and `curl -sL` each signed `url` into one destination folder named for the week/course. Don't fetch file metadata one-by-one through separate clarifying round-trips — batch the whole module's content_ids in one pass.
- When running Python one-liners from `terminal` (git-bash) on Windows, use `C:/Users/...`-style native paths inside the Python script, not `/c/Users/...` MSYS paths — the native Windows Python interpreter raises `FileNotFoundError` on MSYS-style paths even though bash itself resolves them fine. The same applies to the `curl -o <path>` output-file argument on this host: `curl` here is the native Windows binary, so `-o /c/Users/.../file.docx` fails with "client returned ERROR on write" / "system cannot find the file" even though `curl`'s own URL fetch succeeds — use `-o "C:/Users/.../file.docx"` instead. Pass bash-resolved `/c/...` paths only to pure bash builtins (`cd`, `ls`, `mkdir`); pass `C:/...` paths as arguments to any native binary (python, node, git, curl).
- After downloading, if the user says "add to drive"/"deive" (typo for drive), upload each file straight from the local download folder with the google-workspace skill's `drive upload <path> --parent <inbox_folder_id>` — one call per file is fine, no need to zip or batch them into a single upload.

## Finding one specific file by name/topic when the file-list endpoint is 403

- `GET /courses/COURSE_ID/files` is commonly blocked (403 unauthorized) even with a valid token. Instead call `GET /courses/COURSE_ID/modules?per_page=100&include[]=items` — it returns every module's items inline, each `File`-type item carrying a `title` (the actual filename, e.g. `sample_mid_2.pdf`), a `content_id`, and a direct `url` to that file's metadata endpoint (`/courses/COURSE_ID/files/CONTENT_ID`). Grep the dumped JSON for the filename/keyword the user named (course screenshot of the Modules page is the fastest way to get that exact filename) instead of trying to enumerate files generically.
- Fetch that file's metadata (`/courses/COURSE_ID/files/CONTENT_ID`) to get its signed `url` (`.../download?download_frd=1&verifier=...`), then `curl -sL` that URL to download the actual bytes — don't try to hit the files endpoint directly without the verifier token, it 403s.
- When a user says "X only" (e.g. "midterm 2 only"), grep for that specific qualifier in the dumped modules JSON before downloading everything in a module — course module folders often mix multiple exams' resources (e.g. midterm 1 solutions sit next to a midterm 2 sample in the same "Exam Resources" module) and only one file may match the actual ask.
- When generating a practice exam to mirror a real one, read the real sample first and copy its exact structure (question count, point values, section types — MC/short-answer/graphing/word-problem) with fresh numbers and a parallel topic, rather than inventing a generic structure from the syllabus topic list alone — the real sample is the actual rubric shape the student will face.
- Large textbook PDFs (tens of MB) exceed `read_file`'s extraction size limit and fail with "File is too large." Use a local Python PDF library (pymupdf; `pip install pymupdf` if missing, then `import fitz` or the non-deprecated `import pymupdf`) to extract text directly instead.
- `get_toc()` is often empty on scanned/print-style textbook PDFs. Instead, read the brief/full Contents pages near the front (first ~10 pages) to find each chapter's **printed** page number, then find the actual PDF page index by searching the first few pages of the target chapter range for a unique chapter-opening phrase (e.g. the chapter's opening case-study title). The offset (PDF index − printed page number) is usually constant across the whole book — compute it once from one chapter and reuse it to jump straight to any other chapter.
- Extract only the chapter's page range into a scratch `.txt` file, then read that `.txt` with `read_file` (paginate with offset/limit) rather than re-running PDF extraction repeatedly.
- When building assignment content, use the textbook's exact section/concept headings (as found in the chapter text) rather than generic paraphrases — matching the book's terminology is itself part of what the rubric expects, and it produces a stronger APA citation of the real edition/authors instead of a guessed one.

## Reflection/writing assignments that forbid AI-generated prose

- Fetch and read the specific assignment's full instructions file/page and rubric before drafting, rewriting, or formatting the written component. Follow the relevant module's File items as well as the upload assignment; a truncated description or upload page can omit page requirements and AI restrictions. When instructions permit AI only for grammar checks, distinguish that permitted service from other assistance: do not provide submission-ready replacement paragraphs or imply that AI brainstorming/factual rewriting is expressly authorized. Explain the restriction briefly, preserve the student's reasoning and voice, and offer a grammar-only check of their own revised text. General concept explanations or factual corrections should be clearly separated from prose to submit, with sources and uncertainty identified. Never invent personal experiences or present an AI rewrite as a grammar check.
- These assignment-specific instruction files often also carry their own font/spacing numbers and page-count minimums that differ from the course-wide guidelines page — read them together and apply the specific one (see google-workspace skill's docs-api-advanced-editing.md note on formatting overrides).

## Finding a student's TA, section, and tutorial number for title-page/citation requirements

- Many assignment guideline pages (e.g. a course-wide "ASSIGNMENT GUIDELINES" item) require the title page to name the instructor and the student's own TA by full name, plus the course's tutorial/section number — don't guess these from the syllabus alone.
- `GET /courses/COURSE_ID/users?enrollment_type[]=ta&per_page=20` lists every TA on the course, but if there are multiple TAs (common when one Canvas course shell covers several tutorial sections), this alone doesn't tell you which TA grades a specific student. `GET /courses/COURSE_ID/sections?include[]=students` shows each section's roster; if the student's own section only maps to one TA, confirm via that roster, but if several TAs are listed and sections don't disambiguate, ask the student directly rather than assuming the first TA alphabetically.
- Distinguish a lecture section such as D300 from the tutorial number explicitly required on the title page; finding the lecture section does not verify the tutorial. Avoid downloading an entire class roster merely to identify one student's tutorial. Prefer authorized self-enrollment/section information and ask for genuinely unresolved tutorial/TA details. Batch all remaining missing title-page fields into one concise question set; do not guess student numbers or school emails, or repeat questions already answered in the conversation.
- Once instructor/TA/section/student-number/email are confirmed, the actual title-page rewrite and page-wide formatting (font/margins/line-spacing) happens in the Doc itself — see the google-workspace skill's `references/docs-api-advanced-editing.md` "Applying document-wide formatting" section for the exact `batchUpdate` recipe.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 401 Unauthorized | Token invalid or expired — regenerate in Canvas Settings |
| 403 Forbidden | Token lacks permission for this course |
| Empty course list | Try `--enrollment-state active` or omit the flag to see all states |
| Wrong institution | Verify `CANVAS_BASE_URL` matches the URL in your browser |
| Timeout errors | Check network connectivity to your Canvas instance |
