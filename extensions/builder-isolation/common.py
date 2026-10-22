"""Bounded, regular-file-only workspace exchange. No Hermes imports."""
import base64
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import tarfile

MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 5000
SKIP_DIRS = {'.git', '.hermes', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache'}
SECRET_NAMES = {'auth.json', 'credentials.json', 'token.json', 'google_token.json', 'google_client_secret.json'}


def allowed(name):
    p = PurePosixPath(name)
    return (not p.is_absolute() and str(p) == name and '..' not in p.parts
            and '\\' not in name and ':' not in name and bool(p.parts)
            and not any(part in SKIP_DIRS or part.startswith('.env') for part in p.parts)
            and p.name.lower() not in SECRET_NAMES
            and not p.name.lower().endswith(('_token.json', '_client_secret.json', '.pem', '.key')))


def files(root):
    root = Path(root).resolve()
    found = {}
    total = 0
    for parent, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if allowed((Path(parent) / d).relative_to(root).as_posix())
                   and not (Path(parent) / d).is_symlink()]
        for name in names:
            p = Path(parent) / name
            rel = p.relative_to(root).as_posix()
            if not allowed(rel) or p.is_symlink() or not p.is_file():
                continue
            size = p.stat().st_size
            total += size
            if total > MAX_BYTES or len(found) >= MAX_FILES:
                raise ValueError('Selected workspace exceeds the 64 MiB / 5000-file isolation transfer limit.')
            data = p.read_bytes()
            if len(data) != size:
                raise ValueError('Workspace changed during snapshot; retry after stopping concurrent edits.')
            found[rel] = data
    return found


def modes(root, items):
    return {name: (target_path(root, name).stat().st_mode & 0o111) | 0o644 for name in items}


def pack(items, file_modes=None):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w:gz') as archive:
        for name, data in sorted(items.items()):
            if not allowed(name):
                raise ValueError('Disallowed archive path')
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = (int((file_modes or {}).get(name, 0o644)) & 0o111) | 0o644
            archive.addfile(info, io.BytesIO(data))
    return base64.b64encode(out.getvalue()).decode('ascii')


def unpack(encoded, file_modes=None):
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) > MAX_BYTES + 1024 * 1024:
        raise ValueError('Compressed workspace exceeds limit')
    result, total = {}, 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for member in archive:
            if not member.isfile() or not allowed(member.name) or member.name in result:
                raise ValueError('Unsafe, duplicate, linked, or non-file archive entry')
            total += member.size
            if total > MAX_BYTES or len(result) >= MAX_FILES or member.size < 0:
                raise ValueError('Unpacked workspace exceeds limit')
            result[member.name] = archive.extractfile(member).read()
            if file_modes is not None:
                file_modes[member.name] = (member.mode & 0o111) | 0o644
    return result


def target_path(root, name):
    if not allowed(name):
        raise ValueError('Disallowed result path')
    root = Path(root).resolve()
    current = root
    for part in PurePosixPath(name).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Result path traverses a symbolic link')
    if not current.resolve().is_relative_to(root):
        raise ValueError('Result escapes selected workspace')
    return current


def materialize(root, items, file_modes=None):
    for name, data in items.items():
        target = target_path(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod((int((file_modes or {}).get(name, 0o644)) & 0o111) | 0o644)


def apply_result(root, before, after, backup, before_modes=None, after_modes=None):
    changed = {n for n in after if before.get(n) != after[n]}
    if before_modes is not None and after_modes is not None:
        changed.update(n for n in after if before_modes.get(n) != after_modes.get(n))
    removed = set(before) - set(after)
    for name in changed | removed:
        target = target_path(root, name)
        if target.exists() and not target.is_file():
            raise ValueError('Result destination is not a regular file')
        current = target.read_bytes() if target.is_file() else None
        if current != before.get(name):
            raise ValueError('Concurrent workspace edits conflict with Builder output; retained result for recovery.')
        if current is not None and before_modes is not None:
            current_mode = (target.stat().st_mode & 0o111) | 0o644
            if current_mode != before_modes.get(name):
                raise ValueError('Concurrent workspace mode changes conflict with Builder output.')
    backup = Path(backup)
    backup.mkdir(parents=True, exist_ok=False)
    original = {n: before[n] for n in changed | removed if n in before}
    materialize(backup, original, before_modes)
    for name in sorted(changed):
        target = target_path(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name('.' + target.name + '.isolated-new')
        if temp.exists() or temp.is_symlink():
            raise ValueError('Temporary result destination already exists')
        try:
            temp.write_bytes(after[name])
            temp.chmod((int((after_modes or {}).get(name, 0o644)) & 0o111) | 0o644)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
    for name in sorted(removed):
        target_path(root, name).unlink()
    return {'changed_files': sorted(changed), 'deleted_files': sorted(removed),
            'result_sha256': {n: hashlib.sha256(after[n]).hexdigest() for n in sorted(changed)}}
