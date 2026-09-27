---
name: budget-spreadsheet-reconciliation
description: "Use when reconciling a budget spreadsheet."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [budget, spreadsheet, Google Sheets, payments, reconciliation, dashboard]
    category: productivity
---

# Budget Spreadsheet Reconciliation

Repair budget workbooks—especially Google Sheets budgets with manually labeled
source data—without overwriting the user's source tabs. The goal is a
recalculated, auditable Summary and Dashboard, not a reclassification of the
underlying transactions.

## Scope and source-tab protection

1. Identify the workbook and enumerate sheet names before writing anything.
2. Determine which tabs are source/input tabs (commonly `Input` and
   `Transactions`) and which are derived/reporting tabs (commonly `Summary` and
   `Dashboard`).
3. Treat source tabs as read-only unless the user explicitly asks to change
   them. Do not normalize dates, rewrite categories, re-sort rows, add IDs, or
   "fix" hand-entered labels.
4. Read formulas with `valueRenderOption=FORMULA` and computed values with
   `UNFORMATTED_VALUE`; do not rely on displayed currency strings for
   arithmetic.
5. Before writing, capture a deterministic digest of the source-tab values.
   After writing, read the exact same ranges and verify the digests match.

## Reconciliation rules

- A payment/expense is a negative amount in the source amount column. Summaries
  should report it as a positive spend using `SUMIFS(...,"<0")*-1`.
- Reimbursements are not expenses. Report positive reimbursement amounts in a
  separate total, normally filtered by category `reimbursement` and amount
  `">0"`.
- Net spending is total payments minus total reimbursed.
- Do not use `ABS()` across all transactions: that incorrectly turns income,
  reimbursements, deposits, and other credits into spending.
- Build category rows from the categories actually present in the source
  category column. A display list such as `lunch`, `dinner`, or `groceries`
  must not be used unless those labels are actually in the transaction data.
- Use full-column or sufficiently extended ranges so imported rows beyond the
  first few manually entered rows are included. Avoid a fixed `2:1000` range
  when the sheet contains more rows.
- For dashboards, count payments with `COUNTIF(amount_range,"<0")`, not
  `COUNT(date_range)`, because imported dates may be text while manually
  entered dates are serial values.
- Average payment should average negative amounts only and invert the sign:
  `=IFERROR(AVERAGEIF(amount_range,"<0",amount_range)*-1,0)`.

## Summary repair

Keep the existing visual layout where possible. Replace stale category labels
and formulas only on the Summary tab. A robust category row formula is:

```text
=SUMIFS(Input!$F:$F,Input!$C:$C,A3,Input!$F:$F,"<0")*-1
```

Update percentage formulas to divide by the new total-expenses cell. Add or
extend the chart source range if the category list grows; otherwise the chart
can silently omit valid spending categories.

## Dashboard repair

Keep dashboard labels and formatting, but make headline metrics reference the
Summary totals. Recommended metrics are total expenses, total reimbursed, net
spending, payment count, average payment, and top payment category. Category
helper tables should link to Summary rather than duplicate hardcoded amounts.
Recent payments should filter for negative source amounts and return the first
few rows in the workbook's ordering, rather than using `COUNTA()` over a mixed
numeric/text date column.

## Google Sheets execution

Use the Google Sheets API through the configured Google Workspace helper or
`googleapiclient` with the authenticated token. Batch related value writes,
then read back the exact Summary and Dashboard ranges. When a chart exists,
update its source range through `spreadsheets.batchUpdate` rather than deleting
and recreating it unnecessarily.

All external writes require explicit user authorization. The user's direct
request to repair named tabs is the authorization for that scoped repair; do
not broaden it to source-tab edits or unrelated formatting changes.

## Verification checklist

- Input/source tabs have identical before/after digests.
- Transactions/source tabs have identical before/after digests.
- Summary formulas reference the source amount/category columns and negative
  amount criteria.
- Total expenses equals the sum of category payment amounts.
- Total reimbursed is separate and positive.
- Net spending equals expenses minus reimbursements.
- Dashboard headline cells match Summary totals.
- Dashboard payment count is nonzero when negative source amounts exist.
- Dashboard recent-payment rows contain negative amounts.
- Existing charts cover the full category output range.

See `references/google-sheets-budget-repair.md` for the reusable API pattern,
formula design, and verification details from a completed repair.