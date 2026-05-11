#!/usr/bin/env python3
"""Extract per-iteration scores from a PACEvolve controller log.

Completed iterations carry the score printed by the controller. Failed
compilation iterations are assigned score 0. Other failed iterations are also
reported with score 0 by default so the output always has a numeric score.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Iterable


FLOAT = r"-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"

COMPLETED_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*?"
    r"Iteration (?P<iteration>\d+) \(island (?P<island>\d+)\) completed "
    r"in (?P<elapsed>" + FLOAT + r")s\s+score=(?P<score>" + FLOAT + r")"
)
FAILED_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+).*?"
    r"Iteration (?P<iteration>\d+) \(island (?P<island>\d+)\) failed: (?P<error>.*)"
)


@dataclasses.dataclass
class IterationScore:
    iteration: int
    island: int
    score: float
    status: str
    elapsed_s: float | None = None
    error: str = ""
    is_compile_error: bool = False
    timestamp: str = ""
    line: int = 0


def parse_log(lines: Iterable[str], failed_score: float) -> list[IterationScore]:
    rows_by_iteration: dict[int, IterationScore] = {}

    for lineno, line in enumerate(lines, 1):
        if m := COMPLETED_RE.search(line):
            iteration = int(m.group("iteration"))
            rows_by_iteration[iteration] = IterationScore(
                iteration=iteration,
                island=int(m.group("island")),
                score=float(m.group("score")),
                status="completed",
                elapsed_s=float(m.group("elapsed")),
                timestamp=m.group("timestamp"),
                line=lineno,
            )
            continue

        if m := FAILED_RE.search(line):
            iteration = int(m.group("iteration"))
            error = m.group("error").strip()
            is_compile_error = "compilation failed" in error.lower()
            rows_by_iteration[iteration] = IterationScore(
                iteration=iteration,
                island=int(m.group("island")),
                score=0.0 if is_compile_error else failed_score,
                status="compile_error" if is_compile_error else "failed",
                error=error,
                is_compile_error=is_compile_error,
                timestamp=m.group("timestamp"),
                line=lineno,
            )

    return [rows_by_iteration[i] for i in sorted(rows_by_iteration)]


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _as_dict(row: IterationScore) -> dict[str, object]:
    return dataclasses.asdict(row)


def emit_markdown(rows: list[IterationScore], output) -> None:
    columns = [
        "iteration",
        "island",
        "score",
        "status",
        "elapsed_s",
        "error",
    ]
    print("| " + " | ".join(columns) + " |", file=output)
    print("| " + " | ".join(["---"] * len(columns)) + " |", file=output)
    for row in rows:
        print(
            "| " + " | ".join(_fmt(getattr(row, column)) for column in columns) + " |",
            file=output,
        )


def emit_csv(rows: list[IterationScore], output) -> None:
    columns = list(dataclasses.asdict(IterationScore(0, 0, 0.0, "")).keys())
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(_as_dict(row))


def emit_json(rows: list[IterationScore], output) -> None:
    json.dump([_as_dict(row) for row in rows], output, indent=2)
    print(file=output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract one score row per iteration from a PACEvolve controller log."
    )
    parser.add_argument("logfile", type=Path, help="Path to controller_verbose_*.log")
    parser.add_argument(
        "--format",
        choices=("markdown", "csv", "json"),
        default="markdown",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write output to a file instead of stdout.",
    )
    parser.add_argument(
        "--failed-score",
        type=float,
        default=0.0,
        help="Score assigned to non-compilation failed iterations. Compilation failures are always 0.",
    )
    args = parser.parse_args()

    with args.logfile.open("r", encoding="utf-8", errors="replace") as f:
        rows = parse_log(f, failed_score=args.failed_score)

    output = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
    try:
        if args.format == "markdown":
            emit_markdown(rows, output)
        elif args.format == "csv":
            emit_csv(rows, output)
        else:
            emit_json(rows, output)
    finally:
        if args.output:
            output.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
