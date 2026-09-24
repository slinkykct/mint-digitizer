import os
import tempfile

import cv2
import numpy as np

from mazeint_digitizer.core import convert


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
        )

        assert len(paths) >= 1
        assert all(os.path.exists(p) for p in paths)
        assert pattern.count_stitches() > 0
        assert n_thin + n_thick >= 1
