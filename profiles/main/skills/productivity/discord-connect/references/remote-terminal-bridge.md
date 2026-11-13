# Gateway-independent PC terminal bridge (Discord -> PowerShell)

Use when the owner wants to control the PC from Discord while the Hermes gateway may be down (e.g. restart it remotely). Hermes itself cannot restart a dead gateway because it is reached through that gateway.

## Design
- A separate small discord.py script with its OWN bot application/token, so it survives gateway outages. Never reuse the gateway bot token.
- Obey only the owner user ID in one private channel. Optional allowlist of commands is the safer variant; free-form shell is higher risk (account takeover = PC takeover) -- recommend Discord 2FA.
- Needs Message Content Intent enabled on the new bot (Developer Portal, owner does this and pastes the token into a local config.env, never into chat).
- Run with the gateway venv python (has discord.py). Config in `config.env` next to the script (token, OWNER_ID, CHANNEL_ID).

## Steps
1. Create the private channel via REST with the main bot token: POST /guilds/{id}/channels with overwrites deny VIEW_CHANNEL (1024) for @everyone (role id == guild id), allow 3072 for owner (type 1) and the main bot. `discord_admin` has no create-channel action; use REST.
2. Write bridge.py (asyncio subprocess `powershell -NoProfile -NonInteractive -Command`, timeouts, output >1900 chars sent as attachment, `!cancel`, shortcuts like `!restart-gateway`).
3. The new bot is a separate user: it gets 403 Missing Access (50001) on the channel until you PUT /channels/{cid}/permissions/{bot_id} with type 1, allow 101376 (view+send+history+attach). Bot ID = base64-decoded first segment of its token.
4. Verify by reading the channel's latest messages via REST for the bot's "online" post.

## Restarting the multiplexed gateway from the bridge
1. Confirm that `bridge.py` is running independently of the gateway and inspect its exact command dispatch. Some bridges run arbitrary text as PowerShell and offer a shortcut that appends a status check; verify what that shortcut actually expands to before recommending it.
2. Run `hermes -p default gateway status` through the bridge to identify the host-owning gateway. A bare `hermes gateway restart` may resolve the bridge's inherited `HERMES_HOME` to `main` and fail with a child-profile ownership message; that does not prove the bridge is gateway-dependent.
3. From the independent bridge, use `hermes -p default gateway restart`. If a noninteractive confirmation is refused due to live work, decide whether interruption is authorized before adding `-y`. Follow with `hermes -p default gateway status` and inspect the bridge's exit code and output. A PowerShell shortcut using `;` runs the status command even if restart fails, so a healthy final status alone is not proof that restart succeeded.
4. If the bridge itself is offline, use a local PC terminal rather than a gateway-hosted Discord conversation. Avoid `--force`, standalone mode, reinstall, or migration for a profile-selection error.

## Persistence on Windows without admin
- `Register-ScheduledTask -AtLogOn` is Access Denied without elevation. Use a Startup-folder `.vbs` that launches a `run.cmd` loop (restart after 10s) hidden. Survives crashes and logins, not a reboot before login.
- Launching from the agent's terminal tool ties the child to the tool's job and it dies when the call ends; start it detached from Python: `subprocess.Popen(['cmd','/c',run.cmd], creationflags=0x08|0x200|0x08000000, close_fds=True, stdin/stdout/stderr=DEVNULL)`.
- Confirm by the bot's posted message, not by process listing (pipe/WMI output in the agent shell is noisy).
