"""Summarise a CSV of sales rows by region."""
from __future__ import annotations

import argparse
import csv
import io
from collections import defaultdict


def summarize(rows: list[dict[str, str]]) -> list[tuple[str, float]]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[row["region"]] += float(row["amount"])
    return sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))


def read_rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def format_report(pairs: list[tuple[str, float]]) -> str:
    return "\n".join(f"{name}\t{total:.2f}" for name, total in pairs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args()
    with open(args.path, encoding="utf-8") as handle:
        pairs = summarize(read_rows(handle.read()))
    print(format_report(pairs))


if __name__ == "__main__":
    main()
