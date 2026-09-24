#!/usr/bin/env python3
"""
digitize_v2.py — auto-digitizer with stitch-type routing.

Improvements over v1:
  - Classifies each shape as THIN (ring outlines, small text strokes) or
    THICK (bold letterforms, fills) based on estimated stroke width.
  - THIN shapes  -> skeletonized centerline + running stitch (proper
                     technique for strokes under ~1.4mm; fill stitch on
                     something that narrow just makes a blob).
  - THICK shapes -> zigzag fill stitch, with an optional inset underlay
                     pass first (stabilizes the fabric before the top fill,
                     standard digitizing practice).
  - Configurable via CLI: width, row spacing, angle, thin threshold,
    running stitch length, underlay on/off.

Still an auto-digitizer, not a hand digitizer -- good enough to test/sew a
proof, not a substitute for a pro on a final production file. Open the
output in Ink/Stitch to preview/tweak before sending to a machine.

pyembroidery internal coordinate unit = 0.1mm.
"""
import sys
import argparse
import numpy as np
import cv2
from shapely.geometry import Polygon, LineString
from shapely.affinity import affine_transform
import pyembroidery
from pyembroidery import EmbPattern, STITCH, JUMP, TRIM, COLOR_CHANGE, END


# ---------- image -> polygons ----------

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
            # buffer(0) on a self-intersecting shape can split it into a
            # MultiPolygon -- flatten that into separate simple polygons so
            # every downstream step can assume "poly.exterior" exists.
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
    """Widest point of the shape, via distance transform: 2 * max inscribed
    radius. This is robust to shapes with holes (letter counters), unlike
    an area/perimeter ratio -- a letter's counters inflate its perimeter
    and would wrongly make area/perimeter say the whole letter is 'thin'.
    Using the *widest* point means a letter with any bold region gets
    filled; only genuinely thin strokes (ring outlines, hairline text)
    get routed to running stitch."""
    if local_mask is None:
        return 0.0
    dist = cv2.distanceTransform(local_mask, cv2.DIST_L2, 5)
    return 2.0 * float(dist.max())


# ---------- thick shapes: zigzag fill ----------

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
    """Single inset running-stitch pass just inside the boundary, to tack
    the fabric down before the top fill (standard digitizing practice)."""
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


# ---------- thin shapes: skeleton + running stitch ----------

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
    """Skeletonize a thin shape's mask, then greedily chain the skeleton
    pixels into a travel order, resampled to ~step_px spacing. Large gaps
    between chained points start a new segment (returned separately) so we
    JUMP rather than stitch across empty space."""
    skel = cv2.ximgproc.thinning(mask)
    ys, xs = np.nonzero(skel)
    if len(xs) < 2:
        return []
    pts = list(zip(xs.tolist(), ys.tolist()))

    # greedy nearest-neighbor chain (fine for the pixel counts small text
    # produces; good enough for an auto-digitizer)
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

    # split into segments where consecutive chained points are far apart
    # (that means the chain jumped between disconnected skeleton branches)
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

    # resample each segment to even step spacing (arc-length)
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


# ---------- pattern assembly ----------

def build_pattern(mask, out_width_mm=100.0, row_spacing_mm=0.35, angle_deg=45.0,
                   thin_threshold_mm=1.4, running_stitch_len_mm=2.2,
                   underlay=True, underlay_inset_mm=0.4):
    h, w = mask.shape
    px_to_units = (out_width_mm * 10.0) / w   # 0.1mm units
    units_per_mm = 10.0
    px_per_mm = units_per_mm / px_to_units

    row_spacing_px = row_spacing_mm * px_per_mm
    thin_threshold_px = thin_threshold_mm * px_per_mm
    running_step_px = running_stitch_len_mm * px_per_mm
    underlay_inset_px = underlay_inset_mm * px_per_mm

    polys = mask_to_polygons(mask)
    if not polys:
        raise ValueError("No shapes found in image after thresholding.")

    pattern = EmbPattern()
    n_thin = n_thick = 0

    def emit_path(path_px, first_of_shape_start):
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

        if width_px < thin_threshold_px:
            n_thin += 1
            if local_mask is None:
                continue
            segments = skeleton_order_path(local_mask, ox, oy, running_step_px)
            for seg in segments:
                if len(seg) < 2:
                    continue
                emit_path(seg, True)
                pattern.add_command(TRIM)
        else:
            n_thick += 1
            if underlay:
                u_path = underlay_path(poly, underlay_inset_px)
                if len(u_path) >= 2:
                    emit_path(u_path, True)
                    pattern.add_command(TRIM)
            fill_path = scanline_fill(poly, row_spacing_px, angle_deg)
            if len(fill_path) >= 2:
                emit_path(fill_path, True)

    pattern.add_command(END)
    return pattern, n_thin, n_thick


def convert(image_path, out_prefix, **kwargs):
    mask = load_mask(image_path)
    pattern, n_thin, n_thick = build_pattern(mask, **kwargs)
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
        paths.append(outpath)
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
        args.image, args.out_prefix,
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
