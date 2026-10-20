# Google Sheets Budget Repair Reference

## Proven repair pattern

1. Read spreadsheet metadata to get sheet names and stable sheet IDs.
2. Read `Input` and `Transactions` using `valueRenderOption=FORMULA` and hash
   the returned values before any write.
3. Analyze source rows programmatically to discover actual categories and
   debit totals. Do not infer categories from the Summary display labels.
4. Write only `Summary` and `Dashboard` with `values.batchUpdate` and
   `valueInputOption=USER_ENTERED`.
5. Clear stale derived cells when moving a dashboard section, but never clear
   source ranges.
6. Update existing chart source ranges with `updateChartSpec` when the number
   of categories changes.
7. Read back formulas and unformatted values, then re-hash source tabs.

## Formula template

For a category in `Summary!A3`, where Input category is column C and amount is
column F:

```text
=SUMIFS(Input!$F:$F,Input!$C:$C,A3,Input!$F:$F,"<0")*-1
```

For reimbursements:

```text
=SUMIFS(Input!$F:$F,Input!$C:$C,"reimbursement",Input!$F:$F,">0")
```

For dashboard payments:

```text
=COUNTIF(Input!F2:F,"<0")
```

For recent negative transactions, use `FILTER` plus `INDEX` so credits and
starting balances do not appear as payments:

```text
=INDEX(FILTER(Input!B$2:B,Input!F$2:F<0),1)
```

## Important pitfall

Mixed date types are common: manually entered dates may be numeric serials,
while imported bank dates may be text. Therefore `COUNT(Input!B2:B)` can
undercount transactions severely. Count the amount column with a negative
criterion instead.

Likewise, `ABS()` over every transaction is wrong for a budget that contains
credits. It makes reimbursements/income look like expenses. Filter negative
amounts for spending and positive reimbursement rows separately.

## Audit evidence

Record the exact source ranges hashed, before and after digests, the formulas
written, and the post-write totals. A successful API write alone is not enough;
readback is required before reporting completion.