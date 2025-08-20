import os
import cv2
import numpy as np

DATA_ROOT = "data_full"

def generate_overlay(image, mask):
    overlay = image.copy()
    overlay[mask > 0] = [255, 0, 0]  # red mask overlay
    blended = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)
    return blended

for dataset in sorted(os.listdir(DATA_ROOT)):
    mask_dir = os.path.join(DATA_ROOT, dataset, "masks")
    overlay_dir = os.path.join(DATA_ROOT, dataset, "overlays")
    image_dir = os.path.join(DATA_ROOT, dataset)

    print(f"[check] Dataset: {dataset}")
    if not os.path.exists(mask_dir):
        print(f"[skip] No mask dir: {mask_dir}")
        continue

    os.makedirs(overlay_dir, exist_ok=True)
    mask_files = sorted(f for f in os.listdir(mask_dir) if f.endswith("_mask.png"))
    if not mask_files:
        print(f"[skip] No mask files in: {mask_dir}")
        continue

    for mask_file in mask_files:
        base = mask_file.replace("_mask.png", "")
        mask_path = os.path.join(mask_dir, mask_file)
        image_path = os.path.join(image_dir, f"{base}.tif")
        overlay_path = os.path.join(overlay_dir, f"{base}_overlay.png")

        print(f"[debug] Processing {base}...")

        if not os.path.exists(image_path):
            print(f"  [missing] Image not found: {image_path}")
            continue

        try:
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                print(f"  [fail] Could not read image: {image_path}")
                continue

            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                print(f"  [fail] Could not read mask: {mask_path}")
                continue

            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            overlay = generate_overlay(image_rgb, mask)
            cv2.imwrite(overlay_path, overlay)
            print(f"  [ok] Wrote overlay: {overlay_path}")
        except Exception as e:
            print(f"  [error] Failed to process {base}: {e}")