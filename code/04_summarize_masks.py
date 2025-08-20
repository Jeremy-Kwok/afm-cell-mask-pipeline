# 04_summarize_masks.py
import json
from pathlib import Path
import csv
import ast

DATA_DIR = Path("data_full")
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

def summarize_masks(subfolder):
    masks_written = 0
    manual_in_json = 0
    exclude_in_json = 0

    # Count how many masks were written
    mask_path = DATA_DIR / subfolder / "masks"
    if mask_path.exists():
        masks_written = len(list(mask_path.glob("*.png")))

    # Look in annotations subdir for *_im_annotations.json
    annotation_dir = DATA_DIR / subfolder / "annotations"
    if annotation_dir.exists():
        for f in annotation_dir.glob("*_im_annotations.json"):
            try:
                with open(f) as jf:
                    annotations = json.load(jf)
                for key_str, label in annotations.items():
                    try:
                        ast.literal_eval(key_str)
                    except Exception:
                        continue
                    if isinstance(label, dict):
                        if label.get("selection") == "manual":
                            manual_in_json += 1
                        elif label.get("selection") == "exclude":
                            exclude_in_json += 1
            except Exception as e:
                print(f"[error] failed to parse {f}: {e}")
                continue

    return {
        "dataset": subfolder,
        "masks_written": masks_written,
        "manual_in_json": manual_in_json,
        "exclude_in_json": exclude_in_json
    }

def main():
    subfolders = sorted([f.name for f in DATA_DIR.iterdir() if f.is_dir()])
    rows = []
    for sub in subfolders:
        summary = summarize_masks(sub)
        rows.append(summary)

    with open(RESULTS_DIR / "mask_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["dataset", "masks_written", "manual_in_json", "exclude_in_json"])
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()