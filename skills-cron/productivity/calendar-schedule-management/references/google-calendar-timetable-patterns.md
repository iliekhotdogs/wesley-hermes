# Google Calendar timetable patterns

## Managed-event replacement

Use a description marker such as:

```text
COURSE SECTION
Auto-imported from schedule
```

Read the full semester range with a sufficiently large page limit, select only events whose description contains `Auto-imported from schedule`, and preserve all other events. For a confirmed replacement, delete the selected IDs, create one timed event per source row, and verify:

- expected row count equals managed-event count;
- every `(local date, summary, local start, local end)` source key exists exactly once;
- no old-only course summaries remain;
- unmarked event count is unchanged.

## Vancouver timezone

```python
from datetime import datetime
from zoneinfo import ZoneInfo

vancouver = ZoneInfo("America/Vancouver")
start = datetime.strptime(
    f"{date} {start_text}", "%Y-%m-%d %I:%M %p"
).replace(tzinfo=vancouver)
end = datetime.strptime(
    f"{date} {end_text}", "%Y-%m-%d %I:%M %p"
).replace(tzinfo=vancouver)
```

Convert API values back with `.astimezone(ZoneInfo("America/Vancouver"))` before comparing. This avoids the one-hour error that occurs when fall-term rows after the daylight-saving transition are created with a single fixed offset.

## Color assignment

The Google Calendar API supports `colorId` on events. A practical course mapping is:

```python
colors = {
    "MATH 157": "9",   # blueberry
    "BUS 201": "5",    # banana
    "BUS 203": "10",   # basil
    "ECON 103": "6",   # tangerine
    "PHIL 105": "3",   # grape
}
```

Group by course prefix but apply the selected ID to every section summary for that course. Update with `events().update(..., sendUpdates='none')`, then list the exact range again and assert each managed event's `colorId` matches its course mapping. The CLI's create/delete interface may not expose event updates, so direct `googleapiclient` use is an appropriate fallback when the token has calendar write scope.
