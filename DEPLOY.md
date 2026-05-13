# Deploy Guide — Zero Local Processing

The goal: your laptop only runs a browser. All image processing happens on a free cloud server.

```
Your Browser (UI)  ──uploads──▶  Railway / Render (FastAPI)
        ◀──────────── JSON scores ──────────────────────────
```

---

## Step 1 — Push to GitHub

```bash
cd photo-selector
git init
git add .
git commit -m "initial commit"
# Create a new repo at github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/photo-selector.git
git push -u origin main
```

---

## Step 2 — Deploy the API (pick one)

### Option A — Railway (recommended, free tier, ~5 min)

1. Go to **railway.app** → New Project → Deploy from GitHub repo
2. Select your `photo-selector` repo
3. Railway auto-detects the `Dockerfile` and deploys
4. Once deployed, copy the URL: `https://photo-selector-production.up.railway.app`

To get the deploy token for auto-deploys via GitHub Actions:
- Railway Dashboard → Project Settings → Tokens → Create token
- GitHub repo → Settings → Secrets → New secret: `RAILWAY_TOKEN`

### Option B — Render (also free, sleeps after 15 min idle)

1. Go to **render.com** → New → Web Service → Connect GitHub repo
2. Render reads `render.yaml` automatically
3. Click Deploy. Copy the URL once live.

### Option C — Google Cloud Run (best for production, pay-per-use)

```bash
# Install gcloud CLI first: cloud.google.com/sdk
gcloud auth login
gcloud run deploy photo-selector \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1
```

Copy the URL from the output.

---

## Step 3 — Host the UI (pick one)

### Option A — GitHub Pages (automatic via CI)

After Step 1, go to:
GitHub repo → Settings → Pages → Source: `gh-pages` branch → Save

Your UI will be live at:
`https://YOUR_USERNAME.github.io/photo-selector`

### Option B — Netlify (drag and drop, 30 seconds)

1. Go to **netlify.com** → Add new site → Deploy manually
2. Drag the `ui/` folder into the browser
3. Done. You get a URL like `https://amazing-name-123.netlify.app`

### Option C — Cloudflare Pages

```bash
npx wrangler pages deploy ui/ --project-name photo-selector
```

---

## Step 4 — Open the UI and connect

1. Open your UI URL in any browser (including on your phone)
2. Paste your Railway/Render API URL into the **API endpoint** field
3. The status dot turns green when connected
4. Upload photos → click **Rank Photos** → done

---

## Environment variables (optional tuning)

Set these in Railway/Render dashboard under Environment:

| Variable | Default | Effect |
|---|---|---|
| `MAX_FILE_MB` | 20 | Max size per image (MB) |
| `MAX_FILES` | 100 | Max images per request |
| `MAX_DIMENSION` | 3000 | Downsample images above this px |
| `CHUNK_SIZE` | 10 | Images processed per batch |

For free-tier servers (512 MB RAM), keep `MAX_DIMENSION=2000` and `CHUNK_SIZE=5`.

---

## Architecture summary

```
github.com/you/photo-selector
  │
  ├── app/          ← FastAPI + scoring (runs on Railway)
  ├── ui/           ← Static HTML (served by GitHub Pages / Netlify)
  ├── Dockerfile    ← Railway/Cloud Run uses this
  ├── railway.toml  ← Railway config
  ├── render.yaml   ← Render config
  └── .github/      ← Auto-deploy on git push
```

Your computer: opens a browser tab. That's it.
