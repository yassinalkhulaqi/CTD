"""Print a per-branch report of additions, deletions, net LOC and tests.

The report is meant for release review: it lists every feature branch, the
net authored lines and the share of those lines that are tests, then prints
the aggregate totals of the program.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass

from loc_gate import discover_branches, stat_for


@dataclass(frozen=True, slots=True)
class Row:
    """A formatted report row."""

    branch: str
    additions: int
    deletions: int
    net: int
    tests: int
    test_ratio: float


def commit_of(branch: str) -> str:
    """Return the short commit hash of a branch."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", branch],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()[:8]


def build_row(baseline: str, branch: str) -> Row:
    """Build a report row for a branch."""
    stat = stat_for(baseline, branch)
    ratio = stat.test_net / stat.net if stat.net > 0 else 0.0
    return Row(branch, stat.additions, stat.deletions, stat.net, stat.test_net, ratio)


def main(argv: list[str] | None = None) -> int:
    """Render the report and return a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="baseline ref used for every comparison")
    parser.add_argument("branches", nargs="*", help="branches to report")
    parser.add_argument("--all", action="store_true", help="report every local dev/v3-* branch")
    args = parser.parse_args(argv)

    branches = discover_branches() if args.all else list(args.branches)
    if not branches:
        print("error: no branches to report", file=sys.stderr)
        return 2

    rows = [build_row(args.baseline, branch) for branch in branches]
    width = max(len("branch"), *(len(row.branch) for row in rows))
    print(
        f"{'branch':<{width}}  {'commit':<8}  {'add':>6}  {'del':>6}  "
        f"{'net':>7}  {'tests':>6}  {'test %':>7}"
    )
    for row in rows:
        print(
            f"{row.branch:<{width}}  {commit_of(row.branch):<8}  {row.additions:>6}  "
            f"{row.deletions:>6}  {row.net:>7}  {row.tests:>6}  {row.test_ratio:>6.1%}"
        )

    additions = sum(row.additions for row in rows)
    deletions = sum(row.deletions for row in rows)
    tests = sum(row.tests for row in rows)
    net = additions - deletions
    ratio = tests / net if net > 0 else 0.0
    print(f"\ntotal branches: {len(rows)}")
    print(f"total additions: {additions}")
    print(f"total deletions: {deletions}")
    print(f"total net LOC: {net}")
    print(f"total test LOC: {tests} ({ratio:.1%} of net)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
