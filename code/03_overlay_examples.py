"""
03_overlay_examples.py
Creates overlay images showing raw TIFs with masks overlaid for visual sanity check.
"""

import os
import cv2
import glob

DATA_DIR = "data"
MASKS_DIR = "masks"
OVERLAYS_DIR = "overlays"

os.makedirs(OVERLAYS_DIR, exist_ok=True)

def overlay():
    for dataset in sorted(os.listdir(DATA_DIR)):
        ds_path = os.path.join(DATA_DIR, dataset)
        if not os.path.isdir(ds_path) or not dataset.endswith(("rapid", "rate")):
            continue

        mask_dir = os.path.join(MASKS_DIR, dataset)
        if not os.path.exists(mask_dir):
            print(f"[skip] no masks in {dataset}")
            continue

        out_dir = os.path.join(OVERLAYS_DIR, dataset)
        os.makedirs(out_dir, exist_ok=True)

        tifs = glob.glob(os.path.join(ds_path, "*.tif"))
        count = 0
        for tif in tifs[:20]:  # limit to 20 examples
            base = os.path.splitext(os.path.basename(tif))[0]
            mask_file = os.path.join(mask_dir, base + "_mask.png")
            if not os.path.exists(mask_file):
                continue

            img = cv2.imread(tif)
            mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
            overlay = img.copy()
            overlay[mask > 0] = (0, 0, 255)  # red mask overlay
            out_file = os.path.join(out_dir, base + "_overlay.png")
            cv2.imwrite(out_file, overlay)
            count += 1

        print(f"[ok] {dataset}: wrote {count} overlays to {out_dir}")

if __name__ == "__main__":
    overlay()
