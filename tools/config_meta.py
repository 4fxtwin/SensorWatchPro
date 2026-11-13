#!/usr/bin/env python3
"""Read builder metadata from generated configs and check them against an upstream checkout.

  config_meta.py matrix <config.h>...         -> prints a GitHub Actions matrix (JSON)
  config_meta.py check <config.h> <upstream>  -> fails if a face is not in upstream movement_faces.h
"""
import json
import re
import sys
from pathlib import Path

DEFAULTS = {"board": "sensorwatch_pro", "display": "classic", "upstream": "main", "simulator": "no"}
DISPLAYS = {"classic", "custom"}


def meta(path):
    text = Path(path).read_text()
    m = dict(DEFAULTS, name=Path(path).stem)
    m.update(re.findall(r"builder:(\w+)=([\w.\-]+)", text))
    if m["display"] not in DISPLAYS:
        sys.exit(f"{path}: display must be one of {sorted(DISPLAYS)}, got {m['display']!r}")
    if not re.fullmatch(r"[0-9a-f]{7,40}|[\w.\-/]+", m["upstream"]):
        sys.exit(f"{path}: bad upstream ref {m['upstream']!r}")
    m["path"] = str(path)
    return m


def faces(text):
    block = re.search(r"watch_faces\[\]\s*=\s*\{(.*?)\};", text, re.S)
    if not block:
        sys.exit("no watch_faces[] array found")
    body = re.sub(r"/\*.*?\*/", "", block.group(1), flags=re.S)
    body = re.sub(r"//[^\n]*", "", body)
    return [f.strip() for f in body.split(",") if f.strip()]


def check(path, upstream):
    text = Path(path).read_text()
    known = set(re.findall(r'#include\s+"(\w+_face)\.h"', (Path(upstream) / "movement_faces.h").read_text()))
    used = faces(text)
    bad = [f for f in used if f not in known]
    if bad:
        print(f"::error file={path}::Unknown faces for this upstream revision: {', '.join(bad)}")
        sys.exit(1)
    if not used:
        print(f"::error file={path}::watch_faces[] is empty")
        sys.exit(1)
    idx = re.search(r"#define\s+MOVEMENT_SECONDARY_FACE_INDEX\s+(\d+)", text)
    if idx and not 0 <= int(idx.group(1)) < len(used):
        print(f"::error file={path}::MOVEMENT_SECONDARY_FACE_INDEX {idx.group(1)} is outside 0..{len(used) - 1}")
        sys.exit(1)
    print(f"{path}: {len(used)} faces OK")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "matrix":
        print(json.dumps({"include": [meta(p) for p in sys.argv[2:]]}))
    elif len(sys.argv) == 4 and sys.argv[1] == "check":
        check(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
