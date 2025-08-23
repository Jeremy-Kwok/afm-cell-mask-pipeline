"""
02_make_masks.py
Generate binary masks from annotation JSONs for both RAPID and RATE datasets.

- RAPID:
    images: data/DN?-rapid/*.tif
    ann:    data/DN?-rapid/DN?-rapid_im_annotations.json
    (optional) vd: data/DN?-rapid/DN?-rapid_vd_annotations.json (ignored by default)
    matching: choose image for ('cell','meas') by exact meas -> meas-1 -> lowest for that cell

- RATE:
    images: data/DN?-rate/*.tif
    ann:    data/DN?-rate_annotations/*_im_annotations.json
    matching: stem-based exact -> meas-1 -> meas-2 -> meas+1 -> nearest for that cell

Outputs:
    masks/<dataset>/<image_stem>_mask.png
    overlays/<dataset>/<image_stem>_overlay.png (a few samples)
"""

from pathlib import Path
import json, re
import numpy as np
import cv2

# ---------------- Config ----------------
DATA_DIR      = Path("data_full")
MASKS_ROOT    = Path("masks")
OVERLAYS_ROOT = Path("overlays")
OVERLAYS      = True           # write a small sample of overlays
USE_VD_FILTER = False          # if True (rapid only), require vd_annotations[key] == True
SAMPLE_OVERLAYS_PER_SET = 12   # cap overlays per dataset

TUPLE_KEY_RE = re.compile(r"\('(\d+)',\s*'(\d+)'\)")  # matches "('03','0001')"
IMG_EXTS = {".tif", ".tiff"}

# -------------- Helpers -----------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def rasterize_mask(h: int, w: int, polygons) -> np.ndarray:
    """polygons is a list of contours; each contour is [[x,y], [x,y], ...]."""
    mask = np.zeros((h, w), dtype=np.uint8)
    for poly in polygons or []:
        cnt = np.asarray(poly, dtype=np.int32).reshape(-1, 1, 2)
        if cnt.size >= 6:  # at least 3 points
            cv2.drawContours(mask, [cnt], -1, 255, thickness=-1)
    return mask

def find_images(folder: Path):
    for p in folder.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() not in IMG_EXTS:
            continue
        if "overlay" in p.stem.lower():
            continue
        yield p


# ONLY TAKE .tif/.tiff files not in masks/ or overlays/
def index_images_by_stem(img_folder: Path) -> dict[str, Path]:
    allowed = {".tif", ".tiff"}
    idx: dict[str, Path] = {}
    for img_path in sorted(img_folder.iterdir()):
        if not img_path.is_file():
            continue
        if img_path.suffix.lower() not in allowed:
            continue
        if img_path.parent.name in ("masks", "overlays"):
            continue
        if "overlay" in img_path.stem.lower():
            continue
        idx[img_path.stem.lower()] = img_path
    return idx


# ---- Rapid-specific image chooser (by cell, then meas) ----
def list_images_for_cell(folder: Path, cell_str: str):
    by_meas = {}
    prefix = f"cell{int(cell_str):02d}meas"
    for p in find_images(folder):
        s = p.stem.lower()
        if s.startswith(prefix):
            m = re.search(r"meas(\d+)", s)
            if m:
                by_meas[int(m.group(1))] = p
    return by_meas  # {meas_int: Path}

def choose_rapid_image(folder: Path, cell_str: str, meas_str: str):
    annot_meas = int(meas_str)
    by_meas = list_images_for_cell(folder, cell_str)
    if not by_meas:
        return None
    if annot_meas in by_meas:
        return by_meas[annot_meas]
    if (annot_meas - 1) in by_meas:    # common 0001 -> 0000
        return by_meas[annot_meas - 1]
    # fallback: smallest meas for that cell
    return by_meas[min(by_meas.keys())]

# ---- Rate-specific image chooser (tolerant) ----
def stem_for(cell_str: str, meas_str: str) -> str:
    return f"cell{int(cell_str):02d}meas{int(meas_str):04d}".lower()

def choose_rate_image(stem: str, idx: dict):
    # exact
    if stem in idx:
        return idx[stem]
    # try off-by patterns
    m = re.search(r"cell(\d+)meas(\d+)", stem)
    if not m:
        return None
    cell, meas = int(m.group(1)), int(m.group(2))
    for delta in (-1, -2, +1):
        s2 = f"cell{cell:02d}meas{meas+delta:04d}"
        if s2 in idx:
            return idx[s2]
    # nearest for that cell
    per_cell = sorted(
        (int(re.search(r"meas(\d+)", k).group(1)), k)
        for k in idx.keys()
        if k.startswith(f"cell{cell:02d}meas")
    )
    if per_cell:
        nearest_key = min(per_cell, key=lambda t: abs(t[0] - meas))[1]
        return idx[nearest_key]
    return None

# -------------- Processors ----------------
def process_rapid(ds_folder: Path):
    dataset = ds_folder.name   # e.g. DN1-rapid
    
    # NEW
    im_path_root = ds_folder / f"{dataset}_im_annotations.json"
    im_path_alt  = next(iter((ds_folder / "annotations").glob("*_im_annotations.json")), None)
    im_path      = im_path_root if im_path_root.exists() else im_path_alt
    if not im_path:
        print(f"[skip] no annotations for {dataset}")
        return
    im_ann = load_json(im_path) or {}

    vd_path_root = ds_folder / f"{dataset}_vd_annotations.json"
    vd_path_alt  = next(iter((ds_folder / "annotations").glob("*_vd_annotations.json")), None)
    vd_path      = vd_path_root if vd_path_root.exists() else vd_path_alt
    vd_ann       = load_json(vd_path) if (USE_VD_FILTER and vd_path and vd_path.exists()) else None

    # write outputs inside the dataset folder
    mask_dir = ds_folder / "masks"
    ensure_dir(mask_dir)
    ov_dir   = ds_folder / "overlays"
    ensure_dir(ov_dir)

    made = miss = skip = manual = 0
    ov_written = 0
    print(f"\n== {dataset} ==")

    for k, entry in im_ann.items():
        m = TUPLE_KEY_RE.fullmatch(k.strip())
        if not m:
            continue
        # entry must be a dict with selection & clickData
        if not isinstance(entry, dict) or entry.get("selection") != "manual":
            skip += 1
            continue
        if vd_ann is not None and not vd_ann.get(k, False):
            skip += 1
            continue

        cell_str, meas_str = m.group(1), m.group(2)
        img_path = choose_rapid_image(ds_folder, cell_str, meas_str)
        if not img_path:
            miss += 1; print("  [miss-img]", k); continue

        raw = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if raw is None:
            miss += 1; print("  [err] unreadable:", img_path); continue

        H, W = raw.shape[:2]
        polys = entry.get("clickData", [])
        mask = rasterize_mask(H, W, polys)
        out = mask_dir / f"{img_path.stem}_mask.png"
        cv2.imwrite(str(out), mask)
        made += 1; manual += 1
        # small sample of overlays
        if OVERLAYS and ov_written < SAMPLE_OVERLAYS_PER_SET:
            ov = raw.copy()
            ov[mask > 0] = (0.5 * ov[mask > 0] + [0, 0, 255]).astype("uint8")
            cv2.imwrite(str(ov_dir / f"{img_path.stem}_overlay.png"), ov)
            ov_written += 1

    print(f"== {dataset}: wrote={made}; manual={manual}; skipped_nonmanual={skip}; missing_images={miss}")

def process_rate(img_folder: Path):
    dataset = img_folder.name   # e.g. DN1-rate

    # NEW
    ann_folder1 = img_folder.parent / f"{dataset}_annotations"
    ann_folder2 = img_folder / "annotations"

    ann_path = next(iter(ann_folder1.glob("*_im_annotations.json")), None) if ann_folder1.exists() else None
    if not ann_path and ann_folder1.exists():
        ann_path = next(iter(ann_folder1.glob("*.json")), None)
    if not ann_path and ann_folder2.exists():
        ann_path = next(iter(ann_folder2.glob("*_im_annotations.json")), None) \
                or next(iter(ann_folder2.glob("*.json")), None)
    if not ann_path:
        print(f"[skip] no annotations for {dataset}")
        return
    im_ann = load_json(ann_path) or {}
    idx    = index_images_by_stem(img_folder)


    # write outputs inside the dataset folder
    mask_dir = img_folder / "masks"
    ensure_dir(mask_dir)
    ov_dir   = img_folder / "overlays"
    ensure_dir(ov_dir)

    made = miss = skip = manual = 0
    ov_written = 0
    print(f"\n== {dataset} ==")

    for k, entry in im_ann.items():
        m = TUPLE_KEY_RE.fullmatch(k.strip())
        if not m:
            continue
        if not isinstance(entry, dict) or entry.get("selection") != "manual":
            skip += 1
            continue

        cell_str, meas_str = m.group(1), m.group(2)
        stem = stem_for(cell_str, meas_str)
        img_path = choose_rate_image(stem, idx)
        if not img_path:
            miss += 1; print("[miss-img]", k); continue

        raw = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if raw is None:
            miss += 1; print("[err] unreadable:", img_path); continue

        H, W = raw.shape[:2]
        polys = entry.get("clickData", [])
        mask = rasterize_mask(H, W, polys)
        out = mask_dir / f"{img_path.stem}_mask.png"
        cv2.imwrite(str(out), mask)
        made += 1; manual += 1

        if OVERLAYS and ov_written < SAMPLE_OVERLAYS_PER_SET:
            ov = raw.copy()
            ov[mask > 0] = (0.5 * ov[mask > 0] + [0, 0, 255]).astype("uint8")
            cv2.imwrite(str(ov_dir / f"{img_path.stem}_overlay.png"), ov)
            ov_written += 1

    print(f"== {dataset}: wrote={made}; manual={manual}; skipped_nonmanual={skip}; missing_images={miss}")

# -------------- Main --------------------
if __name__ == "__main__":
    # Iterate everything under data/
    for sub in sorted(DATA_DIR.iterdir()):
        if not sub.is_dir():
            continue
        name = sub.name
        if name.endswith("-rapid"):
            process_rapid(sub)
        elif name.endswith("-rate"):
            process_rate(sub)
        else:
            # skip DN?-force and *_annotations directories
            continue
