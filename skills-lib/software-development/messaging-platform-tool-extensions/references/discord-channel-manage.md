# Discord Channel Rename / Move / Delete: Proven Wiring

## Symptom Pattern

A Discord bot could create channels and threads but had no native action to rename, move, or delete existing channels. Requests to reorganize or clean up channels fell back to browser automation or shelling out with the bot token — slow, fragile, and against the scoped-tool principle.

This is a capability mismatch, not general model slanginess.

## Discord REST Contract

All three operations use the same endpoint with different methods/bodies:

```text
PATCH  /channels/{channel_id}   → rename / move
DELETE /channels/{channel_id}   → delete
```

### Rename (non-destructive)

```json
{ "name": "new-name" }
```

Only `name` is sent. Permissions, topic, position, NSFW flag, rate limit, and parent_id are preserved by Discord because they're omitted from the PATCH body.

### Move (destructive — reorganizes channel structure)

```json
{ "parent_id": "TARGET_CATEGORY_ID", "position": 2 }
```

**Critical:** deliberately OMIT `permission_overwrites` from the body. Discord's PATCH replaces the entire permission_overwrites array with whatever you send. If you omit it, the existing overwrites are preserved. If you send `permission_overwrites: []` (or any value), you wipe all existing channel-specific permissions.

`position` is optional; Discord auto-assends when omitted.

### Delete (destructive — irreversible)

No body. Returns `204 No Content`. All messages in the channel are permanently lost.

The bot needs Discord's `MANAGE_CHANNELS` guild permission for all three. A 403 maps to that specific guidance.

## Confirmation Gate Pattern

Destructive actions (move, delete) use a two-step confirmation gate implemented inside the action function itself:

1. **First call** (without `confirmed=True`): returns immediately with `success: false`, `confirmation_required: true`, and a human-readable message describing what will happen. No network call is made.
2. **Second call** (with `confirmed=True`): executes the actual REST request.

This keeps the gate inside the scoped tool (no separate approval system) while giving the model — and through it, the user — a chance to review before executing.

Implementation shape:

```python
def _move_channel(token, channel_id, target_category_id="", position=0, confirmed=False, **_kwargs):
    if not confirmed:
        return json.dumps({
            "success": False,
            "confirmation_required": True,
            "message": f"Move channel {channel_id} under category {target_category_id}? ...",
        })
    # ... actual request
```

The schema description documents this policy so the model knows to call once, present the prompt, then call again.

## Hermes Tool Surfaces to Update

For each new action, wire all of these (same checklist as create_channel):

1. Action implementation function
2. `_ACTIONS` dispatch map
3. `_ACTION_MANIFEST` (visible to the model)
4. `_REQUIRED_PARAMS`
5. JSON schema properties (new params like `new_name`, `target_category_id`, `position`, `confirmed`)
6. `_run_discord_action` signature, local-vars map, and forwarded call
7. `_HANDLER_DEFAULTS`
8. `_ACTION_403_HINT` entry
9. Schema description update (for destructive-action policy)

## Behavioral Test Shape

Patch only `_discord_request`, call `discord_admin_handler`, and assert:

```python
# Confirmation gate fires before any network call
result = json.loads(discord_admin_handler(action="delete_channel", channel_id="14"))
assert result["confirmation_required"] is True
mock_req.assert_not_called()

# Confirmed call executes
mock_req.return_value = None  # 204
result = json.loads(discord_admin_handler(action="delete_channel", channel_id="14", confirmed=True))
assert result["success"] is True
mock_req.assert_called_once_with("DELETE", "/channels/14", "test-token")
```

For move, assert the body contains ONLY `parent_id` (and optionally `position`) — never `permission_overwrites`.

## Operational Guardrails

- **Permission preservation on move:** always assert `"permission_overwrites" not in body` in your move test. This is the single most important correctness check — a move that wipes channel permissions is a footgun.
- **Confirmation gate ordering:** the gate must return BEFORE the network call. Test this with `mock_req.assert_not_called()` on the unconfirmed path.
- **Schema description:** document the destructive-action confirmation policy in the admin tool description so the model doesn't try to confirm via a separate mechanism.
- **Restart/reload the gateway** before claiming the feature is active.
- **Live test on a non-critical channel first** — rename is safest (non-destructive). Verify permissions/topic survive a move before using it on a real channel.
