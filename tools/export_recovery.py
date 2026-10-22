"""Export a private, verified archive outside Docker storage; no remote upload.

Requires an existing owner-restricted output directory. Invoke from an owner
Windows scheduled task. Keep this tool and the deployment configuration locally.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


def run(*args):
    return subprocess.run(['docker', *args], check=True, capture_output=True, text=True, encoding='utf-8', timeout=900).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--deployment', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_dir():
        parser.error('Create and restrict output directory access before exporting')
    name = 'hermes-recovery-export'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    destination = args.output / ('recovery-' + stamp + '.zip')
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('recovery_backup', root / 'extensions/operations/recovery_backup.py')
    backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup)
    image = json.loads(run('inspect', 'hermes'))[0]['Image']
    # SQLite's read-only connection may initialize WAL shared-memory sidecars.
    # Inherit data volume write access for that purpose; connections use mode=ro
    # and backup() rather than immutable=1, which could silently omit live WAL.
    # Main must be last: the Builder image also declares an anonymous /opt/data.
    command = ['run', '--name', name, '--network', 'none', '--cpus', '1', '--memory', '768m', '--volumes-from', 'hermes-builder', '--volumes-from', 'hermes', '--entrypoint', '/opt/hermes/.venv/bin/python', image, '/opt/data/profiles/cron/scripts/recovery_backup.py', '--root', 'data=/opt/data', '--root', 'projects=/projects', '--root', 'builder=/builder-home', '--root', 'workspaces=/workspaces', '--root', 'isolation=/opt/isolation', '--archive', '/tmp/recovery.zip']
    # A fixed helper name prevents concurrent exports; never remove a helper
    # we did not create. A failed prior helper requires explicit inspection.
    existing = run('ps', '-a', '--format', '{{.Names}}').splitlines()
    if name in existing:
        raise RuntimeError('Existing export helper requires inspection')
    try:
        run(*command)
        run('cp', name + ':/tmp/recovery.zip', str(destination))
        checked = backup.verify(destination)
        # Deployment files may include secrets. Keep them ONLY in the private
        # output folder, alongside the archive, never in the Git repository.
        import shutil
        config = args.output / ('deployment-' + stamp)
        shutil.copytree(args.deployment, config, ignore=shutil.ignore_patterns('backups', '*.log', '__pycache__'))
        record = {'ok': True, 'archive': destination.name, 'sha256': backup.digest(destination), 'verified_at_epoch': __import__('time').time(), 'restore_test': checked, 'deployment': config.name}
        backup.write_json(args.output / 'export-status.json', record)
        run('cp', str(args.output / 'export-status.json'), 'hermes:/opt/data/state/host_backup_verification.json')
        # Retain seven verified export generations. Never prune before a new
        # successful restore test. Deployment definitions remain for rollback.
        for old in sorted(args.output.glob('recovery-*.zip'), reverse=True)[7:]:
            if old.resolve().parent != args.output.resolve():
                raise ValueError('Unexpected export retention path')
            old.unlink()
        print(json.dumps(record))
    except Exception as exc:
        backup.write_json(args.output / 'export-status.json', {'ok': False, 'error_type': type(exc).__name__})
        try:
            run('cp', str(args.output / 'export-status.json'), 'hermes:/opt/data/state/host_backup_verification.json')
        except Exception:
            pass  # Host status still records failure when Docker is unavailable.
        raise
    finally:
        # Helper is stopped after its foreground producer exits.
        run('rm', name)


if __name__ == '__main__':
    main()
