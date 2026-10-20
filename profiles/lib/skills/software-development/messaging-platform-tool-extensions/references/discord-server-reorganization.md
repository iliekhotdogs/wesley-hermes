# Discord Server Reorganization: Verified Sequence

Use this procedure for a live Discord rearrangement that also changes Hermes cron delivery targets. It minimizes destructive risk, preserves channel-specific permissions, and leaves a verifiable routing map.

## Preconditions

- The scoped Discord admin tool exposes `list_guilds`, `list_channels`, `create_channel`, `rename_channel`, and `move_channel`.
- `move_channel` has an internal two-pass confirmation gate.
- Cron jobs are managed through the cron tool, not by editing job files.
- The user has approved the target layout. Do not delete old channels merely to make the layout cleaner.

## Procedure

1. **Inventory live state.** Call `list_guilds`, then `list_channels`. List cron jobs before any update. Record immutable category/channel IDs and each active job's current `deliver` target.
2. **Activate missing native actions if needed.** Add and test the complete action path (implementation, dispatch, manifest, required params, schema, shared-handler arguments, `local_vars`, defaults, 403 guidance, allowlist compatibility). Run targeted tests and the full platform-tool module.
3. **Reload safely.** Restart/reload the gateway once. A messaging restart can terminate the current turn; after reconnecting, do not restart again. Re-describe the live admin schema and make a harmless read call to prove the new actions loaded.
4. **Create destination categories first.** Capture returned category IDs. Read the channel tree back before depending on them.
5. **Apply non-destructive renames.** Rename categories/channels with a body containing only `name`; omission preserves topics, permissions, NSFW settings, and other fields.
6. **Create new destination channels.** Set `parent_id`, topic, and desired position explicitly. Capture and read back their IDs before scheduler edits.
7. **Move existing channels with the two-pass gate.** First call without confirmation and verify `confirmation_required: true` with no network mutation. Then call with `confirmed=true`. The move body may contain `parent_id` and `position`, but never `permission_overwrites`. A position-only confirmed move can reorder categories.
8. **Retarget dependent cron jobs.** Update each active job's `deliver` to `discord:<channel_id>`. Leave already-correct jobs unchanged. Completed one-shot jobs normally remain historical and need no retargeting.
9. **Verify both external states.** Read the full channel tree and list all cron jobs again. Programmatically or systematically verify every category, channel, parent, position, topic, and active delivery route. Do not claim completion from successful write responses alone.

## Confirmation-Gate Detail

A first-pass move commonly returns:

```json
{
  "success": false,
  "confirmation_required": true,
  "message": "Move channel ...? Existing permission overwrites will be preserved."
}
```

This is expected control flow, not a failed operation. Review it and issue exactly one confirmed call. Several unconfirmed moves in one batch can look like repeated same-tool failures to loop guardrails; keep gate passes small or explicitly diagnose the expected response before the confirmed batch.

## Final Verification Map

Produce a concise tree plus a routing list:

```text
CATEGORY
├─ channel-a
└─ channel-b

channel-a
- Job 1
- Job 2
```

Explicitly state whether anything was deleted and whether permission overwrites/topics were preserved.
