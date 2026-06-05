"""Load standalone SVG files from disk for ICO conversion."""

from __future__ import annotations

from pathlib import Path

from src.icon_extractor import IconSvg


def _read_svg_bytes(path: Path) -> bytes:
    for encoding in ("utf-8", "utf-8-sig"):
        try:
            return path.read_text(encoding=encoding).encode("utf-8")
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path.name} as UTF-8")


def _load_single_svg(path: Path) -> IconSvg:
    if not path.is_file():
        raise FileNotFoundError(f"SVG file not found: {path}")
    if path.suffix.lower() != ".svg":
        raise ValueError(f"Not an SVG file: {path.name}")

    svg_bytes = _read_svg_bytes(path)
    if not svg_bytes.strip():
        raise ValueError(f"SVG file is empty: {path.name}")

    return IconSvg(font_class=path.stem or "icon", name=path.name, svg_bytes=svg_bytes)


def load_svg_files(paths: list[Path]) -> tuple[list[IconSvg], list[str]]:
    """Load one or more standalone SVG files."""
    icons: list[IconSvg] = []
    warnings: list[str] = []

    for path in paths:
        try:
            icons.append(_load_single_svg(path))
        except (OSError, ValueError) as exc:
            warnings.append(f"{path.name}: {exc}")

    return icons, warnings


def load_svgs_from_dir(svg_dir: Path) -> tuple[list[IconSvg], list[str]]:
    """Load all *.svg files in a directory (non-recursive)."""
    if not svg_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {svg_dir}")

    svg_files = sorted(svg_dir.glob("*.svg"))
    if not svg_files:
        raise ValueError("目录中未找到 .svg 文件")

    return load_svg_files(svg_files)
