"""
photo-selector — Streamlit Review UI
Run: streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import io
import math
from typing import Any

import requests
import streamlit as st
from PIL import Image

API_URL = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Photo Selector",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — upload & settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📷 Photo Selector")
    st.caption("Upload photos, get ranked top picks.")

    uploaded_files = st.file_uploader(
        "Upload images",
        type=["jpg", "jpeg", "png", "webp", "tiff"],
        accept_multiple_files=True,
    )

    st.divider()
    st.subheader("Settings")

    top_n = st.slider("Top N results", min_value=5, max_value=50, value=20, step=5)
    dedup_threshold = st.slider(
        "Dedup sensitivity",
        min_value=0,
        max_value=20,
        value=8,
        help="Hamming distance threshold. Lower = stricter deduplication.",
    )
    prompt = st.text_input(
        "Relevance prompt (optional)",
        placeholder="e.g. product flat lay on white background",
        help="Requires CLIP to be installed. Leave blank to skip.",
    )

    run = st.button("▶ Rank Photos", type="primary", disabled=not uploaded_files)

# ---------------------------------------------------------------------------
# Filter bar (top of main area)
# ---------------------------------------------------------------------------
if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.meta = {}

if run and uploaded_files:
    with st.spinner("Processing…"):
        files_payload = [
            ("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files
        ]
        data = {
            "top_n": top_n,
            "dedup_threshold": dedup_threshold,
        }
        if prompt:
            data["prompt"] = prompt

        try:
            resp = requests.post(f"{API_URL}/rank", files=files_payload, data=data, timeout=120)
            resp.raise_for_status()
            payload = resp.json()
            st.session_state.results = payload["ranked"]
            st.session_state.meta = {
                "total_uploaded": payload["total_uploaded"],
                "duplicates_removed": payload["duplicates_removed"],
                "prompt_used": payload.get("prompt_used"),
            }
        except requests.exceptions.ConnectionError:
            st.error("Could not reach the API. Make sure `uvicorn app.main:app` is running.")
        except Exception as e:
            st.error(f"Error: {e}")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
results: list[dict[str, Any]] | None = st.session_state.results
meta = st.session_state.meta

if results is None:
    st.info("Upload photos and click **▶ Rank Photos** to get started.")
    st.stop()

# Summary bar
col1, col2, col3 = st.columns(3)
col1.metric("Uploaded", meta.get("total_uploaded", "–"))
col2.metric("Duplicates removed", meta.get("duplicates_removed", "–"))
col3.metric("Top picks shown", len(results))

if meta.get("prompt_used"):
    st.caption(f"Relevance scored against: *{meta['prompt_used']}*")

st.divider()

# Orientation filter
orientation_filter = st.radio(
    "Orientation",
    options=["All", "Portrait", "Landscape", "Square"],
    horizontal=True,
)

tag_options = sorted({tag for r in results for tag in r.get("tags", [])})
selected_tags = st.multiselect("Filter by tag", options=tag_options)

# Apply filters
filtered = results
if orientation_filter != "All":
    filtered = [r for r in filtered if r["orientation"].lower() == orientation_filter.lower()]
if selected_tags:
    filtered = [r for r in filtered if any(t in r.get("tags", []) for t in selected_tags)]

if not filtered:
    st.warning("No images match the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Grid display
# ---------------------------------------------------------------------------
COLS = 4
rows = math.ceil(len(filtered) / COLS)
# Build a lookup from filename → bytes for thumbnails
file_bytes = {f.name: f.getvalue() for f in (uploaded_files or [])}

for row in range(rows):
    cols = st.columns(COLS)
    for col_idx in range(COLS):
        idx = row * COLS + col_idx
        if idx >= len(filtered):
            break
        item = filtered[idx]
        with cols[col_idx]:
            # Thumbnail
            raw = file_bytes.get(item["filename"])
            if raw:
                img = Image.open(io.BytesIO(raw))
                st.image(img, use_container_width=True)
            else:
                st.write("*(preview unavailable)*")

            # Score bar
            score = item["final_score"]
            bar_color = "#22c55e" if score >= 0.7 else "#f59e0b" if score >= 0.45 else "#ef4444"
            st.markdown(
                f"""
                <div style="background:#e5e7eb;border-radius:4px;height:6px;margin-bottom:4px;">
                  <div style="width:{int(score*100)}%;background:{bar_color};height:6px;border-radius:4px;"></div>
                </div>
                <span style="font-size:0.78rem;color:#6b7280;">{item['filename']}</span>
                """,
                unsafe_allow_html=True,
            )

            # Tags
            tag_html = " ".join(
                f'<span style="background:#f3f4f6;border-radius:9999px;padding:2px 8px;'
                f'font-size:0.7rem;color:#374151;">{t}</span>'
                for t in item.get("tags", [])
            )
            st.markdown(tag_html, unsafe_allow_html=True)

            # Score details expander
            with st.expander(f"Score: {score:.2f}  ·  {item['orientation']}"):
                sc = item["scores"]
                for signal, label in [
                    ("sharpness", "Sharpness"),
                    ("brightness", "Brightness"),
                    ("contrast", "Contrast"),
                    ("resolution", "Resolution"),
                    ("relevance", "Relevance"),
                ]:
                    val = sc.get(signal)
                    if val is None:
                        continue
                    st.progress(val, text=f"{label}: {val:.2f}")
