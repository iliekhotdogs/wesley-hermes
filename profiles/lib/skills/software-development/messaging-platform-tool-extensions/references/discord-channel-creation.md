# Discord Channel Creation: Proven Wiring

## Symptom Pattern

A Discord bot answered a trivial greeting in a few seconds, but a request to create a channel took many minutes and many model/tool turns. Transcript inspection showed repeated browser attempts, an unauthorized shell request, and credential-file searches. The decisive check was the `discord_admin` action manifest: it could list channels and create threads, but it had no regular channel-creation action.

This is a capability mismatch, not general model slowness.

## Discord REST Contract

Create a guild channel with:

```text
POST /guilds/{guild_id}/channels
```

Minimal text-channel body:

```json
{
  "name": "announcements",
  "type": 0
}
```

Optional fields used by the native action:

```json
{
  "parent_id": "CATEGORY_CHANNEL_ID",
  "topic": "Important updates"
}
```

The bot needs Discord's `MANAGE_CHANNELS` guild permission. A 403 should be translated into that specific guidance.

## Hermes Tool Surfaces to Update

For an action named `create_channel`, wire all of these:

- `_create_channel(...)` implementation using the existing scoped token and `_discord_request`
- `_ACTIONS["create_channel"]`
- `_ACTION_MANIFEST`
- `_REQUIRED_PARAMS` with `guild_id` and `name`
- schema properties for `channel_type`, `parent_id`, and `topic`
- `_run_discord_action` signature, local-vars validation map, and forwarded call
- `_HANDLER_DEFAULTS`
- `_ACTION_403_HINT`

Keep it in `discord_admin`, not the core Discord participation tool.

## Behavioral Test Shape

Patch only `_discord_request`, call `discord_admin_handler`, and assert:

```python
result = json.loads(discord_admin_handler(
    action="create_channel",
    guild_id="111",
    name="announcements",
    channel_type="text",
    parent_id="10",
    topic="Important updates",
))
```

Expected request:

```python
mock_req.assert_called_once_with(
    "POST",
    "/guilds/111/channels",
    "test-token",
    body={
        "name": "announcements",
        "type": 0,
        "parent_id": "10",
        "topic": "Important updates",
    },
)
```

Expected result should include `success`, `channel_id`, normalized `type`, `parent_id`, and `topic`.

## Operational Guardrails

- In the admin schema description, direct the model to native actions and explicitly forbid browser fallback for Discord administration.
- Keep bot tokens inside secret scope; never copy them into curl or browser scripts.
- Lower an excessively large turn budget only as a loop limiter, not as the fix.
- Restart/reload the gateway before calling the feature active.
- After a real create call, list channels and confirm the exact returned channel ID/name before reporting success.
