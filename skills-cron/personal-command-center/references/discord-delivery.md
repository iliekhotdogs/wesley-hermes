# Discord Delivery Pattern

Cron jobs that deliver to Discord have specific constraints that affect whether messages land correctly.

## Message Length

- Discord messages have a **2,000 character limit**
- The cron job's final response is sent as one message
- The full output file (in `%APPDATA%\hermes\cron\output\<job_id>\<timestamp>.md`) includes the skill text and is always over the limit — only the `## Response` section counts
- Keep the actual response content under **1,500 characters** to leave room for the cron wrapper overhead

## Thread vs Main Channel

- `attach_to_session: true` → opens a **continuable thread** on the target channel
  - Message appears in a thread, not the main channel
  - Users see a thread notification but may not find the message
  - Only use for conversational threads
- `attach_to_session: false` → posts directly to the **main channel**
  - Use for one-way informational delivery (briefings, digests, reports, alerts)

## Verification

### Check the Output File

```bash
awk '/^## Response/{found=1} found{print}' <file> | wc -c
```

### Check Delivery Logs

```bash
grep "<job_id>" %APPDATA%\hermes\logs\agent.log | tail -5
```

- `delivered to discord:<channel_id> via live adapter` → success
- `opened continuable thread` → message went to a thread, not main channel
- `delivery_error` → message failed to send
- `skipped: RuntimeError: Skipped to prevent unintended spend` → config drift

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Message not visible in channel | `attach_to_session: true` opened a thread | Set `attach_to_session: false` |
| Message rejected silently | Response over 2,000 chars | Shorten prompt or response format |
| Job skipped | Config drift (provider/model changed) | Pin provider/model or update job config |
| Wrong channel | Incorrect `deliver` target | Verify channel ID in job config |
