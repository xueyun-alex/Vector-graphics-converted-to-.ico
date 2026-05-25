"""Rasterize SVG and build multi-resolution ICO files."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image

DEFAULT_SIZES = [16, 32, 48, 256]


def render_svg_to_image(
    svg_bytes: bytes,
    size: int,
    *,
    background: str = "white",
) -> Image.Image:
    """Render SVG to a square RGBA PIL Image at the given pixel size."""
    doc = fitz.open(stream=svg_bytes, filetype="svg")
    try:
        page = doc[0]
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            raise ValueError("SVG has invalid dimensions")

        scale = size / max(rect.width, rect.height)
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=True)
    finally:
        doc.close()

    img = Image.frombytes("RGBA", (pixmap.width, pixmap.height), pixmap.samples)

    if background == "transparent":
        return img

    bg = Image.new("RGBA", img.size, background)
    bg.paste(img, mask=img.split()[3])
    return bg


def build_ico(
    svg_bytes: bytes,
    output_path: Path,
    sizes: list[int] | None = None,
    *,
    background: str = "white",
) -> None:
    """Render SVG at multiple sizes and save a Windows ICO file."""
    if not sizes:
        raise ValueError("At least one icon size is required")

    sizes = sorted(set(sizes))
    images: list[Image.Image] = []

    for size in sizes:
        img = render_svg_to_image(svg_bytes, size, background=background)
        if img.size != (size, size):
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        images.append(img.convert("RGBA"))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    base = images[-1]
    extra = images[:-1] if len(images) > 1 else []
    size_tuples = [img.size for img in images]

    base.save(
        output_path,
        format="ICO",
        sizes=size_tuples,
        append_images=extra,
    )


def preview_image(
    svg_bytes: bytes,
    size: int = 256,
    *,
    background: str = "white",
) -> Image.Image:
    """Return a PIL Image for GUI preview."""
    return render_svg_to_image(svg_bytes, size, background=background)


def image_to_photoimage(img: Image.Image):
    """Convert PIL Image to tkinter PhotoImage via PNG buffer."""
    import tkinter as tk

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return tk.PhotoImage(data=buf.getvalue())
