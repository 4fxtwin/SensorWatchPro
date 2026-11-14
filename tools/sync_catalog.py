#!/usr/bin/env python3
"""Regenerate the face/tune catalog embedded in index.html from a second-movement checkout.

Usage: python3 tools/sync_catalog.py <path-to-second-movement> [--check]

Writes catalog.json and replaces the block between the CATALOG markers in index.html.
Faces in this repo's faces/<category>/ folder are added with "custom": true
(see tools/custom_faces.py, which adds them to the firmware build).
With --check, exits 1 if index.html is out of date instead of writing.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"
JSON_OUT = ROOT / "catalog.json"
BEGIN, END = "/*CATALOG-BEGIN*/", "/*CATALOG-END*/"


def git(up, *args):
    return subprocess.run(["git", "-C", str(up), *args], capture_output=True, text=True, check=True).stdout.strip()


def header_doc(text):
    """Return (title, body) from the first non-licence /* ... */ comment."""
    for m in re.finditer(r"/\*(.*?)\*/", text, re.S):
        block = m.group(1)
        if re.search(r"MIT License|Permission is hereby granted|SPDX-License|Copyright", block):
            continue
        lines = [re.sub(r"^\s*\* ?", "", l).rstrip() for l in block.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            continue
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        return title, body
    return "", ""


def authors(text):
    out = []
    for m in re.finditer(r"Copyright\s*(?:\(c\)|©)?\s*\d{4}[\d\-–, ]*\s+(.+)", text, re.I):
        name = re.sub(r"<[^>]*>|\(?https?://\S+\)?", "", m.group(1)).strip(" .,")
        if name and name not in out:
            out.append(name)
    return out


# Display names where plain title-casing of the id reads wrong.
NAME_OVERRIDES = {
    "totp": "TOTP", "totp_lfs": "TOTP (LittleFS)", "lis2dw_monitor": "LIS2DW monitor",
    "ke_decimal_time": "Kè decimal time", "rtccount": "RTC count", "irda_upload": "IrDA upload", "ir_peak": "IR peak hold",
    "nanosec": "Nanosec", "fast_stopwatch": "Stopwatch (stock)", "world_clock2": "World clock 2",
    "ish": "-ish", "wumpus": "Hunt the Wumpus", "simon": "Simon", "temperature_display": "Temperature",
    "temperature_logging": "Temperature log", "sun_moon_compass": "Sun & moon compass",
}


def display_name(face_id):
    base = face_id[:-5]
    return NAME_OVERRIDES.get(base) or base.replace("_", " ").capitalize()


def face_entry(name, p):
    text = p.read_text(errors="replace")
    if not re.search(rf"#define\s+{name}[\s\\]*\(\(const watch_face_t\)", text):
        sys.exit(f"{p}: no '#define {name} ((const watch_face_t)...' found")
    title, body = header_doc(text)
    return {
        "id": name,
        "category": p.parent.name,
        "name": display_name(name),
        "title": title,
        "desc": (title + "\n\n" + body).strip(),
        "authors": authors(text),
        "requires": sorted(set(re.findall(r"#ifdef\s+(HAS_\w+)", text))),
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    up = Path(args[0]).resolve()

    includes = re.findall(r'#include\s+"(\w+_face)\.h"', (up / "movement_faces.h").read_text())
    headers = {p.stem: p for p in sorted(up.glob("watch-faces/*/*_face.h"))}
    missing = [n for n in includes if n not in headers]
    orphans = [n for n in headers if n not in includes]
    if missing:
        sys.exit(f"movement_faces.h includes headers not found: {missing}")

    faces = [face_entry(name, headers[name]) for name in includes]
    for p in sorted((ROOT / "faces").glob("*/*_face.h")):
        if p.stem in includes:
            sys.exit(f"{p}: upstream already has a face named {p.stem}")
        faces.append(dict(face_entry(p.stem, p), custom=True))

    tunes = re.findall(r"#ifdef\s+(SIGNAL_TUNE_\w+)", (up / "movement_custom_signal_tunes.h").read_text())
    default_faces = re.findall(r"^\s*(\w+_face),\s*$",
                               re.search(r"watch_faces\[\]\s*=\s*\{(.*?)\};", (up / "movement_config.h").read_text(), re.S).group(1),
                               re.M)

    catalog = {
        "upstream": {
            "repo": "joeycastillo/second-movement",
            "sha": git(up, "rev-parse", "HEAD"),
            "date": git(up, "log", "-1", "--format=%cI"),
        },
        "defaultFaces": default_faces,
        "faces": faces,
        "tunes": tunes,
    }

    js = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
    html = HTML.read_text()
    i, j = html.index(BEGIN) + len(BEGIN), html.index(END)
    new_html = html[:i] + js + html[j:]

    print(f"upstream {catalog['upstream']['sha'][:7]}: {len(faces)} faces, {len(tunes)} tunes"
          + (f", {len(orphans)} headers not in movement_faces.h: {orphans}" if orphans else ""))
    if check:
        if new_html != html:
            sys.exit("index.html catalog is out of date; run tools/sync_catalog.py")
        return
    HTML.write_text(new_html)
    JSON_OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
