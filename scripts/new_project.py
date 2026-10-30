#!/usr/bin/env python3
"""Create projects/<name>/ from projects/_template.
  .venv/bin/python scripts/new_project.py shopx
"""
import re
import shutil
import sys

from lib.config import KIT_ROOT, die


def main():
    if len(sys.argv) < 2:
        die("Usage: new_project.py <project-name>")
    name = sys.argv[1].strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        die("Project name: lowercase letters, digits and '-' only (e.g. shopx, my-app)")
    src, dst = KIT_ROOT / "projects" / "_template", KIT_ROOT / "projects" / name
    if dst.exists():
        die(f"{dst} already exists")
    shutil.copytree(src, dst)
    for f in dst.rglob("*"):
        if f.is_file() and f.suffix in (".yaml", ".md"):
            f.write_text(f.read_text(encoding="utf-8").replace("{{PROJECT}}", name), encoding="utf-8")
    print(f"Created {dst}. Next: fill profile.yaml and notes.md, then run check_setup.py --project {name}")


if __name__ == "__main__":
    main()
