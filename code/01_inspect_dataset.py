"""
01_inspect_dataset.py
Quickly scans the data directory and lists the datasets, image counts, and annotation files.
"""

import os
import glob

DATA_DIR = "data"

def inspect():
    datasets = sorted(os.listdir(DATA_DIR))
    for ds in datasets:
        ds_path = os.path.join(DATA_DIR, ds)
        if os.path.isdir(ds_path):
            tifs = glob.glob(os.path.join(ds_path, "*.tif"))
            jsons = glob.glob(os.path.join(ds_path, "*.json"))
            print(f"{ds}: {len(tifs)} images, {len(jsons)} jsons")

if __name__ == "__main__":
    inspect()
