"""
04_summarize_masks.py
Summarize per-dataset:
- masks_written: number of mask pngs we generated
- manual_in_json: # entries with selection == "manual" in *_im_annotations.json
- exclude_in_json: prefer # entries whose selection != "manual" in *_im_annotations.json;
                   if not available, fall back to counting False entries in *_vd_annotations.json.

Handles RAPID and RATE layouts:
RAPID
  images: data/DN?-rapid/*.tif
  im:     data/DN?-rapid/DN?-rapid_im_annotations.json
  vd:     data/DN?-rapid/DN?-rapid_vd_annotations.json (optional)
RATE
  images: data/DN?-rate/*.tif
  im:     data/DN?-rate_annotations/*_im_annotations.json
  vd:     data/DN?-rate_annotations/*_vd_annotations.json
"""

from pathlib import Path
import json, csv, glob

DATA_DIR    = Path("data")
MASKS_DIR   = Path("masks")
RESULTS_DIR = Path("results"); RESULTS_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE    = RESULTS_DIR / "mask_summary.csv"

def load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def summarize_dataset(ds_name: str):
    """
    Returns (masks_written, manual_in_json, exclude_in_json)
    """
    # count masks
    masks_written = len(list((MASKS_DIR / ds_name).glob("*_mask.png")))

    # locate im/vd annotations
    im_json = None
    vd_json = None

    if ds_name.endswith("-rapid"):
        # RAPID: im/vd live inside the dataset folder
        ds_folder = DATA_DIR / ds_name
        im_path = ds_folder / f"{ds_name}_im_annotations.json"
        vd_path = ds_folder / f"{ds_name}_vd_annotations.json"
        if im_path.exists():
            im_json = load_json(im_path)
        if vd_path.exists():
            vd_json = load_json(vd_path)

    elif ds_name.endswith("-rate"):
        # RATE: annotations live under a sibling *_annotations folder
        ann_dir = DATA_DIR / f"{ds_name}_annotations"
        if ann_dir.exists():
            im_candidates = list(ann_dir.glob("*_im_annotations.json"))
            vd_candidates = list(ann_dir.glob("*_vd_annotations.json"))
            if im_candidates:
                im_json = load_json(im_candidates[0])
            if vd_candidates:
                vd_json = load_json(vd_candidates[0])

    # compute manual/exclude
    manual_in_json = 0
    exclude_in_json = 0

    if isinstance(im_json, dict):
        # prefer explicit selection labels in im_annotations
        entries = [v for v in im_json.values() if isinstance(v, dict)]
        manual_in_json = sum(1 for v in entries if v.get("selection") == "manual")

        # if im_annotations has selection labels, count non-manual as exclude
        exclude_labeled = sum(1 for v in entries if v.get("selection") != "manual")
        if exclude_labeled > 0:
            exclude_in_json = exclude_labeled
        elif isinstance(vd_json, dict):
            # fallback: count False entries in vd_annotations
            exclude_in_json = sum(1 for v in vd_json.values() if v is False)
    else:
        # no im_annotations → try just vd false-count
        if isinstance(vd_json, dict):
            exclude_in_json = sum(1 for v in vd_json.values() if v is False)

    return masks_written, manual_in_json, exclude_in_json


def main():
    rows = [("dataset", "masks_written", "manual_in_json", "exclude_in_json")]

    for sub in sorted(DATA_DIR.iterdir()):
        if not sub.is_dir():
            continue
        name = sub.name
        # only summarize DN?-rapid / DN?-rate (skip *_annotations and DN?-force)
        if name.endswith("-rapid") or name.endswith("-rate"):
            masks_written, manual_cnt, exclude_cnt = summarize_dataset(name)
            rows.append((name, masks_written, manual_cnt, exclude_cnt))

    with OUT_FILE.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"[ok] wrote {OUT_FILE}")

if __name__ == "__main__":
    main()
