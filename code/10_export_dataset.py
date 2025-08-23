#!/usr/bin/env python3
"""Export tif+mask pairs into a flat Cellpose-ready folder (supports --image-glob)."""

import os, glob, shutil, argparse, fnmatch

# Find a mask path for a given base (tries _masks/_mask and png/tif/tiff; falls back to wildcard)
def find_mask_path(mask_dir, base):
    # try exact matches first
    for ext in (".png", ".tif", ".tiff"):
        p = os.path.join(mask_dir, f"{base}_masks{ext}")
        if os.path.exists(p): 
            if "overlay" in os.path.basename(p).lower(): 
                continue
            return p
    for ext in (".png", ".tif", ".tiff"):
        p = os.path.join(mask_dir, f"{base}_mask{ext}")
        if os.path.exists(p): 
            if "overlay" in os.path.basename(p).lower(): 
                continue
            return p

    # wildcard fallbacks
    hits = []
    for ext in (".png", ".tif", ".tiff"):
        hits += glob.glob(os.path.join(mask_dir, f"{base}*masks*{ext}"))
        hits += glob.glob(os.path.join(mask_dir, f"{base}*mask*{ext}"))

    # *** critical hardening: ignore anything with 'overlay' in the name ***
    hits = [h for h in hits if "overlay" not in os.path.basename(h).lower()]

    return sorted(hits, key=len)[0] if hits else None

def main():
    # Parse CLI args (explicit inputs + optional image filter)
    ap = argparse.ArgumentParser(description="Flatten datasets for Cellpose training.")
    ap.add_argument("--inputs", nargs="+", required=True,
                    help='Dataset dirs like data_full/DN1-rapid data_full/DN1-rate (globs OK).')
    ap.add_argument("--output", default="afm_dataset",
                    help="Output folder (default: afm_dataset)")
    ap.add_argument("--image-glob", default=None,
                    help='Filter images by glob, e.g. "*meas0000.tif". If omitted, use all .tif/.tiff.')
    args = ap.parse_args()

    # Expand any unexpanded globs and make absolute paths
    input_dirs = []
    for pat in args.inputs:
        hits = glob.glob(pat)
        input_dirs += hits if hits else [pat]
    input_dirs = [os.path.abspath(d) for d in input_dirs]

    # Ensure output directory exists
    os.makedirs(args.output, exist_ok=True)

    total_pairs, total_missing = 0, 0

    for input_dir in input_dirs:
        if not os.path.isdir(input_dir):
            print(f"❌ Skipping (not a directory): {input_dir}")
            continue

        dataset = os.path.basename(os.path.normpath(input_dir))
        mask_dir = os.path.join(input_dir, "masks")
        if not os.path.isdir(mask_dir):
            print(f"❌ Skipping {dataset}: masks/ not found")
            continue

        # Collect source images: .tif/.tiff (optionally filtered by --image-glob)
        all_imgs = [f for f in os.listdir(input_dir)
                    if os.path.splitext(f)[1].lower() in (".tif", ".tiff")]
        tif_files = sorted(all_imgs) if not args.image_glob else \
                    sorted([f for f in all_imgs if fnmatch.fnmatch(f, args.image_glob)])

        if not tif_files:
            print(f"⚠️  No images matched in {dataset} (filter={args.image_glob or 'all .tif/.tiff'})")
            continue

        print(f"→ {dataset}: {len(tif_files)} image(s)")

        missing_here = 0
        for tif_file in tif_files:
            base = os.path.splitext(tif_file)[0]
            mask_path = find_mask_path(mask_dir, base)
            if mask_path is None:
                print(f"   ⚠️  No mask for {tif_file}")
                total_missing += 1
                missing_here += 1
                continue

            mask_ext = os.path.splitext(mask_path)[1]
            out_img  = f"{dataset}_{tif_file}"
            out_mask = f"{dataset}_{base}_masks{mask_ext}"

            shutil.copy2(os.path.join(input_dir, tif_file), os.path.join(args.output, out_img))
            shutil.copy2(mask_path,                          os.path.join(args.output, out_mask))
            total_pairs += 1

        if missing_here:
            print(f"   ↳ {missing_here} without masks in {dataset}")

    print(f"✅ Exported {total_pairs} pair(s) → {args.output}")
    if total_missing:
        print(f"⚠️  Missing masks for {total_missing} image(s) total")

if __name__ == "__main__":
    main()
