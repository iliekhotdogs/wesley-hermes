# Advanced Google Docs editing (raw API, beyond the CLI)

The `docs` CLI subcommands (`get`, `create`, `append`) only cover basic read/append. For structural edits — tables, paragraph alignment/centering, surgical text replacement inside an existing doc — go straight to the Docs API via the installed `google_api` module's `build_service("docs", "v1")`, from a profile-local scratch script (see google-workspace SKILL.md's attachment pattern for the `sys.path.insert` + `build_service` boilerplate).

## Google Docs API facts that save time

- **There is no API to create/rename/delete/reorder tabs.** `documents().batchUpdate` can read tab content (`get(..., includeTabsContent=True)`) but has no `CreateTabRequest` equivalent — this is an open Google feature request, not a bug in the wrapper. If a user asks for a "new tab" in a Doc, don't attempt it: either append a clearly-headed section to the same doc for them to move into a tab manually, or create a separate Doc — ask which.
- Table cells, once a table exists, get their own `startIndex` per cell — you cannot pre-compute cell indices before insertion; always `documents().get()` again after `insertTable` to read the real cell `startIndex` values before filling them.

## Reading all document tabs before review

Use the raw API for a complete-document read; a CLI result can expose only the legacy body or first tab while additional plans live elsewhere.

```python
svc = ga.build_service('docs', 'v1')
doc = svc.documents().get(
    documentId=DOC_ID, includeTabsContent=True
).execute()

def text_runs(node):
    if isinstance(node, dict):
        if 'textRun' in node:
            yield node['textRun'].get('content', '')
        for key, value in node.items():
            if key != 'textRun':
                yield from text_runs(value)
    elif isinstance(node, list):
        for item in node:
            yield from text_runs(item)

def extract_tabs(tabs):
    for tab in tabs:
        props = tab.get('tabProperties', {})
        content = tab.get('documentTab', {})
        yield {
            'tab_id': props.get('tabId'),
            'title': props.get('title'),
            'text': ''.join(text_runs(content.get('body', {}))),
        }
        yield from extract_tabs(tab.get('childTabs', []))

sections = list(extract_tabs(doc.get('tabs', [])))
if not sections:
    sections = [{'title': doc.get('title'),
                 'text': ''.join(text_runs(doc.get('body', {})))}]
```

Inspect section titles and every section's text before declaring the document fully reviewed. Preserve boundaries when passing a digest to another agent; a newer tab may contradict an older specification rather than extend it. Extract table text recursively, and inspect inline-object metadata or supplied images separately when a design depends on screenshots; text extraction alone does not review those visuals. For edits, retain the originating tab ID and derive indices within that tab rather than concatenating tabs into a shared index space.

## Locating text to edit safely

Paragraph `textRun`s are split into multiple runs (rarely 1:1 with your mental model of a block of text), so naive substring search inside one run misses or mismatches. Build a flat `(absoluteIndex, char)` list across every paragraph element's `textRun.content`, join it into `full_text`, then `full_text.find(target)` and map back through the (index, char) list to get the real document `startIndex`/`endIndex` for `deleteContentRange`/`insertText`/`updateParagraphStyle`.

## Order of batchUpdate edits across one document

When making several edits to different parts of the same doc, **process from the highest index to the lowest** (bottom of the document first). A `deleteContentRange` or `insertTable`/`insertText` at a higher index never shifts the indices of content earlier in the document, so earlier-computed ranges for upstream edits stay valid without recomputing. Doing it top-to-bottom forces a re-fetch-and-recompute after every single edit.

The document body's very last paragraph (`content[-1]`) is a mandatory trailing empty paragraph — never delete through its `endIndex`; delete up to (but not including) its `startIndex`.

## Building and filling a table

1. `batchUpdate([{"insertTable": {"rows": R, "columns": C, "location": {"index": I}}}])`.
2. Re-`get()` the doc, find the `table` element, walk `tableRows[*].tableCells[*].content[0].startIndex` for each cell's real insertion point.
3. Fill cells in **reverse** row/column order (last cell first) in one `batchUpdate` call with one `insertText` per cell — filling forward shifts every later cell's index after each insert.

## Centering a title page / paragraph

`updateParagraphStyle` with `{"alignment": "CENTER"}` and `"fields": "alignment"` over the paragraph's index range. Re-`get()` after any preceding text replacement to recompute the exact range, since replaced text length rarely matches the original.

## Applying document-wide formatting (font, margins, line spacing)

To enforce a school/house style (e.g. Times New Roman 11pt, 1in margins, single line-spacing) across an entire doc in one shot, don't touch the CLI — go straight to three `batchUpdate` requests against `build_service("docs", "v1")`:

1. `updateDocumentStyle` with `marginTop/Bottom/Left/Right: {"magnitude": 72, "unit": "PT"}` (1 inch = 72pt) and `"fields": "marginTop,marginBottom,marginLeft,marginRight"`.
2. `updateTextStyle` over `{"startIndex": 1, "endIndex": <doc end_index - 1>}` with `weightedFontFamily.fontFamily` and `fontSize: {"magnitude": N, "unit": "PT"}`, fields `"weightedFontFamily,fontSize"`. Get `end_index` from `doc['body']['content'][-1]['endIndex']`.
3. `updateParagraphStyle` over the same full range with `lineSpacing: 100` (single) for paragraphs, fields `"lineSpacing,spaceAbove,spaceBelow"`. If the doc actually has bulleted/numbered lists (check `el['paragraph'].get('bullet')` on each content element) and the style calls for looser list spacing (e.g. 1.1-1.2x), apply a second narrower `updateParagraphStyle` (lineSpacing 110-120) only to those bullet paragraphs' ranges — don't assume a doc has lists without checking.

Course-wide formatting guidelines (e.g. a general "ASSIGNMENT GUIDELINES" page saying single-spacing) are a baseline only — always fetch and read the **specific assignment's own instructions document** before locking in font/spacing numbers; a per-assignment spec (e.g. "11pt, 1.15 spacing") overrides the general course rule, and the general guidelines page itself usually says so explicitly. Re-run the `updateParagraphStyle` lineSpacing request a second time if you applied the general-guideline number before reading the assignment-specific file.

All three requests can go in one `batchUpdate` call. This is also the pattern for rewriting a title page to a required format: find the old title block's `startIndex`/`endIndex` by scanning paragraphs for recognizable anchor text (see "Locating text to edit safely" above), then `deleteContentRange` + `insertText` with the new block, in the same batch if the title block is the lowest-index edit (otherwise do it as a separate call first since later edits need the recomputed indices — see "Order of batchUpdate edits" above).

## Text-style ordering and tab-aware readback

- Apply paragraph named styles before font overrides; setting `namedStyleType` can reset earlier direct text styles. Apply font family/size after paragraph styles, then apply or restore bold emphasis last: changing the full `weightedFontFamily` field can normalize weight and remove existing bold. Read back effective styles with named-style inheritance rather than treating omitted 11pt properties as an error.
- With `includeTabsContent=True`, inspect each `tabs[*].documentTab.documentStyle` as well as the legacy top-level field; tab-aware Docs responses can move style data under the tab. Include the exact tab ID in ranges, locations, and supported document-style requests.
- During in-place academic formatting, preserve newly added live paragraphs and rubric tables even when an earlier plain-text read omitted them. Snapshot current structure, use required revision protection, and compare nonblank paragraph multisets plus exact table cell text after mutation. When the user forbids downloads, do not export a PDF just to verify layout; distinguish verified API formatting from unverified rendered pagination.

## Academic layout and visual verification

1. Read both the assignment-specific instructions and course baseline before selecting font size, spacing, page minimum/limit, component order, or export type. A minimum is not a maximum; count reflection pages separately from the title, references, and rubric when the instructions distinguish them. Check any AI-use restrictions before touching prose.
2. Snapshot the live document structure before editing. Read `documentStyle` from the top-level document, not `body.documentStyle`; inspect paragraph styles, page breaks, tables, lists, and the current text. Preserve the user's live edits and anchor ranges to current content rather than reusing indices from earlier turns.
3. Separate the title page, reflection, references, and rubric using explicit page breaks or `paragraphStyle.pageBreakBefore`, not long runs of blank paragraphs. Place the clickable video link at the beginning of the reflection when required, not above the title page. Remove blank-paragraph padding only after ensuring it does not contain a page break or other non-text element.
4. Keep all explicitly mandated font sizes, including titles, unless the instructions exempt them. Use bold and alignment for hierarchy and `keepWithNext` on headings to avoid orphaned section labels. Prefer paragraph spacing to repeated empty lines. Before adding real list bullets, remove literal dash prefixes in descending index order; otherwise both the glyph and dash appear. Apply the assignment's list-spacing rule to the actual resulting bullet ranges.
5. For a rubric supplied as an image with an exact-appearance request, inspect the image first. An editable reconstruction preserves wording but does not automatically preserve widths, wrapping, font, borders, or pagination. If exact appearance is the priority, insert the supplied image with its aspect ratio preserved through a supported authenticated workflow; do not make a private upload public merely to obtain an image URI. If reconstructing a table, explicitly set column widths, padding, borders, alignment, and label styles, then render and compare before calling it an exact match. Do not claim a page break proves the entire table fits on one page.
6. Re-read the exact edited document after the final batch and verify every required text/style property, including nested table paragraphs. Export a PDF preview via `$GAPI drive download DOC_ID --export-mime application/pdf --output <preview.pdf>` and inspect rendered pages to establish actual page boundaries, body-page count, reference/rubric placement, and table overflow. Use the mandated Word format for the final deliverable when specified; PDF may be only a preview. If no rendered inspection was performed, report API formatting as verified but pagination/visual fit as unverified.
7. Report completed changes and remaining gaps precisely. Existing reference entries do not prove APA compliance or support for in-text factual claims. Do not state that the work meets a page minimum, component order, rubric match, or citation requirement without checking that specific criterion.

## Delivering a doc created under the agent's own Google account

When creating a new Doc via the agent's own OAuth identity (not the user's), it lands in the agent's Drive, not the user's. Immediately `drive share FILE_ID --email <user's address> --role writer --notify` so it's visible in the user's own Drive and they get a notification — don't just hand back the link and assume access.
