from __future__ import annotations

import argparse
import sys

from .core import (
    VaultError,
    atomic_new_file,
    build_index,
    capture_note,
    index_status,
    render_dossier,
    resolve_index_path,
    resolve_vault,
    retrieve_index,
    safe_output_path,
    search_markdown,
)
from .semantic import semantic_retrieve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="second-brain", description="Local-first Obsidian vault tools."
    )
    parser.add_argument("--vault", help="Path to an existing Obsidian vault.")
    parser.add_argument("--index", help="SQLite retrieval index path (must be outside the vault).")
    commands = parser.add_subparsers(dest="command")
    search = commands.add_parser("search", help="Search Markdown notes.")
    search.add_argument("terms", nargs="+", help="Case-insensitive terms to match.")
    capture = commands.add_parser("capture", help="Capture an inbox note.")
    capture.add_argument("text", help="Text to capture.")
    dossier = commands.add_parser("dossier", help="Draft a cited synthesis.")
    dossier.add_argument("terms", nargs="+", help="Case-insensitive terms to match.")
    dossier.add_argument("--output", help="New .md path relative to the vault; prints if omitted.")
    commands.add_parser(
        "index", aliases=["index-refresh"], help="Build or update the local SQLite retrieval index."
    )
    commands.add_parser("index-status", help="Report whether the local index is missing, current, or stale.")
    retrieve = commands.add_parser("retrieve", aliases=["search-index"], help="Rank indexed Markdown chunks.")
    retrieve.add_argument("terms", nargs="*", help="Terms to match in the local index.")
    retrieve.add_argument("--limit", type=int, default=10, help="Maximum results to return (default: 10).")
    semantic = commands.add_parser(
        "semantic-retrieve",
        help="Opt-in local vector retrieval; requires an explicit local provider.",
    )
    semantic.add_argument("terms", nargs="+", help="Query text for local semantic retrieval.")
    semantic.add_argument(
        "--provider",
        help="Explicit local semantic provider (local-hash or sentence-transformers).",
    )
    semantic_model = semantic.add_mutually_exclusive_group()
    semantic_model.add_argument(
        "--model-path",
        help="Existing local sentence-transformers model directory (no download is attempted).",
    )
    semantic_model.add_argument(
        "--model",
        help="Explicit locally cached sentence-transformers model identifier (no download is attempted).",
    )
    semantic.add_argument("--limit", type=int, default=10, help="Maximum results to return (default: 10).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        vault = resolve_vault(args.vault)
        if args.command == "search":
            for path, line_number, line in search_markdown(vault, args.terms):
                print(f"{path.relative_to(vault).as_posix()}:{line_number}: {line}")
            return 0
        if args.command in {"index", "index-refresh"}:
            index = resolve_index_path(args.index, vault)
            updated, removed = build_index(vault, index)
            print(f"Indexed {updated} note(s); removed {removed} stale note(s): {index}")
            return 0
        if args.command == "index-status":
            index = resolve_index_path(args.index, vault)
            print(f"{index_status(vault, index)}: {index}")
            return 0
        if args.command in {"retrieve", "search-index"}:
            index = resolve_index_path(args.index, vault)
            if args.limit < 1:
                raise ValueError("Result limit must be at least 1.")
            for rank, (score, source_path, start_line, end_line, content) in enumerate(
                retrieve_index(index, args.terms, args.limit), start=1
            ):
                print(f"{rank}. score={score:.4f} {source_path}:{start_line}-{end_line}")
                print(content)
            return 0
        if args.command == "semantic-retrieve":
            index = resolve_index_path(args.index, vault)
            for rank, result in enumerate(
                semantic_retrieve(
                    index,
                    " ".join(args.terms),
                    args.provider,
                    args.limit,
                    model_path=args.model_path,
                    model_name=args.model,
                ),
                start=1,
            ):
                print(
                    f"{rank}. provider={args.provider} score={result.score:.4f} "
                    f"{result.source_path}:{result.start_line}-{result.end_line}"
                )
                print(result.content)
            return 0
        if args.command == "capture":
            print(capture_note(vault, args.text))
            return 0
        if args.command == "dossier":
            dossier = render_dossier(vault, args.terms)
            if args.output:
                output = safe_output_path(vault, args.output)
                atomic_new_file(output, dossier)
                print(output)
            else:
                print(dossier, end="")
            return 0
        parser.error(f"{args.command} is not implemented")
    except (VaultError, ValueError, FileExistsError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
