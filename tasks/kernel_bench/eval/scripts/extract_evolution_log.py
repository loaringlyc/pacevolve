#!/usr/bin/env python3
"""Extract compact evolution tables from PACEvolve controller logs.

The controller log is intentionally verbose and, in parallel mode, messages from
different workers are interleaved. This parser uses stable log markers to recover
one row per iteration/candidate where possible:

  iteration | candidate | idea | parent | correctness | runtime | speedup | selected?

Notes:
  * "selected?" means the candidate completed evaluation and was registered back
    into the program database. The logs do not record whether it was later chosen
    as a parent by tournament selection.
  * "parent" is left blank unless future logs include an explicit parent marker.
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

IDEA_RE = re.compile(r"edit_until_compile: Setting idea ID to (?P<idea>-?\d+)")
WRITE_RE = re.compile(r"Successfully wrote to the library file: (?P<path>\S+)")
CANDIDATE_RE = re.compile(r"candidate ID (?P<candidate>\d+)", re.IGNORECASE)
CAND_EVAL_RE = re.compile(r"\(Cand ID: (?P<candidate>\d+)\)")
KERNEL_PATH_RE = re.compile(r"--kernel_path (?P<path>\S+)")
RUNTIME_RE = re.compile(r"Kernel runtime:\s*(?P<runtime>" + FLOAT + r")")
SPEEDUP_RE = re.compile(r"Kernel speedup:\s*(?P<speedup>" + FLOAT + r")")
ALL_EVALS_RE = re.compile(
    r"All evals ran for candidate (?P<candidate>\d+) after (?P<attempts>\d+) attempt"
)
EVAL_FAILED_RE = re.compile(r"Eval failed for candidate (?P<candidate>\d+)")
COMPLETE_RE = re.compile(
    r"Iteration (?P<iteration>\d+) \(island (?P<island>\d+)\) completed "
    r"in (?P<elapsed>" + FLOAT + r")s\s+score=(?P<score>" + FLOAT + r")"
)
FAILED_RE = re.compile(
    r"Iteration (?P<iteration>\d+) \(island (?P<island>\d+)\) failed: (?P<error>.*)"
)
SUMMARY_RE = re.compile(r"Summary:\s*(?P<summary>.*)")
START_PARALLEL_RE = re.compile(
    r"Starting parallel iteration (?P<iteration>\d+) on island (?P<island>\d+); "
    r"kernel workspace: (?P<workspace>\S+)"
)


@dataclasses.dataclass
class Row:
    iteration: int | None = None
    island: int | None = None
    candidate: int | None = None
    idea: int | None = None
    parent: str = ""
    correctness: str = ""
    runtime: float | None = None
    speedup: float | None = None
    selected: str = ""
    status: str = ""
    elapsed_s: float | None = None
    workspace: str = ""
    summary: str = ""
    error: str = ""
    line: int | None = None


def _workspace_from_path(path: str) -> str:
    """Return a stable workspace key for a kernel.py path."""
    path = path.strip("'\"")
    if path.endswith("/kernel.py"):
        return path[: -len("/kernel.py")]
    return str(Path(path).parent)


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _as_dict(row: Row) -> dict[str, object]:
    return dataclasses.asdict(row)


def parse_log(lines: Iterable[str]) -> list[Row]:
    rows_by_candidate: dict[int, Row] = {}
    failed_rows: list[Row] = []

    idea_by_workspace: dict[str, int] = {}
    iter_by_workspace: dict[str, tuple[int, int]] = {}
    current_idea: int | None = None
    pending_candidate: int | None = None
    active_candidate: int | None = None
    active_workspace: str = ""
    last_completed_candidate: int | None = None

    def row_for_candidate(candidate: int) -> Row:
        row = rows_by_candidate.get(candidate)
        if row is None:
            row = Row(candidate=candidate)
            rows_by_candidate[candidate] = row
        return row

    for lineno, line in enumerate(lines, 1):
        if m := START_PARALLEL_RE.search(line):
            workspace = m.group("workspace")
            iter_by_workspace[workspace] = (
                int(m.group("iteration")),
                int(m.group("island")),
            )
            continue

        if m := IDEA_RE.search(line):
            current_idea = int(m.group("idea"))
            continue

        if m := WRITE_RE.search(line):
            workspace = _workspace_from_path(m.group("path"))
            if current_idea is not None:
                idea_by_workspace[workspace] = current_idea
            continue

        if m := CANDIDATE_RE.search(line):
            pending_candidate = int(m.group("candidate"))
            row = row_for_candidate(pending_candidate)
            row.line = row.line or lineno
            continue

        if m := CAND_EVAL_RE.search(line):
            pending_candidate = int(m.group("candidate"))
            row_for_candidate(pending_candidate).line = lineno
            continue

        if "evaluate_dataset: Running" in line:
            path_match = KERNEL_PATH_RE.search(line)
            if path_match and pending_candidate is not None:
                active_candidate = pending_candidate
                active_workspace = _workspace_from_path(path_match.group("path"))
                row = row_for_candidate(active_candidate)
                row.workspace = active_workspace
                if active_workspace in idea_by_workspace:
                    row.idea = idea_by_workspace[active_workspace]
                if active_workspace in iter_by_workspace:
                    row.iteration, row.island = iter_by_workspace[active_workspace]
            continue

        if active_candidate is not None:
            row = row_for_candidate(active_candidate)
            if m := RUNTIME_RE.search(line):
                row.runtime = float(m.group("runtime"))
                row.correctness = row.correctness or "pass"
                continue
            if m := SPEEDUP_RE.search(line):
                row.speedup = float(m.group("speedup"))
                row.correctness = row.correctness or "pass"
                continue

        if m := ALL_EVALS_RE.search(line):
            candidate = int(m.group("candidate"))
            row = row_for_candidate(candidate)
            row.correctness = "pass"
            row.status = row.status or "eval_ok"
            if active_candidate == candidate:
                active_candidate = None
                active_workspace = ""
            continue

        if m := EVAL_FAILED_RE.search(line):
            candidate = int(m.group("candidate"))
            row = row_for_candidate(candidate)
            row.correctness = "fail"
            row.selected = "no"
            row.status = "eval_failed"
            if active_candidate == candidate:
                active_candidate = None
                active_workspace = ""
            continue

        if m := COMPLETE_RE.search(line):
            iteration = int(m.group("iteration"))
            island = int(m.group("island"))
            candidate = iteration + 1
            row = row_for_candidate(candidate)
            row.iteration = iteration
            row.island = island
            row.elapsed_s = float(m.group("elapsed"))
            row.speedup = row.speedup if row.speedup is not None else float(m.group("score"))
            row.correctness = row.correctness or "pass"
            row.status = "completed"
            row.selected = "yes"
            last_completed_candidate = candidate
            continue

        if m := FAILED_RE.search(line):
            iteration = int(m.group("iteration"))
            island = int(m.group("island"))
            failed_rows.append(
                Row(
                    iteration=iteration,
                    island=island,
                    candidate=iteration + 1,
                    correctness="fail",
                    selected="no",
                    status="failed",
                    error=m.group("error").strip(),
                    line=lineno,
                )
            )
            last_completed_candidate = None
            continue

        if m := SUMMARY_RE.search(line):
            if last_completed_candidate is not None:
                rows_by_candidate[last_completed_candidate].summary = m.group("summary").strip()
            continue

    rows = list(rows_by_candidate.values()) + failed_rows
    rows.sort(
        key=lambda row: (
            row.iteration if row.iteration is not None else 10**12,
            row.candidate if row.candidate is not None else 10**12,
            row.line if row.line is not None else 10**12,
        )
    )
    return rows


def emit_markdown(rows: list[Row], output) -> None:
    columns = [
        "iteration",
        "candidate",
        "idea",
        "parent",
        "correctness",
        "runtime",
        "speedup",
        "selected",
        "island",
        "status",
    ]
    print("| " + " | ".join(columns) + " |", file=output)
    print("| " + " | ".join(["---"] * len(columns)) + " |", file=output)
    for row in rows:
        values = [_fmt(getattr(row, col)) for col in columns]
        print("| " + " | ".join(values) + " |", file=output)


def emit_csv(rows: list[Row], output) -> None:
    columns = list(dataclasses.asdict(Row()).keys())
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow(_as_dict(row))


def emit_json(rows: list[Row], output) -> None:
    json.dump([_as_dict(row) for row in rows], output, indent=2)
    print(file=output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract iteration/candidate/idea/runtime/speedup tables from PACEvolve logs."
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
    args = parser.parse_args()

    with args.logfile.open("r", encoding="utf-8", errors="replace") as f:
        rows = parse_log(f)

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
