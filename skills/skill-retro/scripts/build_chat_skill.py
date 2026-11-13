#!/usr/bin/env python3
"""Build the Claude chat edition of skill-retro as an uploadable .skill file.

The chat edition lives in chat/skill-retro/ and shares references/note-format.md
with the Claude Code edition, so the build copies that file in.

Usage: python3 scripts/build_chat_skill.py [OUT_DIR]    (default: dist/)
"""
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "chat" / "skill-retro"
SHARED = [ROOT / "references" / "note-format.md"]


def main() -> None:
    out_dir = pathlib.Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else ROOT / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "skill-retro.skill"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SRC.rglob("*")):
            if f.is_file() and f.name != ".DS_Store":
                z.write(f, pathlib.Path("skill-retro") / f.relative_to(SRC))
        for f in SHARED:
            z.write(f, pathlib.Path("skill-retro/references") / f.name)
    print(out)


if __name__ == "__main__":
    main()
