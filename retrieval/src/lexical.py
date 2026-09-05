"""Small, dependency-free V0/V1 lexical retriever.

V0 deliberately behaves like a bounded ``grep`` plus source reader.  V1
reuses the same bounded scan and adds deterministic identifier-aware scoring;
it is not intended to be a replacement for BM25 or a semantic index.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from pathlib import Path
from typing import Iterator


DEFAULT_EXTENSIONS = {".go", ".py", ".js", ".ts", ".java", ".rs", ".md", ".json", ".yaml", ".yml"}
DEFAULT_EXCLUDED_DIRS = {".git", ".hg", ".svn", "__pycache__", "node_modules", "vendor", ".venv"}
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
SYMBOL_RE = re.compile(
    r"^\s*(?:func\s+(?:\([^)]*\)\s*)?|(?:def|class|function)\s+|type\s+|const\s+|var\s+|interface\s+|struct\s+)([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


@dataclass(frozen=True)
class SearchResult:
    path: str
    score: float
    matched_lines: tuple[int, ...]
    symbols: tuple[str, ...]
    matched_fields: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def tokenize_identifier(value: str) -> list[str]:
    """Split paths and code identifiers into comparable lowercase tokens."""

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
    return [token.lower() for token in TOKEN_RE.findall(value)]


def _iter_files(root: Path, extensions: set[str], max_files: int) -> Iterator[Path]:
    count = 0
    for directory in (root, *[p for p in root.rglob("*") if p.is_dir()]):
        if any(part in DEFAULT_EXCLUDED_DIRS for part in directory.relative_to(root).parts):
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.lower() in extensions:
                yield path
                count += 1
                if count >= max_files:
                    return


def _read_bounded(path: Path, max_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def search_text(root: Path, query: str, *, max_files: int = 500, max_bytes: int = 1_000_000,
                max_matches: int = 100) -> list[dict]:
    """V0: return bounded, line-oriented text matches in deterministic order."""

    needle = query.casefold()
    results: list[dict] = []
    for path in _iter_files(root, DEFAULT_EXTENSIONS, max_files):
        content = _read_bounded(path, max_bytes)
        if content is None:
            continue
        lines = [number for number, line in enumerate(content.splitlines(), 1) if needle in line.casefold()]
        if lines:
            results.append({"path": path.relative_to(root).as_posix(), "matched_lines": lines[:max_matches]})
            if sum(len(item["matched_lines"]) for item in results) >= max_matches:
                break
    return results


def read_source(root: Path, relative_path: str, *, start_line: int = 1, end_line: int | None = None,
                max_bytes: int = 1_000_000) -> dict:
    """Read a bounded source range and reject paths escaping ``root``."""

    root = root.resolve()
    path = (root / relative_path).resolve()
    if path != root and root not in path.parents:
        raise ValueError("source path escapes repository root")
    content = _read_bounded(path, max_bytes)
    if content is None:
        raise OSError(f"cannot read bounded source file: {relative_path}")
    lines = content.splitlines()
    start = max(1, start_line)
    end = min(len(lines), end_line or len(lines))
    return {"path": path.relative_to(root).as_posix(), "start_line": start, "end_line": end,
            "content": "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1))}


class LexicalRetriever:
    """V1 path/symbol/identifier-aware lexical search."""

    def __init__(self, root: Path, *, max_files: int = 500, max_bytes: int = 1_000_000):
        self.root = Path(root).resolve()
        self.max_files = max_files
        self.max_bytes = max_bytes

    def search(self, query: str, *, top_k: int = 10) -> list[SearchResult]:
        query_tokens = set(tokenize_identifier(query))
        results: list[SearchResult] = []
        for path in _iter_files(self.root, DEFAULT_EXTENSIONS, self.max_files):
            content = _read_bounded(path, self.max_bytes)
            if content is None:
                continue
            relative = path.relative_to(self.root).as_posix()
            symbols = tuple(SYMBOL_RE.findall(content))
            fields = {"path": set(tokenize_identifier(relative)),
                      "symbol": set(token for symbol in symbols for token in tokenize_identifier(symbol)),
                      "identifier": set(tokenize_identifier(content))}
            matched = tuple(name for name, tokens in fields.items() if query_tokens & tokens)
            if not matched:
                continue
            score = (4.0 * len(query_tokens & fields["path"]) +
                     6.0 * len(query_tokens & fields["symbol"]) +
                     1.0 * len(query_tokens & fields["identifier"]))
            lines = tuple(number for number, line in enumerate(content.splitlines(), 1)
                          if query.casefold() in line.casefold())
            results.append(SearchResult(relative, score, lines[:20], symbols, tuple(matched)))
        return sorted(results, key=lambda item: (-item.score, item.path))[:top_k]
