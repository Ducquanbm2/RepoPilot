"""Command line interface for V0 and V1 retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .lexical import LexicalRetriever, read_source, search_text


def main() -> int:
    parser = argparse.ArgumentParser(description="RepoPilot bounded code retrieval")
    parser.add_argument("root", type=Path)
    parser.add_argument("query")
    parser.add_argument("--variant", choices=("v0", "v1"), default="v1")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--max-files", type=int, default=500)
    parser.add_argument("--read", metavar="PATH", help="read one source file instead of searching")
    parser.add_argument("--start-line", type=int, default=1)
    parser.add_argument("--end-line", type=int)
    args = parser.parse_args()
    if args.read:
        output = read_source(args.root, args.read, start_line=args.start_line, end_line=args.end_line)
    elif args.variant == "v0":
        output = search_text(args.root, args.query, max_files=args.max_files, max_matches=args.top_k)
    else:
        output = [result.to_dict() for result in LexicalRetriever(args.root, max_files=args.max_files).search(args.query, top_k=args.top_k)]
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
