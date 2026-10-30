"""Shared helpers: kit paths, .env, project profile, status labels, ID filters."""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv

KIT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(KIT_ROOT / ".env")

PLATFORMS = ("android", "ios", "web")
STATUS_KEYS = ("pass", "fail", "blocked", "skip")
DEFAULT_LABELS = {"pass": "Passed", "fail": "Failed", "blocked": "Pending", "skip": "Skip"}
DEFAULT_COLUMNS = {
    "id": "ID",
    "description": "Description",
    "precondition": "",
    "steps": "",
    "expected": "Expected Result",
    "priority": "",
    "type": "",
    "status_ios": "Status iOS",
    "status_android": "Status Android",
    "status_web": "Status Web",
    "bug_id": "Bug ID",
    "note": "Note",
    "date": "Date",
}
# Column order used when the kit has to create a new sheet.
COLUMN_ORDER = ("id", "description", "precondition", "steps", "expected", "priority", "type",
                "status_ios", "status_android", "status_web", "bug_id", "note", "date")


def die(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def env(name: str, required: bool = True) -> str | None:
    val = os.getenv(name)
    if required and not val:
        die(f"Missing {name} in .env (see .env.example)")
    return val


def kit_path(p: str | Path) -> Path:
    p = Path(str(p)).expanduser()
    return p if p.is_absolute() else KIT_ROOT / p


def today() -> str:
    return date.today().isoformat()


def load_profile(project: str) -> dict:
    path = KIT_ROOT / "projects" / project / "profile.yaml"
    if not path.exists():
        die(f"Profile not found: {path}. Create it with /new-project {project}")
    prof = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    prof["_dir"] = path.parent
    prof.setdefault("name", project)
    prof.setdefault("platforms", {})
    prof.setdefault("modules", [])
    tc = prof.setdefault("testcases", {})
    cols = dict(DEFAULT_COLUMNS)
    cols.update(tc.get("columns") or {})
    tc["columns"] = cols
    labels = dict(DEFAULT_LABELS)
    labels.update(tc.get("status_labels") or {})
    tc["status_labels"] = labels
    tc.setdefault("skip_sheets", ["Summary"])
    tc.setdefault("note_prefix", "[Claude]")
    return prof


def status_key_of(value: str, labels: dict) -> str:
    """Map a cell value or a results value to pass|fail|blocked|skip; '' if empty; 'other' if unknown."""
    v = (value or "").strip().lower()
    if not v:
        return ""
    for key, label in labels.items():
        if v == str(label).strip().lower() or v == key:
            return key
    aliases = {"passed": "pass", "ok": "pass", "failed": "fail", "pending": "blocked",
               "block": "blocked", "skipped": "skip", "n/a": "skip", "na": "skip"}
    return aliases.get(v, "other")


def module_list(prof: dict, spec: str) -> list[dict]:
    """Return module dicts for 'all' or a comma list of module ids / sheet names."""
    mods = prof.get("modules") or []
    if not spec or spec.strip().lower() == "all":
        return mods
    out = []
    for token in [t.strip() for t in spec.split(",") if t.strip()]:
        hit = next((m for m in mods if str(m.get("id", "")).lower() == token.lower()
                    or str(m.get("sheet", "")).lower() == token.lower()), None)
        if not hit:
            die(f"Module '{token}' not in profile.yaml modules: {[m.get('id') for m in mods]}")
        out.append(hit)
    return out


_NUM_RE = re.compile(r"^(.*?)(\d+)$")


def _split_id(s: str):
    m = _NUM_RE.match(s.strip())
    return (m.group(1).lower(), int(m.group(2))) if m else (s.strip().lower(), None)


def parse_id_filter(spec: str):
    """'MSG_001..MSG_010,MSG_015' -> predicate(id). Also accepts 'MSG_001-MSG_010'."""
    if not spec:
        return lambda _id: True
    singles, ranges = set(), []
    for tok in [t.strip() for t in spec.split(",") if t.strip()]:
        a = b = None
        if ".." in tok:
            a, b = tok.split("..", 1)
        else:
            m = re.match(r"^(.+?\d+)-(.+?\d+)$", tok)
            if m and _split_id(m.group(1))[0] == _split_id(m.group(2))[0]:
                a, b = m.group(1), m.group(2)
        if a and b:
            pa, na = _split_id(a)
            pb, nb = _split_id(b)
            if pa != pb or na is None or nb is None:
                die(f"Bad id range: {tok}")
            ranges.append((pa, min(na, nb), max(na, nb)))
        else:
            singles.add(tok.lower())

    def pred(_id: str) -> bool:
        if _id.strip().lower() in singles:
            return True
        p, n = _split_id(_id)
        return n is not None and any(p == rp and lo <= n <= hi for rp, lo, hi in ranges)

    return pred
