#!/usr/bin/env python3
"""
find-amplification.py

Change amplification detector. Counts distinct files that reference a
given symbol, function name, variable name, or string literal. Use this
to measure how far a concept has leaked across a codebase before
proposing a consolidation.

Usage:
    python scripts/find-amplification.py --symbol <name> [--root <dir>] [--ext <ext>...]

Examples:
    python scripts/find-amplification.py --symbol serialize_user
    python scripts/find-amplification.py --symbol "column_name" --ext .py .sql
    python scripts/find-amplification.py --symbol AUTH_TOKEN --root ./src

Exit codes:
    0  Symbol found in < 3 files  (no amplification)
    1  Symbol found in 3-5 files  (moderate amplification — review recommended)
    2  Symbol found in 6+ files   (severe amplification — consolidation required)
    3  Usage error or invalid arguments
"""

import argparse
import os
import sys
from pathlib import Path


EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".mypy_cache"}
DEFAULT_EXTENSIONS = {".py", ".ts", ".js", ".go", ".java", ".rb", ".rs", ".cs", ".cpp", ".c", ".h"}


def resolve_root(raw: str) -> Path:
    root = Path(raw).resolve()
    if not root.exists():
        print(f"ERROR: Root path does not exist: {root}", file=sys.stderr)
        sys.exit(3)
    if not root.is_dir():
        print(f"ERROR: Root path is not a directory: {root}", file=sys.stderr)
        sys.exit(3)
    return root


def collect_files(root: Path, extensions: set[str]) -> list[Path]:
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories in-place so os.walk skips them
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in extensions:
                results.append(fpath)
    return results


def search_files(files: list[Path], symbol: str) -> list[tuple[Path, list[int]]]:
    """Return list of (file, [line_numbers]) for files containing the symbol."""
    matches = []
    for fpath in files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hit_lines = [
            i + 1
            for i, line in enumerate(text.splitlines())
            if symbol in line
        ]
        if hit_lines:
            matches.append((fpath, hit_lines))
    return matches


def classify_amplification(count: int) -> tuple[str, str]:
    if count < 3:
        return "NONE", "No amplification detected."
    elif count <= 5:
        return "MODERATE", "Moderate amplification. Review whether this concept needs a canonical owner."
    else:
        return "SEVERE", "Severe amplification. Consolidation strongly recommended."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure change amplification by counting files referencing a symbol.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--symbol", required=True, help="Symbol, name, or string literal to search for.")
    parser.add_argument("--root", default=".", help="Root directory to scan (default: current directory).")
    parser.add_argument(
        "--ext",
        nargs="+",
        default=None,
        metavar="EXT",
        help=f"File extensions to include (default: {sorted(DEFAULT_EXTENSIONS)}).",
    )

    args = parser.parse_args()

    symbol: str = args.symbol
    if not symbol.strip():
        print("ERROR: --symbol must be a non-empty string.", file=sys.stderr)
        sys.exit(3)

    root = resolve_root(args.root)
    extensions = set(args.ext) if args.ext else DEFAULT_EXTENSIONS

    # Normalise extensions: ensure each starts with a dot
    extensions = {e if e.startswith(".") else f".{e}" for e in extensions}

    files = collect_files(root, extensions)
    matches = search_files(files, symbol)

    level, summary = classify_amplification(len(matches))

    print(f"\nSymbol       : {symbol!r}")
    print(f"Scanned      : {len(files)} files  ({', '.join(sorted(extensions))})")
    print(f"References   : {len(matches)} file(s)")
    print(f"Amplification: {level}")
    print(f"Assessment   : {summary}")

    if matches:
        print("\nFiles referencing symbol:")
        for fpath, lines in sorted(matches, key=lambda x: str(x[0])):
            rel = fpath.relative_to(root)
            line_list = ", ".join(str(ln) for ln in lines[:10])
            suffix = f" (+{len(lines)-10} more)" if len(lines) > 10 else ""
            print(f"  {rel}  [lines: {line_list}{suffix}]")

    print()

    # Exit code encodes severity for scripting
    if level == "NONE":
        sys.exit(0)
    elif level == "MODERATE":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
