"""
Script to convert an image file to SVG format using the potrace library.
"""

import asyncio
import os
import sys
from pathlib import Path

from PIL import Image


async def convert_to_svg(filename: str, blacklevel=0.5) -> str:
    from potrace import Bitmap, POTRACE_TURNPOLICY_MINORITY  # `potracer` library
    """
    Convert an image file to SVG format using the potrace library.

    Args:
        filename (str): The path to the input image file.
        blacklevel (float): The black level threshold for the image. Defaults to 0.5.

    Returns:
        str: The path to the generated SVG file.
    """

    chat_dir = Path(os.environ.get("CHAT_DIR", Path.cwd()))
    image_path = chat_dir / filename
    image = Image.open(image_path)

    bm = Bitmap(image, blacklevel=blacklevel)
    plist = bm.trace(
        turdsize=2,
        turnpolicy=POTRACE_TURNPOLICY_MINORITY,
        alphamax=1,
        opticurve=False,
        opttolerance=0.2,
    )

    input_path = Path(image_path)
    svg_path = input_path.with_suffix(".svg")

    with open(svg_path, "w") as fp:
        fp.write(
            f'''<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{image.width}" height="{image.height}" viewBox="0 0 {image.width} {image.height}">''')
        parts = []
        for curve in plist:
            fs = curve.start_point
            parts.append(f"M{fs.x},{fs.y}")
            for segment in curve.segments:
                if segment.is_corner:
                    a = segment.c
                    b = segment.end_point
                    parts.append(f"L{a.x},{a.y}L{b.x},{b.y}")
                else:
                    a = segment.c1
                    b = segment.c2
                    c = segment.end_point
                    parts.append(f"C{a.x},{a.y} {b.x},{b.y} {c.x},{c.y}")
            parts.append("z")
        fp.write(f'<path stroke="none" fill="black" fill-rule="evenodd" d="{"".join(parts)}"/>')
        fp.write("</svg>")

    return str(svg_path)


if __name__ == '__main__':
    svg_file = asyncio.run(convert_to_svg(sys.argv[1]))
    print(f"SVG file generated: {svg_file}")
