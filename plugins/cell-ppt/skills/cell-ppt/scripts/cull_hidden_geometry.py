#!/usr/bin/env python3
"""Remove fully hidden or exact duplicate atoms from a Cell_ppt cache."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

import prepare_geometry_cache as cache_builder


def expand_drawing_paths(atoms):
    """Make the culling unit identical to the native shape shown in PowerPoint."""
    expanded = []
    for atom in atoms:
        subpaths = atom.get("subpaths") or []
        if atom.get("kind") == "text" or len(subpaths) <= 1:
            expanded.append(atom)
            continue
        paint_parts = atom.get("paintParts") or []
        for subpath_index, subpath in enumerate(subpaths):
            unit = copy.deepcopy(atom)
            unit["subpaths"] = [subpath]
            unit["sourceSubpathIndex"] = subpath_index
            unit["objectName"] = f"{atom.get('objectName', 'PATH')}_SUB_{subpath_index:03d}"
            unit["complexity"] = len(subpath.get("points") or [])
            if paint_parts:
                selected = paint_parts[subpath_index] if len(paint_parts) == len(subpaths) else paint_parts[0]
                unit["paintParts"] = [copy.deepcopy(selected)]
            expanded.append(unit)
    return expanded


def cubic(p0, p1, p2, p3, steps=12):
    points = []
    for index in range(steps + 1):
        t = index / steps
        u = 1.0 - t
        points.append((
            u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1],
        ))
    return points


def same_point(a, b):
    return abs(a[0] - b[0]) < 1e-7 and abs(a[1] - b[1]) < 1e-7


def flatten_subpath(subpath):
    source = subpath.get("points", [])
    if len(source) < 2:
        return []
    output = [tuple(source[0]["a"])]
    segment_count = len(source) if subpath.get("closed") else len(source) - 1
    for index in range(segment_count):
        current = source[index]
        following = source[(index + 1) % len(source)]
        p0 = tuple(current["a"])
        p1 = tuple(current["r"])
        p2 = tuple(following["l"])
        p3 = tuple(following["a"])
        if same_point(p0, p1) and same_point(p2, p3):
            segment = [p0, p3]
        else:
            segment = cubic(p0, p1, p2, p3)
        output.extend(segment[1:])
    return output


def safe_polygon(points):
    if len(points) < 4:
        return None
    try:
        geometry = Polygon(points)
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        return geometry if not geometry.is_empty else None
    except Exception:
        return None


def atom_geometry(atom):
    if atom.get("kind") == "text":
        return None, None
    paint_parts = atom.get("paintParts") or []
    if not paint_parts:
        return None, None
    paint = paint_parts[0]
    rendered = []
    opaque = []
    opacity = float(paint.get("opacity", 100.0))
    for subpath in atom.get("subpaths", []):
        points = flatten_subpath(subpath)
        if len(points) < 2:
            continue
        if paint.get("filled") and subpath.get("closed"):
            polygon = safe_polygon(points)
            if polygon is not None:
                rendered.append(polygon)
                if opacity >= 99.999:
                    opaque.append(polygon)
        if paint.get("stroked"):
            try:
                line = LineString(points)
                width = max(0.01, float(paint.get("strokeWidth", 1.0)))
                stroke = line.buffer(width / 2.0, cap_style=1, join_style=1)
                if not stroke.is_empty:
                    rendered.append(stroke)
                    if opacity >= 99.999:
                        opaque.append(stroke)
            except Exception:
                pass
    visual = unary_union(rendered) if rendered else None
    # Compound subpaths can encode holes. Do not let an approximation of those
    # paths hide lower objects, but they may still be culled by later coverage.
    cover = unary_union(opaque) if opaque and len(atom.get("subpaths", [])) == 1 else None
    return visual, cover


def signature(atom):
    payload = {
        "kind": atom.get("kind"),
        "subpaths": atom.get("subpaths"),
        "paintParts": atom.get("paintParts"),
        "text": atom.get("text"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--visible-ratio", type=float, default=1e-6)
    args = parser.parse_args()

    cache_path = Path(args.cache).resolve()
    state_path = Path(args.state).resolve()
    cache = json.loads(cache_path.read_text(encoding="utf-8-sig"))
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    source_atoms = cache.get("atoms", [])
    atoms = expand_drawing_paths(source_atoms)
    keep = [True] * len(atoms)
    coverage = None
    seen = set()
    culled = []

    for position in range(len(atoms) - 1, -1, -1):
        atom = atoms[position]
        atom_signature = signature(atom)
        if atom_signature in seen:
            keep[position] = False
            culled.append({"position": position, "source_index": atom.get("index"), "reason": "exact_duplicate"})
            continue
        seen.add(atom_signature)
        visual, opaque_cover = atom_geometry(atom)
        if visual is not None and coverage is not None and not visual.is_empty:
            visible = visual.difference(coverage)
            denominator = max(float(visual.area), 1e-9)
            if visible.is_empty or float(visible.area) / denominator <= args.visible_ratio:
                keep[position] = False
                culled.append({"position": position, "source_index": atom.get("index"), "reason": "fully_occluded"})
                continue
        if opaque_cover is not None and not opaque_cover.is_empty:
            coverage = opaque_cover if coverage is None else unary_union([coverage, opaque_cover])

    kept_atoms = [atom for index, atom in enumerate(atoms) if keep[index]]
    if not kept_atoms:
        raise ValueError("Visibility culling removed every atom")
    batches = cache_builder.build_batches(
        kept_atoms,
        str(cache["job_id"]),
        int(cache["min_batch_size"]),
        int(cache["max_batch_size"]),
        int(cache["complex_point_threshold"]),
        int(cache["max_batch_points"]),
    )
    cache_builder.validate_batch_contract(
        batches,
        kept_atoms,
        int(cache["min_batch_size"]),
        int(cache["max_batch_size"]),
        int(cache["complex_point_threshold"]),
    )
    cache["source_total_atoms"] = len(source_atoms)
    cache["source_total_drawing_paths"] = len(atoms)
    cache["culled_atom_count"] = len(atoms) - len(kept_atoms)
    cache["culled_atoms"] = sorted(culled, key=lambda item: item["position"])
    cache["atoms"] = kept_atoms
    cache["total_atoms"] = len(kept_atoms)
    cache["batches"] = batches
    write_json(cache_path, cache)

    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state["total_atoms"] = len(kept_atoms)
    state["cache_sha256"] = sha256_file(cache_path)
    state["batches"] = [
        {
            "index": batch["index"],
            "group_name": batch["group_name"],
            "atom_indices": batch["atom_indices"],
            "atomic_count": batch["atomic_count"],
            "kind": batch["kind"],
            "completed": False,
            "completed_at": None,
            "attempts": 0,
            "last_error": None,
        }
        for batch in batches
    ]
    write_json(state_path, state)
    print(json.dumps({
        "ok": True,
        "source_atoms": len(source_atoms),
        "source_drawing_paths": len(atoms),
        "kept_atoms": len(kept_atoms),
        "culled_atoms": len(atoms) - len(kept_atoms),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
