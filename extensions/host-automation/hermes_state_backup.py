"""Create a rolling, non-secret Hermes state backup."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, shutil, sqlite3, tempfile, time, zipfile
from contextlib import closing
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData/Local/hermes"))
OUT = HOME / "backups"
KEEP_DAILY, KEEP_WEEKLY, KEEP_MONTHLY = 7, 4, 3
VOLATILE_NAMES = {".tick.lock", ".jobs.lock"}
VOLATILE_SUFFIXES = {"-wal", "-shm"}

def sqlite_snapshot(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    src_uri = f"file:{src.as_posix()}?mode=ro"
    with closing(sqlite3.connect(src_uri, uri=True)) as source, closing(sqlite3.connect(dst)) as target:
        with target:
            source.backup(target)
    with closing(sqlite3.connect(f"file:{dst.as_posix()}?mode=ro", uri=True)) as check:
        result = check.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {src}")

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def manifest_for(root: Path) -> dict:
    files = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        record = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        if path.suffix.lower() == ".db":
            with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as conn:
                record["sqlite_user_version"] = int(conn.execute("PRAGMA user_version").fetchone()[0])
        files[path.relative_to(root).as_posix()] = record
    return {
        "format": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_home": str(HOME),
        "files": files,
    }

def verify_archive(archive: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="hermes-restore-test-") as td:
        restored = Path(td)
        with zipfile.ZipFile(archive) as z:
            bad_member = z.testzip()
            if bad_member:
                raise RuntimeError(f"ZIP CRC verification failed for {bad_member}")
            z.extractall(restored)
        manifest = json.loads((restored / "manifest.json").read_text(encoding="utf-8"))
        for rel, expected in manifest["files"].items():
            path = restored / rel
            if not path.is_file() or sha256(path) != expected["sha256"]:
                raise RuntimeError(f"Restore verification failed for {rel}")
            if path.suffix.lower() == ".db":
                with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as conn:
                    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError(f"Restored SQLite integrity failed for {rel}")

def retention_keep(paths: list[Path]) -> set[Path]:
    """Select newest archives in 7 daily, 4 weekly, and 3 monthly buckets."""
    keep: set[Path] = set()
    buckets = (("daily", KEEP_DAILY), ("weekly", KEEP_WEEKLY), ("monthly", KEEP_MONTHLY))
    for kind, limit in buckets:
        seen = set()
        for path in sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True):
            when = dt.datetime.fromtimestamp(path.stat().st_mtime)
            key = when.date() if kind == "daily" else when.strftime("%G-%V") if kind == "weekly" else when.strftime("%Y-%m")
            if key in seen:
                continue
            seen.add(key)
            keep.add(path)
            if len(seen) >= limit:
                break
    return keep

def is_volatile(path: Path) -> bool:
    name = path.name
    return (
        name in VOLATILE_NAMES
        or (name.startswith(".fire-") and name.endswith(".lock"))
        or any(name.endswith(suffix) for suffix in VOLATILE_SUFFIXES)
    )

def copy_state_tree(src: Path, dst: Path) -> None:
    """Copy durable state without live locks or inconsistent SQLite sidecars."""
    for path in src.rglob("*"):
        if is_volatile(path):
            continue
        target = dst / path.relative_to(src)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            if path.suffix.lower() == ".db":
                sqlite_snapshot(path, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = OUT / f"hermes-{stamp}.zip"
    partial = OUT / f".{archive.name}.partial"
    with tempfile.TemporaryDirectory(prefix="hermes-backup-") as td:
        root = Path(td)
        (root / "config.yaml").write_bytes((HOME / "config.yaml").read_bytes())
        meta = []
        env = HOME / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    meta.append(line.split("=", 1)[0].strip())
        (root / "env.metadata.json").write_text(json.dumps({"keys": sorted(set(meta))}, indent=2), encoding="utf-8")
        state = HOME / "state.db"
        if state.exists(): sqlite_snapshot(state, root / "state.db")
        for name in ("cron", "skills", "scripts"):
            src = HOME / name
            if src.exists(): copy_state_tree(src, root / name)
        (root / "manifest.json").write_text(
            json.dumps(manifest_for(root), indent=2, sort_keys=True), encoding="utf-8"
        )
        partial.unlink(missing_ok=True)
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as z:
            for path in root.rglob("*"):
                if path.is_file(): z.write(path, path.relative_to(root))
        os.replace(partial, archive)

    state_root = HOME.parent.parent if HOME.parent.name.lower() == "profiles" else HOME
    verify_state = state_root / "state" / "backup_verification.json"
    verify_state.parent.mkdir(parents=True, exist_ok=True)
    previous = {}
    try:
        previous = json.loads(verify_state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    last_verified = float(previous.get("verified_at_epoch") or 0)
    # Verify immediately on first use and at least weekly thereafter.
    if not last_verified or time.time() - last_verified >= 7 * 86400:
        verify_archive(archive)
        verify_state.write_text(json.dumps({
            "ok": True,
            "archive": archive.name,
            "verified_at_epoch": time.time(),
            "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }, indent=2), encoding="utf-8")

    archives = list(OUT.glob("hermes-*.zip"))
    keep = retention_keep(archives) | {archive}
    for old in archives:
        if old not in keep:
            old.unlink()
    print(
        f"Hermes backup created atomically: {archive} "
        f"(retention {KEEP_DAILY} daily/{KEEP_WEEKLY} weekly/{KEEP_MONTHLY} monthly; secrets excluded)"
    )

if __name__ == "__main__": main()
