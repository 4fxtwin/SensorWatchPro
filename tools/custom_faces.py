#!/usr/bin/env python3
"""Add this repo's own watch faces (faces/<category>/<name>_face.{c,h}) to a second-movement checkout.

  custom_faces.py apply <second-movement>   -> copy the faces in and register them in the build
  custom_faces.py list                      -> print the custom face ids, one per line

<category> must be one of upstream's watch-faces/ folders that is already on the include path
(clock, complication, demo, sensor, settings, io). Running apply twice is harmless.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACES = ROOT / "faces"
MARKER = "// New includes go above this line."


def custom_faces():
    """Return [(face_id, category, header_path, source_path)] for every face in faces/."""
    out = []
    for h in sorted(FACES.glob("*/*_face.h")):
        c = h.with_suffix(".c")
        if not c.exists():
            sys.exit(f"{h}: matching {c.name} not found")
        out.append((h.stem, h.parent.name, h, c))
    return out


def apply(up):
    up = Path(up).resolve()
    mk, inc = up / "watch-faces.mk", up / "movement_faces.h"
    mk_text, inc_text = mk.read_text(), inc.read_text()
    if MARKER not in inc_text:
        sys.exit(f"{inc}: marker {MARKER!r} not found; upstream layout changed")
    known = set(re.findall(r'#include\s+"(\w+_face)\.h"', inc_text))

    for face, cat, h, c in custom_faces():
        dest = up / "watch-faces" / cat
        if not dest.is_dir():
            sys.exit(f"{h}: category {cat!r} is not an upstream watch-faces/ folder")
        src_line = f"./watch-faces/{cat}/{c.name}"
        if face in known and src_line not in mk_text:
            sys.exit(f"{face}: upstream already has a face with this name")
        shutil.copy2(h, dest / h.name)
        shutil.copy2(c, dest / c.name)
        if src_line not in mk_text:
            mk_text = mk_text.rstrip("\n") + f"\nSRCS += {src_line}\n"
        if face not in known:
            inc_text = inc_text.replace(MARKER, f'#include "{face}.h"\n{MARKER}')
            known.add(face)
        print(f"custom face: {face} -> watch-faces/{cat}/")

    mk.write_text(mk_text)
    inc.write_text(inc_text)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "apply":
        apply(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "list":
        print("\n".join(f[0] for f in custom_faces()))
    else:
        sys.exit(__doc__)
