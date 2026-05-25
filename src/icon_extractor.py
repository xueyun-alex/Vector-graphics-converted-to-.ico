"""Parse iconfont.js / iconfont.json and build standalone SVG documents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

MARKER = "_iconfont_svg_string_='"
DEFAULT_VIEWBOX = "0 0 1024 1024"


@dataclass(frozen=True)
class GlyphInfo:
    font_class: str
    name: str
    symbol_id: str


@dataclass(frozen=True)
class IconSvg:
    font_class: str
    name: str
    svg_bytes: bytes


def _iconfont_paths(iconfont_dir: Path) -> tuple[Path, Path]:
    js_path = iconfont_dir / "iconfont.js"
    json_path = iconfont_dir / "iconfont.json"
    if not js_path.is_file():
        raise FileNotFoundError(f"Missing iconfont.js in {iconfont_dir}")
    if not json_path.is_file():
        raise FileNotFoundError(f"Missing iconfont.json in {iconfont_dir}")
    return js_path, json_path


def extract_svg_string(js_path: Path) -> str:
    """Extract embedded SVG XML from iconfont.js."""
    content = js_path.read_text(encoding="utf-8")
    start = content.find(MARKER)
    if start == -1:
        raise ValueError("Could not find _iconfont_svg_string_ in iconfont.js")
    start += len(MARKER)
    close_tag = "</svg>"
    end = content.find(close_tag, start)
    if end == -1:
        raise ValueError("Could not find end of SVG string in iconfont.js")
    return content[start : end + len(close_tag)]


def load_glyphs(json_path: Path) -> list[GlyphInfo]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    glyphs = []
    for item in data.get("glyphs", []):
        font_class = item.get("font_class", "").strip()
        if not font_class:
            continue
        glyphs.append(
            GlyphInfo(
                font_class=font_class,
                name=item.get("name", font_class),
                symbol_id=f"icon-{font_class}",
            )
        )
    return glyphs


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _serialize_children(element: ET.Element) -> str:
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(ET.tostring(child, encoding="unicode"))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def parse_symbols(svg_xml: str) -> dict[str, tuple[str, str]]:
    """Return symbol_id -> (viewBox, inner SVG markup)."""
    try:
        root = ET.fromstring(svg_xml)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid SVG XML in iconfont.js: {exc}") from exc

    symbols: dict[str, tuple[str, str]] = {}
    for elem in root.iter():
        if _local_tag(elem.tag) != "symbol":
            continue
        symbol_id = elem.attrib.get("id")
        if not symbol_id:
            continue
        viewbox = elem.attrib.get("viewBox", DEFAULT_VIEWBOX)
        inner = _serialize_children(elem)
        symbols[symbol_id] = (viewbox, inner)
    return symbols


def build_standalone_svg(viewbox: str, inner_markup: str) -> bytes:
    svg = (
        f'<svg xmlns="{SVG_NS}" viewBox="{viewbox}" width="1024" height="1024">'
        f"{inner_markup}"
        "</svg>"
    )
    return svg.encode("utf-8")


def load_icons_from_dir(iconfont_dir: Path) -> tuple[list[IconSvg], list[str]]:
    """
    Load all glyphs from iconfont directory.

    Returns (icons, warnings).
    """
    js_path, json_path = _iconfont_paths(iconfont_dir)
    svg_xml = extract_svg_string(js_path)
    symbols = parse_symbols(svg_xml)
    glyphs = load_glyphs(json_path)

    icons: list[IconSvg] = []
    warnings: list[str] = []

    for glyph in glyphs:
        entry = symbols.get(glyph.symbol_id)
        if entry is None:
            warnings.append(f"Symbol not found: {glyph.symbol_id} ({glyph.name})")
            continue
        viewbox, inner = entry
        icons.append(
            IconSvg(
                font_class=glyph.font_class,
                name=glyph.name,
                svg_bytes=build_standalone_svg(viewbox, inner),
            )
        )

    return icons, warnings


def sanitize_filename(font_class: str) -> str:
    """Make font_class safe for Windows filenames."""
    name = re.sub(r'[<>:"/\\|?*]', "_", font_class)
    return name.strip() or "icon"
