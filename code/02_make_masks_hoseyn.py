"""
02_make_masks_hoseyn.py
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
DATA_DIR      = Path("data")
MASKS_ROOT    = Path("masks")
OVERLAYS_ROOT = Path("overlays")
OVERLAYS      = True           # write a small sample of overlays
USE_VD_FILTER = False          # if True (rapid only), require vd_annotations[key] == True
SAMPLE_OVERLAYS_PER_SET = 12   # cap overlays per dataset

TUPLE_KEY_RE = re.compile(r"\('(\d+)',\s*'(\d+)'\)")  # matches "('03','0001')"
IMG_EXTS = {".tif",".tiff",".png",".jpg",".jpeg"}

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
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            yield p

def index_images_by_stem(folder: Path):
    return {p.stem.lower(): p for p in find_images(folder)}

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
    im_path = ds_folder / f"{dataset}_im_annotations.json"
    vd_path = ds_folder / f"{dataset}_vd_annotations.json"
    im_ann  = load_json(im_path) or {}
    vd_ann  = load_json(vd_path) if (USE_VD_FILTER and vd_path.exists()) else None

    mask_dir = MASKS_ROOT / dataset;     ensure_dir(mask_dir)
    ov_dir   = OVERLAYS_ROOT / dataset;  ensure_dir(ov_dir) if OVERLAYS else None

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
    ann_folder = img_folder.parent / f"{dataset}_annotations"
    # Prefer *_im_annotations.json
    ann_path = next(iter(ann_folder.glob("*_im_annotations.json")), None)
    if not ann_path:
        # fallback to any json
        ann_path = next(iter(ann_folder.glob("*.json")), None)
    if not ann_path:
        print(f"[skip] no annotations for {dataset}")
        return

    im_ann = load_json(ann_path) or {}
    idx = index_images_by_stem(img_folder)

    mask_dir = MASKS_ROOT / dataset;     ensure_dir(mask_dir)
    ov_dir   = OVERLAYS_ROOT / dataset;  ensure_dir(ov_dir) if OVERLAYS else None

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
