"""Private recovery archives. Contains credentials: never upload to GitHub.

SQLite databases use online backup; cross-database/application transactions are
not atomic. Stop all writers for a fully quiescent application checkpoint.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
import time
from datetime import datetime, timezone
from contextlib import closing
import zipfile

EXCLUDE = {'backups', 'audit-backups', '__pycache__', '.git', 'node_modules', '.cache', 'logs',
           'cache', 'lazy-packages', 'audio_cache', 'image_cache'}


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temp.chmod(0o600)
    temp.replace(path)


def snapshot(source, target):
    with source.open('rb') as stream:
        is_sqlite = stream.read(16) == b'SQLite format 3\x00'
    if not is_sqlite:
        shutil.copyfile(source, target)
        return False
    deadline = time.monotonic() + 120
    def progress(*_):
        if time.monotonic() > deadline:
            raise TimeoutError('SQLite snapshot deadline exceeded')
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst, pages=256, progress=progress)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Source SQLite integrity check failed')
    return True


def verify(archive):
    """Extract the complete archive, verify every hash, and reopen every SQLite DB."""
    with tempfile.TemporaryDirectory(prefix='hermes-restore-') as directory:
        root = Path(directory)
        with zipfile.ZipFile(archive) as z:
            if z.testzip():
                raise ValueError('Archive CRC failed')
            names = z.namelist()
            if len(names) != len(set(names)):
                raise ValueError('Duplicate archive member')
            for name in names:
                rel = PurePosixPath(name)
                if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
                    raise ValueError('Unsafe archive path')
            manifest = json.loads(z.read('manifest.json'))
            if set(names) != set(manifest['files']) | {'manifest.json'}:
                raise ValueError('Archive inventory differs from manifest')
            z.extractall(root)
        for rel, record in manifest['files'].items():
            path = root / rel
            if digest(path) != record['sha256']:
                raise ValueError('Restored hash mismatch')
            if record['sqlite']:
                with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('Restored SQLite integrity failed')
        return {'files': len(manifest['files']), 'databases': sum(v['sqlite'] for v in manifest['files'].values()), 'roots': manifest['roots']}


def create(roots, archive, status=None):
    archive = archive.resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise FileExistsError('Refusing to replace a recovery archive')
    partial = archive.with_suffix('.partial')
    try:
        with tempfile.TemporaryDirectory(prefix='hermes-snapshot-') as directory:
            stage = Path(directory)
            manifest = {'format': 1, 'created_at': datetime.now(timezone.utc).isoformat(), 'roots': {}, 'files': {}, 'symlinks': {}, 'excluded_directories': sorted(EXCLUDE)}
            for label, source in roots.items():
                source = Path(source).resolve()
                if not source.is_dir() or not label or '/' in label or label in ('.', '..'):
                    raise ValueError('Invalid or missing backup root')
                manifest['roots'][label] = str(source)
                for current, directories, files in os.walk(source, followlinks=False):
                    directories[:] = sorted(d for d in directories if d not in EXCLUDE)
                    for name in list(directories) + sorted(files):
                        path = Path(current) / name
                        rel = (Path(label) / path.relative_to(source)).as_posix()
                        if path.is_symlink():
                            manifest['symlinks'][rel] = os.readlink(path)
                            if name in directories:
                                directories.remove(name)
                            continue
                        mode = path.stat().st_mode
                        if not stat.S_ISREG(mode) or name.endswith(('-wal', '-shm', '.lock', '.partial')) or name.endswith('.sock'):
                            continue
                        target = stage / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        sql = snapshot(path, target)
                        manifest['files'][rel] = {'sha256': digest(target), 'sqlite': sql, 'mode': stat.S_IMODE(mode), 'bytes': target.stat().st_size}
            (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as z:
                for path in sorted(stage.rglob('*')):
                    if path.is_file():
                        z.write(path, path.relative_to(stage).as_posix())
        partial.chmod(0o600)
        checked = verify(partial)
        partial.replace(archive)
        result = {'ok': True, 'archive': archive.name, 'sha256': digest(archive), 'verified_at_epoch': time.time(), 'verified_at': datetime.now(timezone.utc).isoformat(), 'expires_at_epoch': time.time() + 36 * 3600, 'restore_test': checked, 'contains_secrets': True}
        if status:
            write_json(status, result)
        # Only archives made by this producer are eligible for pruning, and
        # only after the new archive was fully extracted and checked.
        if not roots.get('builder'):
            for old in sorted(archive.parent.glob('recovery-*.zip'), reverse=True)[7:]:
                if old.resolve().parent != archive.parent or old == archive:
                    continue
                old.unlink()
        return result
    except Exception as exc:
        partial.unlink(missing_ok=True)
        if status:
            write_json(status, {'ok': False, 'attempted_at_epoch': time.time(), 'error_type': type(exc).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', default=[], help='LABEL=ABSOLUTE_PATH')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--status', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify)))
        return
    if args.root:
        roots = dict(item.split('=', 1) for item in args.root)
    else:
        roots = {'data': '/opt/data', 'projects': '/projects'}
    archive = args.archive or Path('/opt/data/backups/state') / ('recovery-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '.zip')
    status = args.status if args.root or args.archive else Path('/opt/data/state/backup_verification.json')
    print(json.dumps(create(roots, archive, status)))


if __name__ == '__main__':
    main()
