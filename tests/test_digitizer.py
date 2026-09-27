import os
import tempfile

import cv2
import numpy as np

from mazeint_digitizer.core import convert, load_mask


def test_load_mask_preserves_transparent_logo_shape():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "transparent_logo.png")
        img = np.zeros((80, 120, 4), dtype=np.uint8)
        img[:, :, 3] = 0
        cv2.rectangle(img, (18, 18), (76, 62), (255, 255, 255, 255), thickness=-1)
        cv2.circle(img, (95, 36), 18, (255, 255, 255, 255), thickness=-1)
        cv2.imwrite(path, img)

        mask = load_mask(path)
        ys, xs = np.where(mask > 0)

        assert mask.shape == (80, 120)
        assert xs.size > 0
        assert xs.min() <= 18 and ys.min() <= 18
        assert xs.max() >= 95 and ys.max() >= 62


def test_convert_creates_embroidery_files_from_simple_logo():
    with tempfile.TemporaryDirectory() as tmpdir:
        img = np.zeros((80, 120), dtype=np.uint8)
        cv2.rectangle(img, (15, 15), (105, 65), 255, thickness=8)
        path = os.path.join(tmpdir, "logo.png")
        cv2.imwrite(path, img)

        out_prefix = os.path.join(tmpdir, "digitized")
        paths, pattern, n_thin, n_thick = convert(
            path,
            out_prefix,
            out_width_mm=50.0,
            row_spacing_mm=0.8,
            angle_deg=45.0,
            thin_threshold_mm=1.0,
            running_stitch_len_mm=2.0,
            underlay=False,
            thread_colors=("#ff0000",),
        )

        assert len(paths) >= 1
        assert all(os.path.exists(p) for p in paths)
        assert os.path.exists(f"{out_prefix}_preview.png")
        assert pattern.count_stitches() > 0
        assert n_thin + n_thick >= 1


def test_convert_centers_design_coordinates_around_origin():
    with tempfile.TemporaryDirectory() as tmpdir:
        img = np.zeros((100, 200), dtype=np.uint8)
        cv2.rectangle(img, (40, 30), (160, 70), 255, thickness=10)
        path = os.path.join(tmpdir, "offset_logo.png")
        cv2.imwrite(path, img)

        out_prefix = os.path.join(tmpdir, "centered")
        _, pattern, _, _ = convert(
            path,
            out_prefix,
            out_width_mm=80.0,
            row_spacing_mm=1.0,
            angle_deg=0.0,
            thin_threshold_mm=1.0,
            running_stitch_len_mm=2.0,
            underlay=False,
            thread_colors=("#000000",),
        )

        stitches = list(pattern.get_as_stitches())
        xs = [stitch[1] for stitch in stitches]
        ys = [stitch[2] for stitch in stitches]
        assert xs and ys
        assert abs((max(xs) + min(xs)) / 2.0) < 0.15 * max(1.0, max(xs) - min(xs))
        assert abs((max(ys) + min(ys)) / 2.0) < 0.15 * max(1.0, max(ys) - min(ys))
