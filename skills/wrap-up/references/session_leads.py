#!/usr/bin/env python3
"""List leads for wrap-up from a Claude Code session transcript.

Leads, not an inventory: patterns over free-form shell text miss things and
flag things that were already cleaned up. Verify every lead against live state.

Usage: session_leads.py <session-id | path/to/session.jsonl>
Exit 2 when the transcript cannot be found or does not parse as expected.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import NoReturn

PROJECTS = Path.home() / ".claude" / "projects"
LIMIT = 10


class Kind(Enum):
    WORKTREE = "worktree / branch"
    CONTAINER = "container / cluster"
    DATABASE = "database"
    REMOTE = "remote host / shared service"
    PROCESS = "background process"
    BUILD = "install / build outside the main checkout"
    FILE = "file written outside the main checkout"
    SUBAGENT = "subagent with no delivered result"
    QUEUED = "user message sent mid-turn (check it was acted on)"


PATTERNS: dict[Kind, re.Pattern[str]] = {
    Kind.WORKTREE: re.compile(
        r"\bgit\b.*\bworktree\s+add\b|\bgit\b.*\b(checkout|switch)\s+-[bBc]\b"
    ),
    Kind.CONTAINER: re.compile(
        r"\b(docker|podman)\s+(run|create|compose\s+up)\b|\bdocker-compose\s+up\b|\b(kind|k3d|minikube)\s+(create|start)\b|\bcolima\s+start\b"
    ),
    Kind.DATABASE: re.compile(
        r"\b(createdb|initdb|pg_ctl|pgserver|redis-server)\b|\bpostgres\s+-D\b|\bCREATE\s+DATABASE\b",
        re.I,
    ),
    Kind.REMOTE: re.compile(
        r"\brsync\b.*\S:|\bkubectl\s+(apply|create|run|exec|port-forward|delete|scale|rollout)\b"
        r"|\bgcloud\b.*\b(create|deploy)\b|\bgh\s+(pr|issue|release|repo)\s+(create|merge|close|comment|edit)\b"
        r"|\bgh\s+api\b.*-X\s*(POST|PATCH|PUT|DELETE)\b"
    ),
    Kind.PROCESS: re.compile(
        r"\bnohup\b|(?<![&|>])&\s*($|;|\n)|\btilt\s+up\b|\b(pnpm|npm|yarn)\s+(run\s+)?dev\b"
    ),
}
BUILD = re.compile(
    r"\b(pnpm|npm|yarn|bun)\s+(install|i|ci|rebuild)\b|\bcargo\s+(build|test|install)\b|\bnapi\s+build\b"
    r"|\buv\s+(sync|venv)\b|\bpython3?\s+-m\s+venv\b|\bpip3?\s+install\b|\bplaywright\s+install\b"
)
SYSTEM_INSTALL = re.compile(
    r"\b(brew|apt|apt-get|dnf)\s+install\b|\bnpm\s+(install|i)\s+-g\b|\bcargo\s+install\b"
)
DIR_HINT = re.compile(
    r"(?:^|&&|;|\|\|)\s*cd\s+(\"[^\"]+\"|'[^']+'|\S+)|\s-C\s+(\"[^\"]+\"|\S+)"
)
MUTATING_MCP = re.compile(
    r"^mcp__.*__.*(send|create|post|update|delete|schedule|share|trash)", re.I
)
AGENT_ID = re.compile(r"agentId:\s*([0-9a-f]{8,})")
SSH_HOST = re.compile(
    r"\bssh\s+(?:-\S+(?:\s+(?!-)[^\s'\"]+)?\s+)*(\w[\w.@-]*)|\bscp\b.*?\s(\w[\w.@-]*):"
)
REMOTE_CREATE = re.compile(
    r"(?:mkdir\s+(?:-p\s+)?|uv\s+venv\s+(?:-\S+\s+(?:\S+\s+)?)*|git\s+clone\s+(?:-\S+\s+(?:\d+\s+)?)*\S+\s+|cat\s+>\s*|\s>\s*|cd\s+)((?:/|~/)[^\s'\";&|]+)"
)
QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\\\]|\\\\.)*\"")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?^\s*\2\s*$", re.S | re.M)
SCRATCH = re.compile(r"/tmp/claude-\d+/[^/]+/[0-9a-f-]{36}/(scratchpad|tasks)(/|$)")
LOCAL_VM_SSH = re.compile(r"\b(colima|limactl|multipass|vagrant|orb)\s+ssh\b")
REMOTE_DETACH = re.compile(r"\bnohup\b|\bsetsid\b|\btmux\s+new|\bscreen\s+-d")


@dataclass(frozen=True)
class Lead:
    kind: Kind
    where: str
    text: str


@dataclass
class Session:
    path: Path
    raw: str
    main_dir: Path | None = None
    leads: list[Lead] = field(default_factory=list)
    user_texts: set[str] = field(default_factory=set)
    queued: list[tuple[str, str]] = field(default_factory=list)
    agent_ids: dict[str, str] = field(default_factory=dict)
    background: dict[str, str] = field(default_factory=dict)
    hosts: dict[str, tuple[int, set[str], bool]] = field(default_factory=dict)
    builds: dict[str, set[str]] = field(default_factory=dict)
    assistant_events: int = 0
    tool_uses: int = 0


def fail(reason: str) -> NoReturn:
    print(f"error: {reason}", file=sys.stderr)
    sys.exit(2)


def locate(arg: str) -> Path:
    candidate = Path(arg).expanduser()
    if candidate.suffix == ".jsonl" and candidate.is_file():
        return candidate
    matches = sorted(PROJECTS.glob(f"*/{arg}.jsonl"))
    match matches:
        case [only]:
            return only
        case []:
            fail(f"no transcript for session {arg!r} under {PROJECTS}")
        case _:
            fail(f"several transcripts for {arg!r}: {', '.join(map(str, matches))}")


def short(text: str, limit: int = 220) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def effective_dir(command: str, cwd: Path | None) -> Path | None:
    hints = [a or b for a, b in DIR_HINT.findall(command)]
    if not hints:
        return cwd
    target = Path(hints[-1].strip("\"'").rstrip(";&|)")).expanduser()
    return target if target.is_absolute() or cwd is None else cwd / target


def outside(path: Path | None, main_dir: Path | None) -> bool:
    if path is None or main_dir is None or SCRATCH.search(str(path)):
        return False
    if "/worktrees/" in f"{path}/":
        return True
    return not (path == main_dir or main_dir in path.parents)


def text_blocks(content: object) -> list[str]:
    match content:
        case str(text):
            return [text]
        case list(blocks):
            return [
                b["text"]
                for b in blocks
                if isinstance(b, dict) and b.get("type") == "text" and "text" in b
            ]
        case _:
            return []


def collapse(path: str) -> str:
    parts = Path(path).parts
    match parts:
        case ("/", "tmp" | "var", name, *_):
            return f"/{parts[1]}/{name}"
        case ("/", "home", user, top, name, *_) if top in {"venvs", ".cache", ".venvs"}:
            return f"/home/{user}/{top}/{name}"
        case ("/", "home", user, name, *_):
            return f"/home/{user}/{name}"
        case ("~", name, *_):
            return f"~/{name}"
        case _:
            return path


def scan_tool_use(session: Session, block: dict, cwd: Path | None, origin: str) -> None:
    session.tool_uses += 1
    name, payload = block.get("name", ""), block.get("input") or {}
    where = f"{origin} {cwd or '?'}"
    match name:
        case "Bash":
            raw_command = str(payload.get("command", ""))
            command = HEREDOC.sub("<<heredoc", raw_command)
            local = QUOTED.sub("''", command)
            for host in {
                a or b for a, b in SSH_HOST.findall(LOCAL_VM_SSH.sub("", command))
            } - {""}:
                count, paths, detached = session.hosts.get(host, (0, set(), False))
                paths |= {
                    collapse(m)
                    for m in REMOTE_CREATE.findall(raw_command)
                    if not (m.startswith("/dev") or SCRATCH.search(m))
                }
                session.hosts[host] = (
                    count + 1,
                    paths,
                    detached or bool(REMOTE_DETACH.search(command)),
                )
            for kind, pattern in PATTERNS.items():
                if pattern.search(command if kind is Kind.REMOTE else local):
                    session.leads.append(Lead(kind, where, short(command)))
            if payload.get("run_in_background"):
                session.background[block.get("id", "")] = short(command)
            if SYSTEM_INSTALL.search(command):
                session.leads.append(Lead(Kind.BUILD, where, short(command)))
            elif (found := BUILD.search(local)) and outside(
                target := effective_dir(command, cwd), session.main_dir
            ):
                session.builds.setdefault(str(target), set()).add(
                    " ".join(found.group(0).split())
                )
        case "Write" | "Edit" | "NotebookEdit":
            target = Path(
                str(payload.get("file_path") or payload.get("notebook_path") or "")
            )
            if not SCRATCH.search(str(target)) and outside(target, session.main_dir):
                session.leads.append(Lead(Kind.FILE, where, str(target)))
        case "EnterWorktree":
            session.leads.append(Lead(Kind.WORKTREE, where, short(json.dumps(payload))))
        case _ if MUTATING_MCP.search(name):
            session.leads.append(
                Lead(Kind.REMOTE, where, f"{name} {short(json.dumps(payload), 160)}")
            )


def scan_events(session: Session, path: Path, origin: str) -> None:
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        cwd = Path(event["cwd"]) if event.get("cwd") else None
        if session.main_dir is None and cwd is not None and origin == "main":
            session.main_dir = cwd
        message = event.get("message") or {}
        match event.get("type"):
            case "assistant":
                session.assistant_events += 1
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        scan_tool_use(session, block, cwd, origin)
                        if block.get("name") == "Agent" and origin == "main":
                            description = str(
                                (block.get("input") or {}).get("description", "")
                            )
                            session.agent_ids[block.get("id", "")] = description
            case "user" if origin == "main":
                content = message.get("content")
                session.user_texts.update(t.strip() for t in text_blocks(content))
                if isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "tool_result"
                        ):
                            joined = json.dumps(block.get("content"))
                            if found := AGENT_ID.search(joined):
                                tool_id = block.get("tool_use_id", "")
                                session.agent_ids[found.group(1)] = (
                                    session.agent_ids.pop(tool_id, "")
                                )
            case "queue-operation" if (
                origin == "main" and event.get("operation") == "enqueue"
            ):
                content = str(event.get("content", "")).strip()
                if content and not content.startswith("<"):
                    session.queued.append((str(event.get("timestamp", "?")), content))


def finished(raw: str, key: str) -> bool:
    stopped = re.search(rf'"task_id":\s*"{key}"', raw) is not None
    notified = (
        re.search(
            rf"<(task-id|tool-use-id)>{key}</\1>.{{0,800}}?<status>\w+</status>",
            raw,
            re.S,
        )
        is not None
    )
    return stopped or notified


def main() -> None:
    if len(sys.argv) != 2:
        fail(str(__doc__).strip())
    path = locate(sys.argv[1])
    session = Session(path, path.read_text(errors="replace"))
    scan_events(session, path, "main")
    if session.assistant_events == 0:
        fail(
            f"no assistant events parsed in {path}; the transcript format may have changed"
        )
    if session.tool_uses == 0 and session.assistant_events > 20:
        fail(
            f"{session.assistant_events} assistant events but no tool calls parsed; the format may have changed"
        )
    for sub in sorted((path.parent / path.stem / "subagents").glob("agent-*.jsonl")):
        scan_events(session, sub, f"subagent {sub.stem.removeprefix('agent-')}")
        session.raw += sub.read_text(errors="replace")

    for agent_id, description in session.agent_ids.items():
        if (
            not agent_id.startswith("toolu_")
            and f'from="{agent_id}"' not in session.raw
            and not finished(session.raw, agent_id)
        ):
            session.leads.append(
                Lead(Kind.SUBAGENT, "main", f"{agent_id} {description}")
            )
    for task_id, command in session.background.items():
        if not finished(session.raw, task_id):
            session.leads.append(Lead(Kind.PROCESS, f"background {task_id}", command))
    for directory, tools in session.builds.items():
        session.leads.append(Lead(Kind.BUILD, directory, ", ".join(sorted(tools))))
    for host, (count, paths, detached) in session.hosts.items():
        created = ", ".join(sorted(paths)) or "nothing detected"
        note = "; detached job started" if detached else ""
        session.leads.append(
            Lead(
                Kind.REMOTE,
                f"ssh {host}",
                f"{count} commands; paths created or entered: {created}{note}",
            )
        )
    for timestamp, content in session.queued:
        if content not in session.user_texts:
            session.leads.append(Lead(Kind.QUEUED, timestamp, short(content, 400)))

    print(f"# leads for {path}")
    print(f"# main checkout: {session.main_dir}")
    print(
        "# leads, not an inventory: patterns miss things and flag already-cleaned ones — verify each live"
    )
    for kind in Kind:
        leads = list(dict.fromkeys(lead for lead in session.leads if lead.kind is kind))
        if leads:
            print(f"\n## {kind.value} ({len(leads)})")
            for lead in leads[:LIMIT]:
                print(f"- [{lead.where}] {lead.text}")
            if len(leads) > LIMIT:
                print(f"- … {len(leads) - LIMIT} more of this kind")


if __name__ == "__main__":
    main()
