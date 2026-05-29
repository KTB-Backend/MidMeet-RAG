"""Command-line entrypoint for indexing seed records into Chroma."""

from __future__ import annotations

import argparse
from pathlib import Path

from rag_core.embedder import SnowflakeArcticEmbedAdapter
from rag_core.indexer import DEFAULT_CHROMA_PATH, ChromaIndexResult, index_seed_records
from rag_core.loader import load_seed_directory


DEFAULT_SEED_DIR = "data/seeds/processed/"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-dir",
        default=DEFAULT_SEED_DIR,
        help="Directory containing validated seed JSON files.",
    )
    args = parser.parse_args(argv)

    records = load_seed_directory(Path(args.seed_dir))
    result = index_seed_records(records, SnowflakeArcticEmbedAdapter())
    _print_result(result)
    return 0


def _print_result(result: ChromaIndexResult) -> None:
    print(f"collection={result.collection_name}")
    print(f"path={result.chroma_path or DEFAULT_CHROMA_PATH}")
    print(f"indexed_count={result.indexed_count}")
    print(f"collection_count={result.collection_count}")
    if result.used_legacy_hnsw_config:
        print("hnsw_configuration=legacy_metadata")


if __name__ == "__main__":
    raise SystemExit(main())
