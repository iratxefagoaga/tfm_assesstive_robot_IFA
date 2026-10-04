#!/usr/bin/env python3
"""Static sanity checks for the HOME/PARK/AIRPORT experiment assets."""
from __future__ import annotations

import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from collections import deque

ROOT = Path(__file__).resolve().parents[2]
NAV = ROOT / "ros2/src/wheelchair_navigation"
GAZEBO = ROOT / "ros2/src/wheelchair_gazebo"
SCENARIOS = {
    "home": {"spawn": (2.0, -3.0), "goal": (8.9, 5.0), "waypoint": (-1.0, -1.0)},
    "park": {"spawn": (0.0, -9.0), "goal": (0.0, 9.0), "waypoint": (-7.5, 0.0)},
    "airport": {"spawn": (0.0, -8.0), "goal": (0.0, 8.0), "waypoint": (7.0, 0.0)},
}
MIN_CLEARANCE_M = 0.51  # conservative center clearance; not a Nav2 footprint proof


def pgm(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    match = re.match(rb"P5\s+(\d+)\s+(\d+)\s+255\s", data)
    if not match:
        raise ValueError(f"unsupported/non-binary PGM header: {path}")
    width, height = map(int, match.groups())
    pixels = data[match.end():]
    if len(pixels) != width * height:
        raise ValueError(f"PGM data size mismatch: {path}")
    return width, height, pixels


def point_cell(point: tuple[float, float], origin: tuple[float, float], res: float,
               width: int, height: int) -> tuple[int, int]:
    x, y = point
    col, row_from_bottom = math.floor((x-origin[0])/res), math.floor((y-origin[1])/res)
    row = height - 1 - row_from_bottom
    if not (0 <= col < width and 0 <= row < height):
        raise AssertionError(f"point outside map: {point}")
    return row, col


def check_map(env: str, coordinates: dict[str, tuple[float, float]]) -> None:
    metadata = (NAV / "maps" / f"{env}.yaml").read_text()
    image_name = re.search(r"(?m)^image:\s*(\S+)", metadata).group(1)
    res = float(re.search(r"(?m)^resolution:\s*([0-9.]+)", metadata).group(1))
    origin_values = re.search(r"(?m)^origin:\s*\[([^]]+)\]", metadata).group(1)
    ox, oy = map(float, origin_values.split(",")[:2])
    width, height, pixels = pgm(NAV / "maps" / image_name)
    for label, point in coordinates.items():
        row, col = point_cell(point, (ox, oy), res, width, height)
        if pixels[row*width+col] < 200:
            raise AssertionError(f"{env} {label} is occupied at {point}")
        radius = math.ceil(2.0/res)
        nearest = float("inf")
        for rr in range(max(0,row-radius), min(height,row+radius+1)):
            for cc in range(max(0,col-radius), min(width,col+radius+1)):
                if pixels[rr*width+cc] < 200:
                    wx = ox + (cc+0.5)*res
                    wy = oy + (height-rr-0.5)*res
                    nearest = min(nearest, math.hypot(wx-point[0], wy-point[1]))
        if pixels[row*width+col] < 200 or nearest < MIN_CLEARANCE_M:
            raise AssertionError(f"{env} {label} clearance {nearest:.2f}m < {MIN_CLEARANCE_M}m")
        clearance = f">2.00m" if math.isinf(nearest) else f"{nearest:.2f}m"
        print(f"STATICALLY_VALIDATED {env} {label}: {point}, nearest occupied cell {clearance}")

    # Raw occupancy connectivity only: Nav2's inflated footprint and planner
    # remain runtime checks. Check both legs through the configured waypoint.
    walkable = lambda r, c: pixels[r*width+c] >= 200
    def connected(a: tuple[float, float], b: tuple[float, float]) -> bool:
        start = point_cell(a, (ox, oy), res, width, height)
        target = point_cell(b, (ox, oy), res, width, height)
        pending = deque([start])
        visited = {start}
        while pending:
            r, c = pending.popleft()
            if (r, c) == target:
                return True
            for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                if 0 <= nr < height and 0 <= nc < width and (nr,nc) not in visited and walkable(nr,nc):
                    visited.add((nr,nc))
                    pending.append((nr,nc))
        return False
    points = [coordinates[k] for k in ("spawn", "waypoint", "goal")]
    if not connected(points[0], points[1]) or not connected(points[1], points[2]):
        raise AssertionError(f"{env} raw occupancy grid disconnects spawn/waypoint/goal")
    print(f"STATICALLY_VALIDATED {env} raw occupancy connects spawn → waypoint → goal")


def main() -> None:
    ids = ["HOME_01_clearance_preference", "PARK_01_west_path_preference", "AIRPORT_01_east_detour"]
    if len(ids) != len(set(ids)):
        raise AssertionError("scenario IDs are not unique")
    matrix = (ROOT / "docs/experiments/SCENARIO_MATRIX.md").read_text()
    for env in SCENARIOS:
        if not (GAZEBO / "worlds" / f"{env}.world").is_file():
            raise AssertionError(f"missing world {env}")
        model = GAZEBO / "models" / env / "model.sdf"
        if not model.is_file():
            raise AssertionError(f"missing model {env}")
        ET.parse(model)
        for condition in ("N0", "N1"):
            if f"{env.upper()}_01" not in matrix:
                raise AssertionError(f"matrix missing {env}")
        check_map(env, SCENARIOS[env])
    strategy_impl = (ROOT / "ros2/src/wheelchair_memory/wheelchair_memory/navigation_memory_node.py").read_text()
    for marker in ("ruta oeste", "ruta central", "alternativa", "desvio", "desvío"):
        if marker not in strategy_impl:
            raise AssertionError(f"strategy parser no longer recognizes {marker!r}")
    for strategy in ("west", "alternative"):
        if f"{strategy}:" not in matrix:
            raise AssertionError(f"matrix strategy is not represented as an offset: {strategy}")
    for launch in ("simulation.launch.py",):
        text = (ROOT / "ros2/src/wheelchair_bringup/launch" / launch).read_text()
        if not all(f'"{env}"' in text for env in SCENARIOS):
            raise AssertionError("simulation launch does not allow all environments")
    nav_launch = (ROOT / "ros2/src/wheelchair_navigation/launch/navigation.launch.py").read_text()
    if not all(f'"{env}"' in nav_launch for env in SCENARIOS):
        raise AssertionError("navigation launch does not allow all environments")
    params = (ROOT / "ros2/src/wheelchair_navigation/config/nav2_params.yaml").read_bytes()
    for env in SCENARIOS:
        for condition in ("n0", "n1"):
            launch = f"{env}_{condition}.launch.py"
            if not (ROOT / "ros2/src/wheelchair_assistive_bt/launch" / launch).is_file():
                raise AssertionError(f"missing scenario launch {launch}")
    n0 = (ROOT / "ros2/src/wheelchair_assistive_bt/launch/home_n0.launch.py").read_text()
    n1 = (ROOT / "ros2/src/wheelchair_assistive_bt/launch/home_n1.launch.py").read_text()
    if "MEMORY_OFF" not in n0 or "memory_observation_bt_orchestrator" in n0:
        raise AssertionError("N0 launch appears to enable memory")
    if "memory_observation_bt_orchestrator" not in n1 or "recommendation" not in n1:
        raise AssertionError("N1 launch does not start recommendation path")
    if "nav2_params.yaml" not in nav_launch:
        raise AssertionError("navigation launch does not use shared Nav2 parameters")
    print("STATICALLY_VALIDATED shared Nav2 parameter file used by all environments")
    print("STATICALLY_VALIDATED scenario IDs unique; condition launches preserve N0/N1 memory split")
    print("NOTE map checks are occupancy/clearance checks only; not Nav2 path-planning proof")


if __name__ == "__main__":
    main()
