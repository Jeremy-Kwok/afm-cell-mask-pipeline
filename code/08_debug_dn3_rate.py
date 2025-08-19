"""
08_debug_dn3_rate.py
Diagnose why a RATE dataset might have fewer masks than manual annotations.
- Lists how many images exist
- Parses *_im_annotations.json (manual polygons)
- Tries to match each annotated key to a filename (exact, -1, -2, +1, nearest)
- Prints missing matches (first 30) and a sample of filenames
"""

from pathlib import Path
import json, re

DATA_DIR = Path("data")
TARGET = "DN3-rate"  # <-- change to DN1-rate, DN2-rate, DN4-rate as needed

IMG_DIR = DATA_DIR / TARGET
ANN_DIR = DATA_DIR / f"{TARGET}_annotations"

TUPLE = re.compile(r"\('(\d+)',\s*'(\d+)'\)")
def stem(cell, meas): return f"cell{int(cell):02d}meas{int(meas):04d}".lower()

# load im_annotations (polygons)
jpath = next((p for p in ANN_DIR.glob("*_im_annotations.json")), None)
if not jpath:
    raise SystemExit(f"[err] No *_im_annotations.json in {ANN_DIR}")
ann = json.loads(jpath.read_text())

# index images
idx = {p.stem.lower(): p for p in IMG_DIR.glob("*") if p.suffix.lower() in {".tif",".tiff",".png",".jpg",".jpeg"}}
print("found images:", len(idx))

manual = [k for k,v in ann.items() if isinstance(v, dict) and v.get("selection")=="manual"]
print("manual keys:", len(manual))

missing = []
for k in manual:
    m = TUPLE.fullmatch(k.strip())
    if not m:
        continue
    cell, meas_ = m.group(1), m.group(2)
    s = stem(cell, meas_)
    candidates = [s]
    mv = int(meas_)
    for delta in (-1, -2, +1):  # common off-by patterns
        candidates.append(stem(cell, f"{mv+delta:04d}"))
    found = next((c for c in candidates if c in idx), None)
    if not found:
        # nearest per cell as a last resort
        per_cell = sorted((int(re.search(r"meas(\d+)", k2).group(1)), k2)
                          for k2 in idx.keys()
                          if k2.startswith(f"cell{int(cell):02d}meas"))
        if per_cell:
            nearest = min(per_cell, key=lambda t: abs(t[0]-mv))[1]
            found = nearest if nearest in idx else None
    if not found:
        missing.append((k, candidates))

print("missing images for keys:", len(missing))
for k, cands in missing[:30]:
    print("  missing", k, "tried:", ", ".join(cands))

print("\nexample filenames in", TARGET, ":", sorted(list(idx.keys()))[:20])
