"""Net-lines-of-code gate for the V3 feature branch program.

The gate compares every feature branch against the agreed baseline with
``git diff --numstat`` and fails when a branch does not add enough net lines.
Generated assets, dependency trees and caches are ignored so the number
reflects authored code, documentation and tests only.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass

IGNORED_PREFIXES: tuple[str, ...] = (
    "frontend/node_modules/",
    "frontend/dist/",
    "src/ctf_team_dashboard.egg-info/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
)

IGNORED_SUFFIXES: tuple[str, ...] = (
    ".pyc",
    ".coverage",
    ".tsbuildinfo",
)


@dataclass(frozen=True, slots=True)
class DiffLine:
    """One line of a ``git diff --numstat`` report."""

    additions: int
    deletions: int
    path: str


@dataclass(frozen=True, slots=True)
class BranchStat:
    """Aggregated diff statistics of a branch against the baseline."""

    branch: str
    additions: int
    deletions: int
    test_additions: int
    test_deletions: int

    @property
    def net(self) -> int:
        """Return the net number of added lines."""
        return self.additions - self.deletions

    @property
    def test_net(self) -> int:
        """Return the net number of added test lines."""
        return self.test_additions - self.test_deletions


def is_test_path(path: str) -> bool:
    """Return whether a path looks like a test file."""
    name = path.rsplit("/", 1)[-1]
    return name.startswith("test_") or ".test." in name or name.startswith("conftest")


def is_ignored(path: str) -> bool:
    """Return whether a path is generated output that must not be counted."""
    if any(path.startswith(prefix) for prefix in IGNORED_PREFIXES):
        return True
    return any(path.endswith(suffix) for suffix in IGNORED_SUFFIXES)


def numstat(baseline: str, branch: str) -> list[DiffLine]:
    """Return the parsed numstat lines between two refs."""
    result = subprocess.run(
        ["git", "diff", "--numstat", f"{baseline}..{branch}"],
        check=True,
        capture_output=True,
        text=True,
    )
    lines: list[DiffLine] = []
    for raw in result.stdout.splitlines():
        fields = raw.split("\t")
        if len(fields) != 3:
            continue
        if fields[0] == "-" or fields[1] == "-":
            continue
        path = fields[2]
        if is_ignored(path):
            continue
        lines.append(DiffLine(int(fields[0]), int(fields[1]), path))
    return lines


def stat_for(baseline: str, branch: str) -> BranchStat:
    """Aggregate the diff statistics of one branch."""
    additions = 0
    deletions = 0
    test_additions = 0
    test_deletions = 0
    for line in numstat(baseline, branch):
        additions += line.additions
        deletions += line.deletions
        if is_test_path(line.path):
            test_additions += line.additions
            test_deletions += line.deletions
    return BranchStat(branch, additions, deletions, test_additions, test_deletions)


def discover_branches() -> list[str]:
    """Return the local V3 feature branches sorted by name."""
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/dev/v3-*"],
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(name for name in result.stdout.splitlines() if name)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("refs", nargs="*", help="baseline followed by branches")
    parser.add_argument("--min", type=int, default=2000, help="minimum net LOC per branch")
    parser.add_argument(
        "--program-min",
        type=int,
        default=0,
        help="minimum combined net LOC across all branches",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="check every local dev/v3-* branch against the baseline",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the gate and return a process exit code."""
    args = build_parser().parse_args(argv)
    refs = list(args.refs)
    if refs and refs[-1].isdigit():
        args.min = int(refs.pop())
    if args.all:
        refs = refs[:1]
    if not refs:
        print("error: expected at least a baseline ref", file=sys.stderr)
        return 2

    baseline = refs[0]
    branches = discover_branches() if args.all else refs[1:]
    if not branches:
        print("error: no branches to check", file=sys.stderr)
        return 2

    stats = [stat_for(baseline, branch) for branch in branches]
    width = max(len("branch"), *(len(stat.branch) for stat in stats))
    print(f"{'branch':<{width}}  {'add':>6}  {'del':>6}  {'net':>7}  {'tests':>6}  status")
    for stat in stats:
        status = "PASS" if stat.net >= args.min else "FAIL"
        print(
            f"{stat.branch:<{width}}  {stat.additions:>6}  {stat.deletions:>6}  "
            f"{stat.net:>7}  {stat.test_net:>6}  {status}"
        )

    total = sum(stat.net for stat in stats)
    print(f"\nprogram net LOC: {total}")
    failed = [stat for stat in stats if stat.net < args.min]
    if failed:
        print(f"FAIL: {len(failed)} branch(es) below {args.min} net LOC", file=sys.stderr)
        return 1
    if args.program_min and total < args.program_min:
        print(f"FAIL: program below {args.program_min} net LOC", file=sys.stderr)
        return 1
    print("PASS: all branches meet the LOC gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
