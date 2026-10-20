"""Validate a reviewed snapshot; install only into explicitly selected new profiles.

Standard library only. No network calls, credential copying, gateway startup,
plugin loading, alias creation, or scheduled-job activation.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil


PAYLOAD_ROOTS = {'profiles', 'extensions', 'reference', 'examples'}
PRIVATE_PARTS = {'memories', 'vault', 'sessions', 'logs', 'cache', 'state', '__pycache__', 'node_modules', 'backups'}
PRIVATE_NAMES = {'auth.json', 'credentials.json', 'token.json', 'jobs.json', 'state.db', 'gateway_state.json', 'discord_threads.json', 'channel_directory.json'}


def load_bundle(root):
    root = root.resolve()
    data = json.loads((root / 'bundle-manifest.json').read_text(encoding='utf-8'))
    names, files = data['profiles'], data['files']
    if not names or len(set(names)) != len(names) or any(not re.fullmatch(r'[a-z][a-z0-9_-]*', n) for n in names):
        raise ValueError('Invalid profile roster')
    for rel, digest in files.items():
        path = PurePosixPath(rel)
        if (path.is_absolute() or '\\' in rel or ':' in rel or str(path) != rel
                or '..' in path.parts or not path.parts or path.parts[0] not in PAYLOAD_ROOTS
                or any(part.startswith('.') or part in PRIVATE_PARTS for part in path.parts)
                or path.name in PRIVATE_NAMES or path.suffix in {'.db', '.sqlite', '.sqlite3', '.jsonl', '.pyc'}):
            raise ValueError('Disallowed payload path: ' + rel)
        file = root / rel
        if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in [file, *file.parents] if p != root.parent):
            raise ValueError('Linked payload paths are not supported: ' + rel)
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError('Missing or modified payload: ' + rel)
    actual = set()
    for directory in PAYLOAD_ROOTS:
        if (root / directory).exists():
            actual.update(f.relative_to(root).as_posix() for f in (root / directory).rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    if actual != set(files):
        raise ValueError('Payload files do not exactly match the manifest')
    for name in names:
        for leaf in ['config.yaml', 'SOUL.md', 'profile.yaml']:
            if f'profiles/{name}/{leaf}' not in files:
                raise ValueError('Incomplete profile: ' + name)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('validate')
    install = commands.add_parser('install')
    install.add_argument('--target', type=Path, required=True, help='Hermes data ROOT, not an individual profile home')
    install.add_argument('--profiles', nargs='+', required=True)
    install.add_argument('--with-skills', action='store_true', help='Opt in to reviewed skill code and documentation')
    args = parser.parse_args()
    try:
        data = load_bundle(args.root)
        if args.command == 'validate':
            print(json.dumps({'status': 'PASS', 'profiles': data['profiles'], 'payload_files': len(data['files'])}))
            return
        if len(set(args.profiles)) != len(args.profiles) or any(n not in data['profiles'] for n in args.profiles):
            raise ValueError('Select distinct profile names from the bundle roster')
        target = args.target.absolute()
        for p in [target, target / 'profiles', *target.parents]:
            if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
                raise ValueError('Linked target paths are not supported')
        for name in args.profiles:
            dest = target / 'profiles' / name
            if dest.exists() or dest.is_symlink():
                raise ValueError('Refusing to overwrite an existing profile: ' + name)
        for name in args.profiles:
            dest = target / 'profiles' / name
            dest.mkdir(parents=True, exist_ok=False)
            for filename in ['config.yaml', 'SOUL.md', 'profile.yaml']:
                shutil.copyfile(args.root / 'profiles' / name / filename, dest / filename)
            if args.with_skills:
                prefix = f'profiles/{name}/skills/'
                for rel in data['files']:
                    if rel.startswith(prefix):
                        skill_dest = target / rel
                        skill_dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(args.root / rel, skill_dest)
        print(json.dumps({'installed': args.profiles, 'gateway_started': False, 'schedules_activated': False}))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
