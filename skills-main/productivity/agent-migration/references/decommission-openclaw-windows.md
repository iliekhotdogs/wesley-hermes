# Decommission OpenClaw on Windows — Complete Checklist

Session-specific detail from fully removing OpenClaw from Wesley's machine (2026-08-30). Use this when the user wants the old framework *completely wiped*, not just migrated away from.

## Why this exists

OpenClaw installs itself in multiple locations on Windows. A partial removal leaves dead scheduled tasks, startup entries, dangling PATH references, and SQLite files that are locked by a running gateway process. This checklist covers every location found and the exact removal order.

## Removal order (dependency-aware)

### Step 1: Stop all OpenClaw processes

OpenClaw's gateway locks its own SQLite files. On Windows, you cannot delete a file while a process holds an open handle.

**Find the gateway:**
```powershell
Get-WmiObject Win32_Process -Filter 'Name="node.exe"' | Where-Object { $_.CommandLine -like '*openclaw*' } | Select-Object ProcessId, CommandLine
```

**Kill it:**
```powershell
Stop-Process -Id <PID> -Force
```

**Verify:**
```powershell
Get-Process -Id <PID> -ErrorAction SilentlyContinue
```

If the process won't die, check for child processes or a wrapper service. OpenClaw's gateway typically runs as `node.exe dist/index.js gateway --port 18789`.

### Step 2: Backup before destructive action

Always create a timestamped archive before deleting. The user may later realize they needed something.

```bash
ts=$(date +%Y%m%d_%H%M%S)
backup_path="$HOME/Desktop/openclaw_backup_${ts}.tar.gz"
tar -czf "$backup_path" -C "$HOME" .openclaw
```

**Verify the backup:**
- `gzip -t "$backup_path"` — integrity check
- `sha256sum "$backup_path"` — capture hash
- `tar -tzf "$backup_path" | wc -l` — file count

If the archive is >1GB (common when `npm/node_modules` is included), expect the backup to take several minutes. Run in background.

### Step 3: Remove the main data directory

```bash
rm -rf "$HOME/.openclaw"
```

**Expected failure:** SQLite files will report "Device or resource busy" if the gateway wasn't killed first. Kill the process and retry.

**Verify:**
```bash
ls "$HOME/.openclaw" 2>&1  # should say "No such file or directory"
```

### Step 4: Uninstall the global npm package

```bash
npm uninstall -g openclaw
```

This removes:
- `~/AppData/Roaming/npm/openclaw` (shell wrapper)
- `~/AppData/Roaming/npm/openclaw.cmd`
- `~/AppData/Roaming/npm/openclaw.ps1`
- `~/AppData/Roaming/npm/node_modules/openclaw/` (the full package, often 100MB+)

### Step 5: Remove the local deps directory

OpenClaw stores portable-git and other deps separately from the main data directory.

```bash
rm -rf "$HOME/AppData/Local/OpenClaw"
```

**Size:** Typically 50-100MB.

### Step 6: Remove the startup entry

```bash
rm "$HOME/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/OpenClaw Gateway.vbs"
```

The VBS file is typically a wrapper that launches the gateway. It may not exist on all installs.

### Step 7: Remove the scheduled task

OpenClaw registers a Windows Scheduled Task named "OpenClaw Gateway" that runs at user logon.

**Try PowerShell:**
```powershell
Unregister-ScheduledTask -TaskName 'OpenClaw Gateway' -Confirm:$false
```

**If that fails with Access Denied** (common): try `schtasks`:
```cmd
schtasks /delete /tn "OpenClaw Gateway" /f
```

**If both fail:** The task is dead anyway if it points to the deleted `~/.openclaw/gateway.vbs`. Verify:
```cmd
schtasks /query /tn "OpenClaw Gateway" /v /fo LIST
```

If "Task To Run" points to a non-existent file, the task is harmless. Leave it and report to the user.

### Step 8: Clean PATH entries

Check for dangling OpenClaw references:
```bash
echo "$PATH" | tr ':' '\n' | grep -i openclaw
```

Typical entries to remove:
- `C:\Users\<user>\AppData\Local\OpenClaw\deps\portable-git\mingw64\bin`
- `C:\Users\<user>\AppData\Local\OpenClaw\deps\portable-git\usr\bin`

Remove via System Properties → Environment Variables → User PATH. (Requires user action — cannot be done programmatically without registry writes.)

### Step 9: Final artifact sweep

```bash
# Find any remaining openclaw-named files anywhere in the user tree
find "$HOME" -iname '*openclaw*' -type f 2>/dev/null
```

On Windows with MSYS, this may be slow. PowerShell alternative:
```powershell
Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter '*openclaw*' -ErrorAction SilentlyContinue | Select-Object FullName
```

**Expected leftovers (benign, can ignore):**
- Backup archive you created in Step 2
- Old migration zips in `~/shared with old pc/` or `~/OneDrive/`
- Documentation/reference files in `~/OneDrive/`
- `.lnk` shortcut files in `~/AppData/Roaming/Microsoft/Windows/Recent/`

## Locations checklist

| Location | What | Size |
|----------|------|------|
| `~/.openclaw/` | Main data (agents, workspaces, config, state, SQLite) | 2-4 GB |
| `~/AppData/Local/OpenClaw/` | Deps (portable-git) | ~90 MB |
| `~/AppData/Roaming/npm/node_modules/openclaw/` | npm package + extensions | ~100+ MB |
| `~/AppData/Roaming/npm/openclaw*` | CLI wrappers (3 files) | <1 KB |
| Startup folder | `OpenClaw Gateway.vbs` | <1 KB |
| Scheduled task | "OpenClaw Gateway" | — |
| PATH | `AppData/Local/OpenClaw/deps/...` | — |

## Verification

After removal, confirm:
1. `ls ~/.openclaw` → "No such file or directory"
2. `npm ls -g openclaw` → "(empty)"
3. `echo "$PATH" | grep -i openclaw` → empty
4. Startup folder has no `OpenClaw` entries
5. `schtasks /query /tn "OpenClaw Gateway"` → either "ERROR: The system cannot find the file specified" (removed) or points to a deleted file (dead)
6. Final file sweep shows only intentional leftovers (backup, old archives)

## Gotchas

1. **SQLite file locking is the #1 blocker.** The gateway holds open handles to `.sqlite`/`.sqlite-wal`/`.sqlite-shm` files in every agent's directory AND the main `state/` directory. Kill the process FIRST, then delete.
2. **Multiple node processes may be running.** OpenClaw's gateway is `node.exe dist/index.js gateway`. Other node processes (Codex, Next.js, etc.) are unrelated — check the command line before killing.
3. **Backup size can be huge.** The `npm/node_modules` tree inside `~/.openclaw/` is often 1-2 GB. Compress with `tar -czf` and expect several minutes of work.
4. **Scheduled task access denied is common on Windows.** The task may have been created by a different user context. If both PowerShell and schtasks fail, the task is dead if its target file is gone — report it and move on.
5. **PATH cleanup is manual on Windows.** There's no reliable programmatic way to edit user PATH from bash/MSYS without registry writes. Tell the user which entries to remove.
6. **Startup entries are sometimes .vbs files.** Don't just look for `.exe` or `.lnk` — check for `.vbs`, `.bat`, and `.ps1` wrappers.

## Execution results (2026-08-30)

Removal executed successfully on Wesley's machine:
- Backup: `~/Desktop/openclaw_backup_20260830_121900.tar.gz` (1.4 GB, 52,276 files, SHA256 `314dcc883b36567ee1e15b002ec9dd5b8e248b8b635d09fc396d9bcdcf8fad2f`)
- Gateway killed: PID 8116 (`node.exe dist/index.js gateway --port 18789`)
- `~/.openclaw/` removed after killing the gateway
- `npm uninstall -g openclaw` — removed 309 packages
- `~/AppData/Local/OpenClaw/` removed (91 MB)
- Startup entry `OpenClaw Gateway.vbs` removed
- Scheduled task "OpenClaw Gateway" — dead (pointed to deleted `~/.openclaw/gateway.vbs`), couldn't remove due to Windows permissions
- PATH entries to `OpenClaw/deps/portable-git/` remain (manual cleanup needed)
- Disk space recovered: ~3.5 GB