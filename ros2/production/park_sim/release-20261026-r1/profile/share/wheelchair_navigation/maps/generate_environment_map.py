#!/usr/bin/env python3
"""Rasterize static, axis-aligned SDF collision geometry into binary PGM."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def pose_values(text: str | None) -> tuple[float, float, float, float, float, float]:
    values = [float(value) for value in (text or "0 0 0 0 0 0").split()]
    values.extend([0.0] * (6 - len(values)))
    return tuple(values[:6])


def generate(sdf: Path, output: Path, origin_x: float, origin_y: float,
             width_m: float, height_m: float, resolution: float) -> None:
    if resolution <= 0 or width_m <= 0 or height_m <= 0:
        raise ValueError("map dimensions and resolution must be positive")
    width, height = round(width_m / resolution), round(height_m / resolution)
    if abs(width * resolution - width_m) > 1e-8 or abs(height * resolution - height_m) > 1e-8:
        raise ValueError("map dimensions must be integer multiples of resolution")
    model = ET.parse(sdf).getroot().find("model")
    if model is None:
        raise ValueError(f"{sdf} has no top-level <model>")
    grid = [bytearray([254]) * width for _ in range(height)]

    def pixel(x: float, y: float) -> tuple[int, int]:
        col = math.floor((x - origin_x) / resolution)
        from_bottom = math.floor((y - origin_y) / resolution)
        return int(col), height - 1 - int(from_bottom)

    def fill_box(cx: float, cy: float, sx: float, sy: float) -> None:
        c0, r1 = pixel(cx - sx / 2, cy - sy / 2)
        c1, r0 = pixel(cx + sx / 2, cy + sy / 2)
        c0, c1 = max(0, min(c0, c1)), min(width - 1, max(c0, c1))
        r0, r1 = max(0, min(r0, r1)), min(height - 1, max(r0, r1))
        for row in range(r0, r1 + 1):
            grid[row][c0:c1 + 1] = b"\x00" * (c1 - c0 + 1)

    def fill_circle(cx: float, cy: float, radius: float) -> None:
        c0, r1 = pixel(cx - radius, cy - radius)
        c1, r0 = pixel(cx + radius, cy + radius)
        c0, c1 = max(0, min(c0, c1)), min(width - 1, max(c0, c1))
        r0, r1 = max(0, min(r0, r1)), min(height - 1, max(r0, r1))
        for row in range(r0, r1 + 1):
            y = origin_y + (height - row - 0.5) * resolution
            for col in range(c0, c1 + 1):
                x = origin_x + (col + 0.5) * resolution
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    grid[row][col] = 0

    for link in model.findall("link"):
        if link.get("name") == "floor":
            continue
        lx, ly, _z, _roll, _pitch, yaw = pose_values(link.findtext("pose"))
        if abs(yaw) > 1e-9:
            raise ValueError(f"rotated collision not supported: {link.get('name')}")
        collision = link.find("collision")
        geometry = collision.find("geometry") if collision is not None else None
        if geometry is None:
            continue
        clx, cly, _clz, _cr, _cp, cyaw = pose_values(collision.findtext("pose"))
        if abs(cyaw) > 1e-9:
            raise ValueError(f"rotated collision not supported: {link.get('name')}")
        lx += clx
        ly += cly
        box = geometry.find("box")
        cylinder = geometry.find("cylinder")
        if box is not None:
            size = [float(value) for value in box.findtext("size", "").split()]
            if len(size) != 3:
                raise ValueError(f"invalid box size: {link.get('name')}")
            fill_box(lx, ly, size[0], size[1])
        elif cylinder is not None:
            fill_circle(lx, ly, float(cylinder.findtext("radius", "0")))
        else:
            raise ValueError(f"unsupported map geometry: {link.get('name')}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as stream:
        stream.write(f"P5\n{width} {height}\n255\n".encode("ascii"))
        stream.writelines(grid)
    print(f"Generated {output}: {width}x{height} at {resolution:.3f} m/cell")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--origin-x", type=float, required=True)
    parser.add_argument("--origin-y", type=float, required=True)
    parser.add_argument("--width", type=float, required=True)
    parser.add_argument("--height", type=float, required=True)
    parser.add_argument("--resolution", type=float, default=0.05)
    args = parser.parse_args()
    generate(args.sdf, args.output, args.origin_x, args.origin_y,
             args.width, args.height, args.resolution)


if __name__ == "__main__":
    main()
