#!/usr/bin/env python3
"""Core digitizing logic for MazeInt embroidery generation."""

import argparse
import os
from typing import Iterable, List, Tuple

import cv2
import numpy as np
import pyembroidery
from shapely.affinity import affine_transform
from shapely.geometry import LineString, Polygon

from pyembroidery import COLOR_CHANGE, END, EmbThread, JUMP, STITCH, TRIM, EmbPattern


def load_mask(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read {image_path}")
    _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(mask == 255) > 0.5:
        mask = cv2.bitwise_not(mask)
    return mask


def mask_to_polygons(mask, min_area_px=25):
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    hierarchy = hierarchy[0]
    polys = []
    for i, cnt in enumerate(contours):
        if hierarchy[i][3] != -1:
            continue
        if cv2.contourArea(cnt) < min_area_px:
            continue
        outer_pts = cnt.reshape(-1, 2)
        if len(outer_pts) < 3:
            continue
        holes = []
        child = hierarchy[i][2]
        while child != -1:
            hole_cnt = contours[child]
            if cv2.contourArea(hole_cnt) >= min_area_px:
                hpts = hole_cnt.reshape(-1, 2)
                if len(hpts) >= 3:
                    holes.append(hpts)
            child = hierarchy[child][0]
        try:
            poly = Polygon(outer_pts, holes=holes)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                continue
            if poly.geom_type == "MultiPolygon":
                for sub in poly.geoms:
                    if not sub.is_empty and sub.area >= min_area_px:
                        polys.append((sub, cnt, hierarchy[i]))
            elif poly.geom_type == "Polygon" and poly.area >= min_area_px:
                polys.append((poly, cnt, hierarchy[i]))
        except Exception:
            continue
    return polys


def estimate_max_width_px(local_mask):
    if local_mask is None:
        return 0.0
    dist = cv2.distanceTransform(local_mask, cv2.DIST_L2, 5)
    return 2.0 * float(dist.max())


def scanline_fill(poly, row_spacing_px, angle_deg=0.0):
    if poly.is_empty:
        return []
    theta = np.radians(angle_deg)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    rotated_poly = affine_transform(poly, [cos_t, sin_t, -sin_t, cos_t, 0, 0])
    minx, miny, maxx, maxy = rotated_poly.bounds
    y = miny + row_spacing_px / 2.0
    rows = []
    left_to_right = True
    while y <= maxy:
        line = LineString([(minx - 1, y), (maxx + 1, y)])
        inter = rotated_poly.intersection(line)
        segs = _flatten_segments(inter)
        segs.sort(key=lambda s: s[0][0])
        if not left_to_right:
            segs = segs[::-1]
        for a, b in segs:
            rows.extend([a, b] if left_to_right else [b, a])
        left_to_right = not left_to_right
        y += row_spacing_px

    def unrot(x, y):
        return x * cos_t - y * sin_t, x * sin_t + y * cos_t

    return [unrot(x, y) for x, y in rows]


def _flatten_segments(geom):
    segs = []
    if geom.is_empty:
        return segs
    if geom.geom_type == "LineString":
        c = list(geom.coords)
        if len(c) >= 2:
            segs.append((c[0], c[-1]))
    elif geom.geom_type in ("MultiLineString", "GeometryCollection"):
        for g in geom.geoms:
            segs.extend(_flatten_segments(g))
    return segs


def underlay_path(poly, inset_px):
    try:
        inset = poly.buffer(-inset_px)
    except Exception:
        return []
    if inset.is_empty:
        return []
    if inset.geom_type == "Polygon":
        polys = [inset]
    elif inset.geom_type == "MultiPolygon":
        polys = list(inset.geoms)
    else:
        return []
    path = []
    for p in polys:
        path.extend(list(p.exterior.coords))
    return path


def polygon_to_local_mask(poly, pad=3):
    minx, miny, maxx, maxy = poly.bounds
    minx, miny = int(np.floor(minx)) - pad, int(np.floor(miny)) - pad
    maxx, maxy = int(np.ceil(maxx)) + pad, int(np.ceil(maxy)) + pad
    w, h = maxx - minx, maxy - miny
    if w <= 0 or h <= 0:
        return None, None, None
    mask = np.zeros((h, w), dtype=np.uint8)
    ext = [(int(round(x - minx)), int(round(y - miny))) for x, y in poly.exterior.coords]
    cv2.fillPoly(mask, [np.array(ext, dtype=np.int32)], 255)
    for interior in poly.interiors:
        hole = [(int(round(x - minx)), int(round(y - miny))) for x, y in interior.coords]
        cv2.fillPoly(mask, [np.array(hole, dtype=np.int32)], 0)
    return mask, minx, miny


def skeleton_order_path(mask, offset_x, offset_y, step_px):
    skel = cv2.ximgproc.thinning(mask)
    ys, xs = np.nonzero(skel)
    if len(xs) < 2:
        return []
    pts = list(zip(xs.tolist(), ys.tolist()))

    pts_arr = np.array(pts, dtype=np.float32)
    used = np.zeros(len(pts_arr), dtype=bool)
    order = [0]
    used[0] = True
    cur = pts_arr[0]
    for _ in range(len(pts_arr) - 1):
        remaining_idx = np.where(~used)[0]
        d = np.sum((pts_arr[remaining_idx] - cur) ** 2, axis=1)
        nxt = remaining_idx[np.argmin(d)]
        order.append(nxt)
        used[nxt] = True
        cur = pts_arr[nxt]
    chained = pts_arr[order]

    max_gap = step_px * 4
    segments, seg = [], [chained[0]]
    for p in chained[1:]:
        if np.linalg.norm(p - seg[-1]) > max_gap:
            if len(seg) >= 2:
                segments.append(seg)
            seg = [p]
        else:
            seg.append(p)
    if len(seg) >= 2:
        segments.append(seg)

    out_segments = []
    for seg in segments:
        seg = np.array(seg)
        d = np.linalg.norm(np.diff(seg, axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(d)])
        total = cum[-1]
        if total < step_px:
            resampled = seg
        else:
            n = max(2, int(total // step_px))
            targets = np.linspace(0, total, n)
            resampled = np.stack([
                np.interp(targets, cum, seg[:, 0]),
                np.interp(targets, cum, seg[:, 1]),
            ], axis=1)
        pts_global = [(x + offset_x, y + offset_y) for x, y in resampled]
        out_segments.append(pts_global)
    return out_segments


def hex_to_bgr(hex_color):
    hex_color = (hex_color or "#000000").strip()
    if not hex_color.startswith("#"):
        hex_color = f"#{hex_color}"
    hex_color = hex_color[1:]
    if len(hex_color) == 3:
        hex_color = "".join(ch * 2 for ch in hex_color)
    if len(hex_color) != 6:
        return (0, 0, 0)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)


def normalize_thread_colors(thread_colors):
    if not thread_colors:
        return []
    colors = []
    for raw in thread_colors:
        if raw is None:
            continue
        color = str(raw).strip()
        if not color:
            continue
        if not color.startswith("#"):
            color = f"#{color}"
        if len(color) == 4:
            color = "#" + "".join(ch * 2 for ch in color[1:])
        try:
            int(color[1:], 16)
        except ValueError:
            continue
        if len(color) == 7:
            colors.append(color.lower())
    return colors or ["#1f2937"]


def apply_thread_colors(pattern, thread_colors):
    colors = normalize_thread_colors(thread_colors)
    for color in colors:
        thread = EmbThread()
        thread.set_hex_color(color)
        pattern.add_thread(thread)


def generate_preview(mask, outpath, thread_colors=None):
    if mask is None:
        return None
    height, width = mask.shape[:2]
    preview = np.full((height, width, 3), 255, dtype=np.uint8)
    binary = (mask > 0).astype(np.uint8) * 255
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        color = hex_to_bgr((normalize_thread_colors(thread_colors or ["#000000"]))[0])
        cv2.drawContours(preview, contours, -1, color, 1)
    ok = cv2.imwrite(outpath, preview)
    if not ok:
        raise ValueError(f"Could not write preview image to {outpath}")
    return outpath


def build_pattern(mask, out_width_mm=100.0, row_spacing_mm=0.35, angle_deg=45.0,
                   thin_threshold_mm=1.4, running_stitch_len_mm=2.2,
                   underlay=True, underlay_inset_mm=0.4, thread_colors=None,
                   use_exact_size=False):
    h, w = mask.shape
    if use_exact_size:
        out_width_mm = max(10.0, float(w) / 10.0)
    px_to_units = (out_width_mm * 10.0) / w
    px_per_mm = 10.0 / px_to_units
    row_spacing_px = row_spacing_mm * px_per_mm
    thin_threshold_px = thin_threshold_mm * px_per_mm
    running_step_px = running_stitch_len_mm * px_per_mm
    underlay_inset_px = underlay_inset_mm * px_per_mm

    polys = mask_to_polygons(mask)
    if not polys:
        raise ValueError("No shapes found in image after thresholding.")

    pattern = EmbPattern()
    apply_thread_colors(pattern, thread_colors)
    n_thin = n_thick = 0

    def emit_path(path_px):
        if len(path_px) < 2:
            return
        sx, sy = path_px[0]
        pattern.add_stitch_absolute(JUMP, sx * px_to_units, sy * px_to_units)
        for x, y in path_px:
            pattern.add_stitch_absolute(STITCH, x * px_to_units, y * px_to_units)

    first_shape = True
    for poly, cnt, hier in polys:
        local_mask, ox, oy = polygon_to_local_mask(poly)
        width_px = estimate_max_width_px(local_mask)
        if not first_shape:
            pattern.add_command(TRIM)
        first_shape = False

        if local_mask is None:
            continue

        if width_px < thin_threshold_px:
            n_thin += 1
            segments = skeleton_order_path(local_mask, ox, oy, running_step_px)
            for seg in segments:
                if len(seg) >= 2:
                    emit_path(seg)
                    pattern.add_command(TRIM)
        else:
            n_thick += 1
            if underlay:
                u_path = underlay_path(poly, underlay_inset_px)
                if len(u_path) >= 2:
                    emit_path(u_path)
                    pattern.add_command(TRIM)
            fill_path = scanline_fill(poly, row_spacing_px, angle_deg)
            if len(fill_path) >= 2:
                emit_path(fill_path)

    pattern.add_command(END)
    if pattern.count_stitches() == 0:
        raise ValueError("No stitch data generated from the selected artwork. Please use a cleaner, higher-contrast logo.")
    pattern.move_center_to_origin()
    return pattern, n_thin, n_thick


def convert(image_path, out_prefix, **kwargs):
    mask = load_mask(image_path)
    thread_colors = kwargs.pop("thread_colors", None)
    preview_path = kwargs.pop("preview_path", None)

    if kwargs.get("use_exact_size") is None:
        kwargs["use_exact_size"] = True
    if kwargs.get("out_width_mm") is None:
        kwargs["out_width_mm"] = max(10.0, float(mask.shape[1]) / 10.0)

    out_dir = os.path.dirname(out_prefix)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    pattern, n_thin, n_thick = build_pattern(mask, thread_colors=thread_colors, **kwargs)
    formats = {
        "dst": pyembroidery.write_dst,
        "pes": pyembroidery.write_pes,
        "jef": pyembroidery.write_jef,
        "exp": pyembroidery.write_exp,
    }
    paths = []
    for ext, writer in formats.items():
        outpath = f"{out_prefix}.{ext}"
        writer(pattern, outpath)
        if not os.path.exists(outpath):
            raise ValueError(f"Embroidery export failed while writing {outpath}")
        paths.append(outpath)

    final_preview = preview_path or f"{out_prefix}_preview.png"
    generate_preview(mask, final_preview, thread_colors)
    paths.append(final_preview)
    return paths, pattern, n_thin, n_thick


def main():
    ap = argparse.ArgumentParser(description="Auto-digitize a flat logo into embroidery stitch files.")
    ap.add_argument("image", help="input image path (flat, high-contrast logo works best)")
    ap.add_argument("out_prefix", help="output file prefix")
    ap.add_argument("--width-mm", type=float, default=100.0, help="output design width in mm (default 100)")
    ap.add_argument("--row-spacing-mm", type=float, default=0.35, help="fill stitch row spacing (default 0.35mm)")
    ap.add_argument("--angle", type=float, default=45.0, help="fill stitch angle in degrees (default 45)")
    ap.add_argument("--thin-threshold-mm", type=float, default=1.4,
                     help="shapes narrower than this use running stitch instead of fill (default 1.4mm)")
    ap.add_argument("--running-stitch-len-mm", type=float, default=2.2, help="running stitch length (default 2.2mm)")
    ap.add_argument("--no-underlay", action="store_true", help="disable underlay pass under fills")
    ap.add_argument("--underlay-inset-mm", type=float, default=0.4, help="underlay inset from edge (default 0.4mm)")
    args = ap.parse_args()

    paths, pattern, n_thin, n_thick = convert(
        args.image,
        args.out_prefix,
        out_width_mm=args.width_mm,
        row_spacing_mm=args.row_spacing_mm,
        angle_deg=args.angle,
        thin_threshold_mm=args.thin_threshold_mm,
        running_stitch_len_mm=args.running_stitch_len_mm,
        underlay=not args.no_underlay,
        underlay_inset_mm=args.underlay_inset_mm,
    )
    print("Wrote:", paths)
    print(f"Shapes: {n_thin} thin (running stitch), {n_thick} thick (fill stitch)")
    print("Stitch count:", pattern.count_stitches())


if __name__ == "__main__":
    main()
