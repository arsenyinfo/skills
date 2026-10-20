# /// script
# requires-python = ">=3.11"
# dependencies = ["lizard>=1.17"]
# ///
"""Rank refactor candidates: churn x indentation complexity, grouped by change coupling; cyclomatic shown alongside."""

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path, PurePosixPath

import lizard


class Lang(Enum):
    PYTHON = "python"
    RUST = "rust"
    TS = "ts"


EXTENSIONS = {
    ".py": Lang.PYTHON,
    ".rs": Lang.RUST,
    ".ts": Lang.TS,
    ".tsx": Lang.TS,
    ".js": Lang.TS,
    ".jsx": Lang.TS,
    ".mjs": Lang.TS,
}
EXCLUDED = [
    "*.d.ts",
    "*_pb2.py",
    "*_pb2_grpc.py",
    "*.generated.*",
    "*.gen.*",
    "*.min.js",
    "*/migrations/*",
    "*/vendor/*",
    "*/node_modules/*",
    "*/dist/*",
    "*/build/*",
    "*/target/*",
    "*/__snapshots__/*",
]
GENERATED_MARKERS = re.compile(r"@generated|DO NOT EDIT|auto-?generated", re.IGNORECASE)
FIX_SUBJECT = re.compile(r"\b(fix|fixes|fixed|bug|revert|hotfix)\b", re.IGNORECASE)
MOCK_TOKENS = re.compile(r"\bmock|monkeypatch|MagicMock|\bpatch\(|jest\.mock|vi\.mock|sinon\.|mockall")
GENERIC_STEMS = {"index", "mod", "lib", "main", "__init__", "utils", "types", "conftest"}
COMMIT_MARK = "\x1e"
MASS_COMMIT_FILES = 50


@dataclass(frozen=True)
class Commit:
    author: str
    is_fix: bool
    files: tuple[str, ...]


@dataclass(frozen=True)
class FileStats:
    path: str
    churn: int
    complexity: int
    ccn: int
    max_ccn: int
    hotspot: int
    fix_ratio: float
    authors: int
    likely_tests: tuple[str, ...]
    mock_hits: int


@dataclass(frozen=True)
class Candidate:
    files: tuple[FileStats, ...]
    coupled: tuple[str, ...]
    score: int


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "core.quotePath=false", *args], check=True, capture_output=True, text=True
    ).stdout


def is_test(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        any(part in {"tests", "test", "__tests__"} for part in p.parts[:-1])
        or p.name.startswith("test_")
        or p.stem.endswith("_test")
        or ".test." in p.name
        or ".spec." in p.name
    )


def is_excluded(path: str, extra: list[str]) -> bool:
    padded = f"/{path}"
    return any(fnmatch.fnmatch(padded, pat) or fnmatch.fnmatch(path, pat) for pat in EXCLUDED + extra)


def read_text(repo: Path, path: str) -> str:
    try:
        return (repo / path).read_text(errors="replace")
    except OSError:
        return ""


def whitespace_complexity(text: str) -> int:
    lines = [ln.expandtabs(4) for ln in text.splitlines() if ln.strip()]
    indents = [len(ln) - len(ln.lstrip(" ")) for ln in lines]
    unit = min((i for i in indents if i > 0), default=4)
    return sum(i // unit for i in indents)


def parse_log(raw: str) -> list[Commit]:
    commits = []
    for chunk in raw.split(COMMIT_MARK)[1:]:
        header, _, body = chunk.partition("\n")
        author, _, subject = header.partition("\x00")
        files = tuple(f for f in body.splitlines() if f)
        commits.append(Commit(author=author, is_fix=bool(FIX_SUBJECT.search(subject)), files=files))
    return commits


def find_tests(path: str, text: str, tests: list[str], coupled_tests: set[str]) -> tuple[str, ...]:
    stem = PurePosixPath(path).stem
    by_name = (
        set()
        if stem in GENERIC_STEMS
        else {t for t in tests if re.search(rf"(^|[_./]){re.escape(stem)}([_./]|$)", PurePosixPath(t).name)}
    )
    inline = {path} if "#[cfg(test)]" in text else set()
    return tuple(sorted(by_name | coupled_tests | inline))


def file_stats(
    repo: Path, f: str, text: str, churn: int, complexity: int, fixes: int, authors: int, tests: tuple[str, ...]
) -> FileStats:
    # lizard's TSX reader finds no functions in real components; the TS reader handles JSX fine
    lizard_name = str(PurePosixPath(f).with_suffix(".ts")) if EXTENSIONS[PurePosixPath(f).suffix] is Lang.TS else f
    ccns = [fn.cyclomatic_complexity for fn in lizard.analyze_file.analyze_source_code(lizard_name, text).function_list]
    return FileStats(
        path=f,
        churn=churn,
        complexity=complexity,
        ccn=sum(ccns),
        max_ccn=max(ccns, default=0),
        hotspot=churn * complexity,
        fix_ratio=round(fixes / churn, 2),
        authors=authors,
        likely_tests=tests,
        mock_hits=sum(len(MOCK_TOKENS.findall(read_text(repo, t))) for t in tests if t != f),
    )


def build_candidates(args: argparse.Namespace) -> list[Candidate]:
    repo = Path(git(args.repo, "rev-parse", "--show-toplevel").strip())
    code = {
        f
        for f in git(repo, "ls-files").splitlines()
        if PurePosixPath(f).suffix in EXTENSIONS and not is_excluded(f, args.exclude)
    }
    in_scope = set(git(repo, "ls-files", "--", *args.paths).splitlines()) & code if args.paths else code
    raw = git(repo, "log", "--no-merges", f"--since={args.since}", "--name-only", f"--format={COMMIT_MARK}%ae%x00%s")
    commits = [c for c in parse_log(raw) if any(f in code for f in c.files)]

    churn: Counter[str] = Counter()
    fixes: Counter[str] = Counter()
    authors: defaultdict[str, set[str]] = defaultdict(set)
    pairs: Counter[tuple[str, str]] = Counter()
    for c in commits:
        touched = sorted(f for f in c.files if f in code)
        for f in touched:
            churn[f] += 1
            fixes[f] += c.is_fix
            authors[f].add(c.author)
        if len(touched) <= MASS_COMMIT_FILES:
            pairs.update(
                (a, b) for i, a in enumerate(touched) for b in touched[i + 1 :] if a in in_scope or b in in_scope
            )

    shared: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for (a, b), n in pairs.items():
        if n >= args.min_shared:
            shared[a][b] = shared[b][a] = n

    def coupled_with(f: str) -> set[str]:
        return {other for other, n in shared[f].items() if n / churn[f] >= args.min_coupling}

    texts = {f: read_text(repo, f) for f in churn if f in in_scope and not is_test(f)}
    texts = {f: t for f, t in texts.items() if not GENERATED_MARKERS.search("\n".join(t.splitlines()[:5]))}
    complexity = {f: whitespace_complexity(t) for f, t in texts.items()}
    hotspot = {f: churn[f] * complexity[f] for f in texts}

    claimed: set[str] = set()
    groups: list[list[str]] = []
    for seed in sorted(hotspot, key=hotspot.__getitem__, reverse=True):
        if seed in claimed:
            continue
        members = [seed, *sorted((coupled_with(seed) & hotspot.keys()) - claimed)]
        claimed.update(members)
        groups.append(members)
    groups = sorted(groups, key=lambda g: sum(hotspot[f] for f in g), reverse=True)[: args.top]

    tests = sorted(f for f in code if is_test(f))
    candidates = []
    for members in groups:
        extra = set().union(*(coupled_with(f) for f in members)) - set(members)
        candidates.append(
            Candidate(
                files=tuple(
                    file_stats(
                        repo,
                        f,
                        texts[f],
                        churn[f],
                        complexity[f],
                        fixes[f],
                        len(authors[f]),
                        find_tests(f, texts[f], tests, {t for t in coupled_with(f) if is_test(t)}),
                    )
                    for f in members
                ),
                coupled=tuple(sorted(f for f in extra if not is_test(f))),
                score=sum(hotspot[f] for f in members),
            )
        )
    return candidates


def render(candidates: list[Candidate]) -> str:
    out = []
    for i, c in enumerate(candidates, 1):
        out.append(f"#{i}  score={c.score}")
        for f in c.files:
            tests = (
                f"~{len(f.likely_tests)} likely tests, {f.mock_hits} mock hits" if f.likely_tests else "no tests found"
            )
            out.append(
                f"    {f.path}  churn={f.churn} cx={f.complexity} ccn={f.ccn} max_ccn={f.max_ccn} fix={f.fix_ratio:.0%} "
                f"authors={f.authors}  [{tests}]"
            )
        if c.coupled:
            out.append(f"    coupled: {', '.join(c.coupled)}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", help="restrict candidates to these repo-root-relative pathspecs (default: whole repo)"
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--since", default="12 months ago")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--exclude", action="append", default=[], help="extra glob, repeatable")
    parser.add_argument("--min-shared", type=int, default=3, help="min co-changing commits for coupling")
    parser.add_argument("--min-coupling", type=float, default=0.5, help="min shared/churn ratio for coupling")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        candidates = build_candidates(args)
    except subprocess.CalledProcessError as e:
        sys.exit(f"git failed: {e.stderr.strip()}")
    if not candidates:
        sys.exit(f"no candidates: no tracked Python/Rust/TS changes since {args.since!r}")
    print(json.dumps([asdict(c) for c in candidates], indent=2) if args.json else render(candidates))


if __name__ == "__main__":
    main()
