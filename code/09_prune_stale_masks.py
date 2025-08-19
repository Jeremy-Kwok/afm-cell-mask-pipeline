"""
09_prune_stale_masks.py
Remove mask files that don't correspond to a manual annotation key
(keeps the typical meas-1 fallback too).
"""

from pathlib import Path
import json, re

DATA_DIR = Path("data")
MASKS_DIR = Path("masks")

DATASET = "DN4-rapid"  # <-- change to the dataset you want to clean

folder = DATA_DIR / DATASET
mask_dir = MASKS_DIR / DATASET
ann_file = folder / f"{DATASET}_im_annotations.json"  # rapid stores im_annotations inside the dataset
ann_dir_rate = DATA_DIR / f"{DATASET}_annotations"     # rate stores annotations in a sibling *_annotations folder

if not ann_file.exists() and ann_dir_rate.exists():
    # rate: prefer *_im_annotations.json under *_annotations
    j = next(ann_dir_rate.glob("*_im_annotations.json"), None)
    if j: ann_file = j

if not ann_file or not ann_file.exists():
    raise SystemExit(f"[err] Could not find im_annotations for {DATASET}")

ann = json.loads(ann_file.read_text())

TUPLE = re.compile(r"\('(\d+)',\s*'(\d+)'\)")
def stem(cell, meas): return f"cell{int(cell):02d}meas{int(meas):04d}".lower()

# allowed stems from manual keys (+ meas-1 fallback)
allowed = set()
for k, v in ann.items():
    if isinstance(v, dict) and v.get("selection") == "manual":
        m = TUPLE.fullmatch(k.strip())
        if not m: 
            continue
        cell, meas = m.group(1), m.group(2)
        mv = int(meas)
        allowed.add(stem(cell, meas))
        allowed.add(stem(cell, f"{mv-1:04d}"))

removed = 0
if not mask_dir.exists():
    raise SystemExit(f"[err] No mask dir: {mask_dir}")

for mpath in mask_dir.glob("*_mask.png"):
    base = mpath.stem.replace("_mask", "").lower()
    if base not in allowed:
        print("[rm]", mpath.name)
        try:
            mpath.unlink()
            removed += 1
        except Exception as e:
            print("  could not remove:", e)

print(f"removed {removed} stale masks from {mask_dir}")
