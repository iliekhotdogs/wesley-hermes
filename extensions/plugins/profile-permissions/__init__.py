"""Profile tool boundaries; privileged steps are performed by main."""
import re
import shlex
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_POLICY = json.loads((_DIR / 'policy.json').read_text(encoding='utf-8'))
_spec = importlib.util.spec_from_file_location('profile_permissions_workspace_policy', _DIR / 'workspace_policy.py')
workspace_policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(workspace_policy)
ROLE_TOOLSETS = {role: set(names) for role, names in _POLICY['role_toolsets'].items()}
WORKER_KANBAN = set(_POLICY['worker_kanban'])
CRON_GOOGLE_ROUTINE = {service: set(ops) for service, ops in _POLICY['cron_google_routine'].items()}
PYTHON_EXE = re.compile(r'(?i)^(?:python(?:3(?:\.\d+)?)?|pythonw|py)(?:\.exe)?$')
GOOGLE_HELPER = re.compile(r'(?i)workspace_api|google_api')
HERMES_HOME_REF = re.compile(
    r'(?:^|[\s"\'/~])\.hermes(?:/|$|[\s"\'])|(?:appdata/local|localappdata[%}]?)/hermes(?:/|$|[\s"\'])'
    r'|\$\{?(?:env:)?hermes_home'
)
HERMES_GLOB = re.compile(r'(?i)[^\s"\'/\\]*[*?\[][^\s"\'/\\]*')
GOOGLE_NON_ROUTINE = workspace_policy.DENIED
PRIVILEGED_COMMAND = re.compile(
    r'(?i)\b(?:sudo|runas|icacls|takeown|reg|schtasks|set-acl|remove-item|rm|rmdir|del|taskkill|stop-process)\b'
    r'|\b(?:pip|pip3|uv|npm|pnpm|yarn|winget|choco)\s+(?:install|add|remove|uninstall|upgrade|update|sync|exec)\b'
    r'|\bgit\s+(?:push|reset\s+--hard|clean|config)\b'
    r'|\b(?:netlify|vercel)\s+(?:deploy|env|login)\b'
    r'|\b(?:hermes(?:\.exe)?|hermes_cli\.main)\s+(?:--?p(?:rofile)?\s+\S+\s+)?(?:setup|login|logout|auth|config\s+set|update|uninstall|gateway\s+(?:start|stop|restart))\b'
    r'|\bgh\s+(?:pr|issue|release|repo)\s+(?:create|edit|merge|close|delete|comment|review)\b'
    r'|\bgh\s+api\s+.*(?:--method|-X)\s+(?:POST|PUT|PATCH|DELETE)\b'
    r'|\bcurl\s+.*(?:--request|-X)\s+(?:POST|PUT|PATCH|DELETE)\b'
    r'|(?:^|\s)(?:python\S*|node|powershell|pwsh|bash|sh)\s+(?:-c|-e|-command|-encodedcommand)\b'
)
# A token anywhere (path component or command word), not only the final path segment.
SECRET_NAMES = re.compile(
    r'(?i)(?:^|[\s"\'\\/=])(?:\.env(?:\.[^\s"\'\\/]*)?|auth\.json|google_(?:token|client_secret|oauth_pending)\.json)'
    r'(?=$|[\s"\'\\/])')
MEMORY_NAMES = re.compile(r'(?i)(?:^|[\\/])(?:MEMORY\.md|USER\.md)$')
SHELL_CONTROL = re.compile(r'[;&|<>`\n\r]|\$\(')
# The hook sees literal text; the shell may expand these into different paths or values.
SHELL_EXPANSION = re.compile(r'[$%*?\[\]{}~`]')
ENV_EXPANSION = re.compile(r'[$%`]')
WRITABLE_CODE = {'.py', '.pth', '.json', '.yaml', '.yml', '.toml', '.ps1', '.psm1', '.bat', '.cmd', '.sh', '.exe', '.dll'}


def _blocked(role, reason):
    return {'action': 'block', 'reason': reason, 'message': (
        f'MAIN_REQUIRED: {role}: {reason}. Do not retry, rephrase, change permissions, '
        'or ask the user. On a Kanban assignment call kanban_block once with kind="capability" '
        'and include the exact step and target needed from main. Otherwise return the request '
        'to main in your final response. Main can perform the privileged step and resume the work.'
    )}


def _paths(args):
    values = [args.get(key) for key in ('path', 'file_path', 'target_path', 'directory')]
    patch = args.get('patch')
    if isinstance(patch, str):
        values.extend(re.findall(r'^\*\*\*\s*(?:Add|Update|Delete) File:\s*(.+)$', patch, re.M))
        values.extend(re.findall(r'^\*\*\*\s*Move to:\s*(.+)$', patch, re.M))
    return [Path(value).expanduser().resolve() for value in values if isinstance(value, str) and value]


def _install_of(home):
    return home.parent.parent if home.parent.name == 'profiles' else home


def _protected(path, role, home):
    """Inside the Hermes install but outside the task-local write exceptions."""
    install = _install_of(home)
    if not path.is_relative_to(install):
        return False
    exceptions = [home / 'sessions', install / 'kanban' / 'workspaces']
    if role == 'lib':
        exceptions.extend([home / 'memories', install / 'profiles' / 'main' / 'memories'])
    return not any(path.is_relative_to(root) for root in exceptions)


def _local_file_reason(value, home, writing):
    if not value or value.startswith('-') or SHELL_EXPANSION.search(value) or not Path(value).is_absolute():
        return 'Drive transfers need an explicit absolute local path without shell expansion'
    path = Path(value).resolve()
    if SECRET_NAMES.search(str(path)):
        return 'direct access to credential files is reserved for main; use the installed API wrapper'
    if _protected(path, 'cron', home) or (writing and path.suffix.lower() in WRITABLE_CODE):
        return 'Hermes configuration, plugins, and installed scripts are maintained by main'
    return None


def _download_reason(args, home):
    outputs = []
    for index, word in enumerate(args):
        lowered = word.lower()
        if lowered.startswith('--output='):
            outputs.append(word.split('=', 1)[1])
        elif lowered == '--output':
            outputs.append(args[index + 1] if index + 1 < len(args) else '')
        elif lowered.startswith(('--o', '-o')):
            return 'spell out --output; abbreviated output flags are not accepted'
    if not outputs:
        return 'drive download needs an explicit absolute --output path'
    for value in outputs:
        reason = _local_file_reason(value, home, writing=True)
        if reason:
            return reason
    return None


def _request_file_reason(value):
    # workspace_api.py re-checks the same policy at run time, so rewriting the file after this check fails closed.
    path = Path(value)
    if SHELL_EXPANSION.search(value) or not path.is_absolute() or SECRET_NAMES.search(str(path)):
        return 'workspace requests need an absolute task-local JSON file path without shell expansion'
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'the workspace request file is missing or not readable JSON'
    return workspace_policy.workspace_request_reason(payload, _POLICY)


def _expands(raw):
    """Quotes stop globbing, braces and tilde, but not $VAR or %VAR%."""
    quoted = len(raw) > 1 and raw[0] == raw[-1] and raw[0] in '"\''
    return (ENV_EXPANSION if quoted else SHELL_EXPANSION).search(raw)


def _terminal_reason(role, command, home):
    if not isinstance(command, str) or not command.strip():
        return 'a concrete command is required'
    if role != 'cron' and GOOGLE_HELPER.search(command):
        return 'Google Workspace helpers run only in cron or through main'
    if role == 'builder' and (';' in command or '&&' in command or '||' in command):
        parts = re.split(r';|&&|\|\|', command)
        for part in parts:
            if part.strip():
                reason = _terminal_reason(role, part.strip(), home)
                if reason:
                    return reason
        return None
    if SHELL_CONTROL.search(command):
        return 'shell pipelines, command chaining, redirection, and inline shell code belong to main'
    if PRIVILEGED_COMMAND.search(command):
        return 'system administration, installation, deployment, deletion, or permission changes belong to main'
    if role == 'builder':
        # Best-effort and lexical: builder can still run Python it writes, so this is not a sandbox.
        text = command.replace('\\', '/').lower()
        if SECRET_NAMES.search(command) or HERMES_HOME_REF.search(text) \
                or str(_install_of(home)).replace('\\', '/').lower() in text \
                or any('herm' in g or '_api' in g for g in HERMES_GLOB.findall(text)):
            return 'Hermes configuration and credentials are administered by main'
        return None
    try:
        raw = shlex.split(command, posix=False)
    except ValueError:
        return 'the command could not be parsed'
    words = [word.strip('\"\'') for word in raw]
    if words and Path(words[0]).stem.lower() == 'canvas':
        if role == 'cowsearcher' and len(words) > 1 and words[1] in {'list_courses', 'list_assignments'}:
            return None
    if role == 'cron':
        python = bool(words) and PYTHON_EXE.match(words[0]) is not None
        if len(words) >= 3 and python and not SHELL_EXPANSION.search(words[1]):
            script = Path(words[1]).resolve()
            if script == (home / 'scripts' / 'workspace_api.py').resolve():
                if words[2:] == ['--clock']:
                    return None
                if len(words) == 4 and words[2] == '--request-file':
                    return _request_file_reason(words[3])
            expected = home / 'skills' / 'productivity' / 'google-workspace' / 'scripts' / 'google_api.py'
            if len(words) >= 4 and script == expected.resolve():
                service, operation, args = words[2], words[3], words[4:]
                # Invites email third parties (any --att* prefix of --attendees), so they stay main-owned.
                if operation not in CRON_GOOGLE_ROUTINE.get(service, set()) or any(_expands(w) for w in raw[2:]) \
                        or any(w.lower().startswith('--att') for w in args):
                    return GOOGLE_NON_ROUTINE
                if (service, operation) == ('drive', 'upload'):
                    return _local_file_reason(args[0] if args else '', home, writing=False)
                if (service, operation) == ('drive', 'download'):
                    return _download_reason(args, home)
                return None
        if words and Path(words[0]).stem.lower() == 'hermes':
            if words[1:] in (['status'], ['doctor'], ['--version']):
                return None
            if words[1:] in (['config', 'check'], ['gateway', 'status'], ['tools', 'list']):
                return None
            if len(words) >= 3 and words[1] in {'cron', 'sessions', 'kanban'} and words[2] in {'list', 'stats', 'show'}:
                return None
    return 'this terminal command exceeds the profile role; send the exact command to main'


def _queue_main_recovery(role, tool_name, session_id, message):
    """A scheduled/direct assignment has no worker card to notify its coordinator."""
    if not session_id:
        return None
    from tools.kanban_tools import _default_task_id
    if _default_task_id(None):
        return None
    from hermes_cli import kanban_db as kb
    from hermes_cli import kanban_db_connect as kbc
    cron = re.match(r'^cron_([a-zA-Z0-9]+)_', session_id)
    source = 'cron:' + cron[1] if cron else 'session:' + session_id
    prefix = _recovery_key(role, source)
    body = (
        f'Administrative recovery requested by {role}. Source profile: {role}; '
        f'source session: {session_id}; source identifier: {source}; blocked tool: {tool_name}.\n'
        f'{message}\n\n'
        'This is a recovery assignment for main: inspect the source session/job to recover the '
        'actual user request and exact intended step. Perform the privileged prerequisite directly '
        'with main permissions; do not send that same denied step back to a specialist. '
        'For recurring jobs, correct the job or install a narrowly scoped trusted helper so future '
        'runs can finish without repeating the same permission request. Preserve working state, '
        'As a main Kanban worker, use the unrestricted terminal and Hermes CLI for administrative '
        'actions on other cards; native orchestrator-only model tools are unavailable in workers. '
        'verify the result, and report through the original configured route. If Google consent or '
        'another external boundary requires the user, stop once with the precise dependency. '
        'This card has 300s for the prerequisite repair only; if full takeover is needed, create '
        'or claim a separate takeover card with a longer runtime instead of doing it here. '
        'The blocked command, credentials, file content, and OAuth codes are intentionally not copied here.'
    )
    with kbc.connect_closing(board='default') as conn:
        # One open recovery owner per source; later blocks join it, but never a closed card.
        # Prefix match on the role+source key over any open status; hex fingerprint holds no LIKE wildcards.
        existing = conn.execute(
            "SELECT id FROM tasks WHERE idempotency_key LIKE ? AND status NOT IN ('done','archived','cancelled')",
            (prefix + '%',)).fetchone()
        if existing:
            return existing['id']
        now = datetime.now(timezone.utc)
        key = _recovery_key(role, source, now)
        # Any card still holding this minute key is closed; a finer suffix keeps the new card distinct.
        if conn.execute('SELECT 1 FROM tasks WHERE idempotency_key = ?', (key,)).fetchone():
            key += now.strftime('%S%f')
        return kb.create_task(
            conn, title=f'Main recovery: {role} needs permission for {tool_name}',
            body=body, assignee='main', created_by=f'{role}:profile-permissions',
            board='default', workspace_kind='scratch', session_id=session_id,
            idempotency_key=key,
            max_retries=1, max_runtime_seconds=300,
        )


def _recovery_key(role, source, now=None):
    """Prefix per role+source; a minute suffix makes each new card distinct from closed ones."""
    key = 'profile-permission:' + hashlib.sha256((role + ':' + source).encode()).hexdigest()[:24]
    return key + now.strftime(':%Y%m%dT%H%MZ') if now else key


def make_guard(role, home):
    home = Path(home).resolve()

    def decide(tool_name, args, **kwargs):
        if role == 'main':
            return None
        args = args or {}
        allowed = ROLE_TOOLSETS.get(role)
        if allowed is None:
            return _blocked(role, 'this profile has no approved specialist role')
        if tool_name in {'delegate_task', 'execute_code', 'send_message', 'message_agent', 'clarify'}:
            return _blocked(role, 'delegation, arbitrary code execution, and direct messaging are reserved for main')
        if tool_name.startswith('kanban_') and tool_name not in WORKER_KANBAN:
            return _blocked(role, 'only main creates, reassigns, or restarts team work')
        if tool_name in {'request_toolset', 'tool_search'}:
            requested = args.get('toolsets') or []
            if isinstance(requested, str):
                requested = [requested]
            if any(name not in allowed for name in requested):
                return _blocked(role, 'requested tools exceed the profile role')
            return None
        if tool_name == 'terminal':
            reason = _terminal_reason(role, args.get('command'), home)
            return _blocked(role, reason) if reason else None
        if tool_name == 'process_manage' and args.get('action') not in {'list', 'status', 'poll', 'tail', 'wait', 'log'}:
            return _blocked(role, 'process termination and process ownership changes are administered by main')
        if tool_name == 'manage_connections':
            if str(args.get('action') or 'status').lower() != 'status':
                return _blocked(role, 'connection installation and account authorization are administered by main')
            return None
        if tool_name in {'read_file', 'search_files', 'write_file', 'patch'}:
            writing = tool_name in {'write_file', 'patch'}
            if role == 'cowsearcher' and writing:
                return _blocked(role, 'research is read-only; return the findings to main')
            for path in _paths(args):
                if SECRET_NAMES.search(str(path)):
                    return _blocked(role, 'direct access to credential files is reserved for main; use the installed API wrapper')
                if role != 'lib' and MEMORY_NAMES.search(str(path)):
                    return _blocked(role, 'durable memory is owned by lib through main')
                if writing and _protected(path, role, home):
                    return _blocked(role, 'Hermes configuration, plugins, and installed scripts are maintained by main')
                if writing and re.match(r'(?i)^[A-Z]:[\\/]Windows(?:[\\/]|$)|^[A-Z]:[\\/]Program Files', str(path)):
                    return _blocked(role, 'system files are maintained by main')
            return None
        if tool_name == 'skill_manage' and args.get('action') not in {'list', 'view', 'read'}:
            return _blocked(role, 'main reviews and applies persistent skill changes')
        if tool_name == 'memory' and str(args.get('action') or '').lower() in {
                'delete', 'clear', 'reset', 'remove', 'forget', 'purge', 'prune'}:
            return _blocked(role, 'destructive memory changes require main')
        if tool_name == 'second_brain_search' and role == 'lib':
            return None
        if role in {'builder', 'cowsearcher'} and tool_name.startswith('mcp__github__'):
            operation = tool_name.removeprefix('mcp__github__')
            if operation.startswith(('get_', 'list_', 'search_')) or operation in {'pull_request_read', 'issue_read'}:
                return None
            return _blocked(role, 'GitHub mutations are performed by main')
        if role in {'builder', 'cowsearcher'} and tool_name.startswith('mcp__firecrawl__'):
            operation = tool_name.removeprefix('mcp__firecrawl__')
            if operation in {'firecrawl_scrape', 'firecrawl_search', 'firecrawl_map'}:
                return None
            return _blocked(role, 'this external crawl operation needs main')
        from tools.registry import registry
        toolset = registry.get_toolset_for_tool(tool_name)
        if toolset not in allowed:
            return _blocked(role, f'tool {tool_name} is outside the assigned toolsets')
        return None

    def guard(tool_name, args, **kwargs):
        result = decide(tool_name, args, **kwargs)
        if result and result.get('action') == 'block':
            # Never log command text or args; they may hold secrets.
            entry = {'ts': datetime.now(timezone.utc).isoformat(), 'role': role,
                     'tool': tool_name, 'reason': result.pop('reason', '')}
            try:
                (home / 'state').mkdir(parents=True, exist_ok=True)
                with open(home / 'state' / 'permission_blocks.jsonl', 'a', encoding='utf-8') as log:
                    log.write(json.dumps(entry) + '\n')
            except OSError:
                pass
            try:
                task_id = _queue_main_recovery(role, tool_name, kwargs.get('session_id', ''), result['message'])
                if task_id:
                    result['message'] += f' Main recovery task {task_id} is already queued; do not create a duplicate.'
            except Exception as exc:
                result['message'] += f' Automatic recovery queue unavailable ({type(exc).__name__}); return this blocker to main once.'
        return result

    return guard


def register(ctx):
    from hermes_constants import get_hermes_home
    home = get_hermes_home()
    ctx.register_hook('pre_tool_call', make_guard(home.name, home))
