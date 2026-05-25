"""Headless batch export test (no GUI)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.icon_extractor import load_icons_from_dir, sanitize_filename
from src.ico_builder import DEFAULT_SIZES, build_ico

INPUT_DIR = ROOT / "ai_icon" / "font_6xww5b6c7bv"
OUTPUT_DIR = ROOT / "output_icons"


def main() -> None:
    icons, warnings = load_icons_from_dir(INPUT_DIR)
    print(f"Loaded {len(icons)} icons, {len(warnings)} warnings")
    for w in warnings:
        print("  warn:", w)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for icon in icons:
        out = OUTPUT_DIR / f"{sanitize_filename(icon.font_class)}.ico"
        build_ico(icon.svg_bytes, out, DEFAULT_SIZES, background="white")
        ok += 1
        print(f"  ok: {out.name}")

    print(f"Exported {ok} ICO files to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
