#!/usr/bin/env python3
"""Generate home.pgm deterministically from the collision geometry in home/model.sdf.

Only static collision footprints that intersect the navigation plane are rasterized.
The floor is intentionally ignored. The output is an ASCII PGM (P2), which Nav2
map_server can read and which stays easy to inspect and reproduce.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

RESOLUTION = 0.05
ORIGIN_X = -13.0
ORIGIN_Y = -10.0
WIDTH_M = 26.0
HEIGHT_M = 20.0
WIDTH = int(round(WIDTH_M / RESOLUTION))
HEIGHT = int(round(HEIGHT_M / RESOLUTION))


def parse_pose(text: str | None) -> tuple[float, float, float, float, float, float]:
    values = [float(v) for v in (text or "0 0 0 0 0 0").split()]
    values += [0.0] * (6 - len(values))
    return tuple(values[:6])


def world_to_pixel(x: float, y: float) -> tuple[int, int]:
    col = int(math.floor((x - ORIGIN_X) / RESOLUTION))
    # PGM row zero is the top of the image; map origin is lower-left.
    row_from_bottom = int(math.floor((y - ORIGIN_Y) / RESOLUTION))
    row = HEIGHT - 1 - row_from_bottom
    return col, row


def mark_box(grid: list[bytearray], cx: float, cy: float, sx: float, sy: float) -> None:
    x0, x1 = cx - sx / 2.0, cx + sx / 2.0
    y0, y1 = cy - sy / 2.0, cy + sy / 2.0
    c0, r1 = world_to_pixel(x0, y0)
    c1, r0 = world_to_pixel(x1, y1)
    c0, c1 = max(0, min(c0, c1)), min(WIDTH - 1, max(c0, c1))
    r0, r1 = max(0, min(r0, r1)), min(HEIGHT - 1, max(r0, r1))
    for row in range(r0, r1 + 1):
        grid[row][c0:c1 + 1] = b"\x00" * (c1 - c0 + 1)


def mark_circle(grid: list[bytearray], cx: float, cy: float, radius: float) -> None:
    c0, r1 = world_to_pixel(cx - radius, cy - radius)
    c1, r0 = world_to_pixel(cx + radius, cy + radius)
    c0, c1 = max(0, min(c0, c1)), min(WIDTH - 1, max(c0, c1))
    r0, r1 = max(0, min(r0, r1)), min(HEIGHT - 1, max(r0, r1))
    rr = radius * radius
    for row in range(r0, r1 + 1):
        y = ORIGIN_Y + (HEIGHT - row - 0.5) * RESOLUTION
        for col in range(c0, c1 + 1):
            x = ORIGIN_X + (col + 0.5) * RESOLUTION
            if (x - cx) ** 2 + (y - cy) ** 2 <= rr:
                grid[row][col] = 0


def generate(sdf_path: Path, output_path: Path) -> None:
    root = ET.parse(sdf_path).getroot()
    model = root.find("model")
    if model is None:
        raise RuntimeError("SDF has no <model>")

    grid = [bytearray([254]) * WIDTH for _ in range(HEIGHT)]

    for link in model.findall("link"):
        if link.get("name") == "floor":
            continue
        lx, ly, _lz, _rr, _rp, lyaw = parse_pose(link.findtext("pose"))
        if abs(lyaw) > 1e-9:
            raise RuntimeError(f"Rotated link not supported by map generator: {link.get('name')}")

        collision = link.find("collision")
        if collision is None:
            continue
        geometry = collision.find("geometry")
        if geometry is None:
            continue

        box = geometry.find("box")
        cylinder = geometry.find("cylinder")
        if box is not None:
            size = [float(v) for v in box.findtext("size", "").split()]
            if len(size) != 3:
                raise RuntimeError(f"Invalid box size in {link.get('name')}")
            mark_box(grid, lx, ly, size[0], size[1])
        elif cylinder is not None:
            radius = float(cylinder.findtext("radius", "0"))
            mark_circle(grid, lx, ly, radius)
        else:
            raise RuntimeError(f"Unsupported collision geometry in {link.get('name')}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as stream:
        stream.write(f"P5\n{WIDTH} {HEIGHT}\n255\n".encode("ascii"))
        for row in grid:
            stream.write(row)

    print(f"Generated {output_path} ({WIDTH}x{HEIGHT}, {RESOLUTION:.2f} m/cell)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.sdf, args.output)


if __name__ == "__main__":
    main()
