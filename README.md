# Photo Selector

A tool for social media managers to batch-upload photos and automatically receive ranked, deduplicated top picks with quality tags.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API
uvicorn app.main:app --reload

# 3. In a second terminal, start the UI
streamlit run ui/streamlit_app.py
```

Open **http://localhost:8501** in your browser.

---

## Architecture

```
photo-selector/
├── app/
│   ├── main.py          # FastAPI app — POST /rank endpoint
│   ├── schemas.py       # Pydantic request/response models
│   ├── dedup.py         # Perceptual hash deduplication (pHash)
│   ├── scorer.py        # Image quality signals (sharpness, brightness, contrast, resolution)
│   ├── orientation.py   # EXIF-aware portrait/landscape detection
│   ├── ranker.py        # Weighted scoring + top-N ranking
│   └── utils.py         # Optional CLIP relevance scorer
├── ui/
│   └── streamlit_app.py # Review UI with grid, filters, score bars
├── tests/
│   ├── test_orientation.py
│   └── test_scorer.py
└── requirements.txt
```

---

## Scoring Algorithm (v1)

| Signal | Weight | Method |
|---|---|---|
| Sharpness | 35 % | Laplacian variance, capped at 2000 |
| Resolution | 20 % | Pixel count normalised against 12 MP ceiling |
| Brightness | 20 % | Proximity to ideal range 80–180 / 255 |
| Contrast | 15 % | Grayscale std dev, normalised against 80 |
| Relevance | 10 % | CLIP cosine similarity (optional) |

If CLIP is not installed the 10 % relevance weight is redistributed proportionally across the other four signals.

---

## API Reference

### `POST /rank`

**Form fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `files` | `UploadFile[]` | required | Image files (JPEG, PNG, WebP, TIFF) |
| `top_n` | `int` | 20 | Number of results to return (-1 = all) |
| `prompt` | `str` | `""` | Text prompt for CLIP relevance scoring |
| `dedup_threshold` | `int` | 8 | Hamming distance threshold (0 = exact only, 10 = near-duplicates) |

**Response:** `RankResponse`

```json
{
  "total_uploaded": 47,
  "duplicates_removed": 3,
  "prompt_used": "product on white background",
  "ranked": [
    {
      "filename": "shot_042.jpg",
      "orientation": "landscape",
      "width": 4000,
      "height": 2667,
      "final_score": 0.834,
      "scores": {
        "sharpness": 0.91,
        "brightness": 0.87,
        "contrast": 0.72,
        "resolution": 0.89,
        "relevance": 0.63
      },
      "tags": ["sharp", "well-lit", "high-res", "relevant", "top-pick"],
      "duplicate_of": null
    }
  ]
}
```

---

## Enabling CLIP (optional)

Uncomment the relevant lines in `requirements.txt`, then reinstall:

```bash
pip install transformers torch open-clip-torch
```

Pass a `prompt` string to the `/rank` endpoint or fill in the **Relevance prompt** field in the UI.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Roadmap

- [ ] SQLite job history (store past ranking runs)
- [ ] Batch export: download top picks as a ZIP
- [ ] Face / subject detection as an additional signal
- [ ] Side-by-side duplicate review before removal
- [ ] Cloud storage input (S3, Google Drive)
