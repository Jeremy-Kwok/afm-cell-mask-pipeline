# 🚀 AFM Cell Mask Generation (DN1–DN4 • Rapid + Rate)

Automated, reproducible pipeline to convert AFM `.tif` frames + JSON annotations into **binary cell masks** and **overlay images** for downstream analysis.  
Supports DN1–DN4 datasets for both **rapid** and **rate** acquisitions.

---

## 🧠 Why this matters

Manual segmentation is slow and inconsistent. This pipeline standardizes mask generation so you can:

- ✅ Train and benchmark segmentation models (Cellpose, U-Net, etc.)
- ✅ Validate automated methods against human annotations
- ✅ Scale downstream biophysics analyses with consistent inputs

---

## 📦 Repo layout

```
afm_cell_training/
├── code/                   # scripts (inspect → masks → overlays → summary)
├── data_full/              # full datasets (gitignored)
│   └── DN1-rapid/
│       ├── *.tif           # raw AFM image frames
│       ├── annotations/    # human-drawn JSON annotations
│       ├── masks/          # generated binary masks (auto)
│       └── overlays/       # visual overlays (image + mask)
├── data_samples/           # curated public samples (committed)
│   ├── DN1-rapid/
│   │   ├── masks/
│   │   └── overlays/
│   └── DN1-rate/
│       ├── masks/
│       └── overlays/
├── results/                # includes mask_summary.csv
├── .gitignore
├── README.md
├── requirements.txt
└── pyproject.toml
```

---

## 🛠️ Installation

Recommended: create and activate a virtual environment.

```bash
# Clone the repo
git clone https://github.com/yourusername/afm_cell_training.git
cd afm_cell_training

# (Optional) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Alternatively, if you're using [`uv`](https://github.com/astral-sh/uv):

```bash
uv venv
uv pip install -r requirements.txt
```

---

## ▶️ How to run (full local data)

This assumes you've extracted all datasets into the `data_full/` folder:

```bash
python code/01_inspect_dataset.py
python code/02_make_masks_hoseyn.py
python code/03_overlay_examples.py
python code/04_summarize_masks.py
```

This will populate:

- `data_full/**/masks/` with generated binary masks  
- `data_full/**/overlays/` with annotated overlays  
- `results/mask_summary.csv` with dataset stats

---

## 🌐 Try it out: Tiny public preview

Run on public sample data:

```bash
python code/01_inspect_dataset.py data_samples
python code/02_make_masks_hoseyn.py data_samples
python code/03_overlay_examples.py data_samples
python code/04_summarize_masks.py data_samples
```

---

## 📊 Outputs

This repo produces:

- 🟣 Binary masks of each cell
- 🟢 Overlay `.png` files showing annotations on top of raw images
- 📄 Summary CSV file (see `results/mask_summary.csv`)

---

## 🧪 Example visual (from assets/)

| Raw Image | Overlay Output |
|-----------|----------------|
| ![raw](assets/cell01meas0000.png) | ![overlay](assets/cell01meas0000_overlay.png) |

---

## 📁 Notes on data

> ⚠️ Raw `.tif` image files are **not included** in this repo due to size.

---

## 👤 Author

**Jeremy Kwok**  
📧 [jeremykwok917@gmail.com](mailto:jeremykwok917@gmail.com)

---

## 🙏 Acknowledgments

This project was made possible with data and technical guidance provided by [**Hoseyn Amiri**](https://www.sulchek2.gatech.edu/people/graduate/hoseyn-amiri/), a graduate researcher in the [Sulchek Lab](https://www.sulchek2.gatech.edu/) at Georgia Tech.  
Hoseyn's mentorship shaped the approach to annotation standards, mask generation, and tool development used throughout this work.

---

## 📄 License

This project is intended for academic and research use.  
For commercial use or redistribution, please contact the author.