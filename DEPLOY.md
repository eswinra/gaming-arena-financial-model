# Deploying Gaming Arena Dashboard to trendnalysis.trading

## Architecture

```
[Streamlit Community Cloud]  ←  free Python hosting
        ↑
   dashboard.py + model engine (runs server-side)
        ↑
   GitHub repo (auto-deploys on push)
        ↑
dashboard.trendnalysis.trading  ←  CNAME in Namecheap DNS
        ↑
blog.trendnalysis.trading  ←  WordPress iframe embed (optional)
```

Your cPanel shared hosting runs PHP/WordPress but cannot run persistent Python processes.
Streamlit Community Cloud is free, purpose-built for Streamlit apps, and deploys from GitHub.

---

## Step 1: Push Code to GitHub

You already have a GitHub account (visible in your bookmarks bar).

### 1A. Create a new GitHub repository

1. Go to https://github.com/new
2. Repository name: `gaming-arena-financial-model`
3. Set to **Public** (required for free Streamlit Cloud) or Private (if you connect GitHub to Streamlit Cloud with permissions)
4. Do NOT initialize with README (you already have one)
5. Click **Create repository**

### 1B. Push your local code

Open a terminal in your `gaming_arena_financial_toolkit` folder and run:

```bash
git init
git add config.py model_engine.py scenarios.py excel_export.py dashboard.py main.py
git add requirements.txt README.md .gitignore .streamlit/config.toml
git commit -m "Initial commit: Gaming Arena financial model toolkit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/gaming-arena-financial-model.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

**Do NOT push:** `__pycache__/`, `.xlsx` files, or any `.env` files. The `.gitignore` already handles this.

---

## Step 2: Deploy on Streamlit Community Cloud

### 2A. Sign up / Sign in

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Authorize Streamlit to access your repos

### 2B. Deploy the app

1. Click **"New app"**
2. Fill in:
   - **Repository:** `YOUR_USERNAME/gaming-arena-financial-model`
   - **Branch:** `main`
   - **Main file path:** `dashboard.py`
3. Click **"Deploy"**

Streamlit Cloud will:
- Clone your repo
- Install everything in `requirements.txt`
- Start `dashboard.py`
- Give you a public URL like: `https://your-username-gaming-arena-financial-model-dashboard-xxxxx.streamlit.app`

### 2C. Verify it works

Visit the URL. You should see the full interactive dashboard with sliders, tabs, charts. If anything errors out, check the logs in the Streamlit Cloud console (click "Manage app" in the bottom-right corner of the deployed app).

---

## Step 3: Point a Subdomain (Namecheap DNS)

This step makes `dashboard.trendnalysis.trading` load your Streamlit app instead of the ugly `.streamlit.app` URL.

**Note:** Streamlit Community Cloud supports custom domains on public apps.

### 3A. Configure custom domain in Streamlit Cloud

1. Go to your deployed app on share.streamlit.io
2. Click the **3-dot menu** (kebab menu) → **Settings**
3. Under **General** → **Custom subdomain**, enter: `gaming-arena-dashboard` (or whatever you want as the subdomain prefix on streamlit.app)
4. Note: Full custom domain support (your own domain) requires checking Streamlit's current docs — as of early 2025, custom domains are available but the process may have changed. Check: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/custom-subdomains

### 3B. Alternative: Use an iframe (simpler, works immediately)

If custom domain mapping isn't available or you want the dashboard embedded inside your existing site layout, skip the CNAME approach and go straight to Step 4 (iframe embed). This is the most practical path for a WordPress blog.

### 3C. If custom domains are supported — set up CNAME

1. Log in to Namecheap → **Domain List** → click **Manage** next to `trendnalysis.trading`
2. Go to **Advanced DNS**
3. Add a new record:
   - **Type:** CNAME
   - **Host:** `dashboard` (this creates `dashboard.trendnalysis.trading`)
   - **Value:** Your Streamlit app URL (e.g., `your-app-name.streamlit.app`)
   - **TTL:** Automatic
4. Save. DNS propagation takes 5-30 minutes.
5. Go back to Streamlit Cloud settings and add `dashboard.trendnalysis.trading` as your custom domain.

---

## Step 4: Embed in WordPress Blog

This is the fastest way to get the dashboard on `blog.trendnalysis.trading`.

### 4A. Get the embed URL

Your Streamlit app URL will be something like:
```
https://your-username-gaming-arena-financial-model-dashboard-xxxxx.streamlit.app
```

You can add `?embed=true` to hide Streamlit's default header/footer for a cleaner embed:
```
https://your-app-url.streamlit.app/?embed=true
```

And `&embed_options=dark_theme` or `&embed_options=light_theme` to force a theme:
```
https://your-app-url.streamlit.app/?embed=true&embed_options=light_theme
```

### 4B. Create the WordPress post

Since you write blog posts in HTML, paste this into your WordPress post editor (HTML/Code view):

```html
<h2>Gaming Arena Financial Model — Interactive Dashboard</h2>

<p>Use the sliders on the left to adjust utilization, pricing, and forecast period. 
The model recalculates all three financial statements, scenarios, sensitivity tables, 
and Monte Carlo simulations in real time.</p>

<div style="position: relative; width: 100%; padding-bottom: 75%; overflow: hidden; border-radius: 8px; border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
  <iframe 
    src="https://YOUR-APP-URL.streamlit.app/?embed=true&embed_options=light_theme"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
    loading="lazy"
    allow="clipboard-write"
    title="Gaming Arena Financial Model Dashboard">
  </iframe>
</div>

<p style="font-size: 0.85em; color: #666; margin-top: 8px;">
  Built with Python, pandas, and Streamlit. Model assumptions based on a 40-station 
  gaming arena SBA loan application.
</p>
```

Replace `YOUR-APP-URL` with your actual Streamlit Cloud URL.

### 4C. Responsive sizing tips

The `padding-bottom: 75%` creates a 4:3 aspect ratio container. Adjust as needed:
- `56.25%` = 16:9 (wider)
- `75%` = 4:3 (balanced)
- `100%` = 1:1 (taller)

For a fixed height instead:
```html
<iframe 
  src="https://YOUR-APP-URL.streamlit.app/?embed=true"
  width="100%" 
  height="800px" 
  style="border: none; border-radius: 8px;"
  title="Gaming Arena Financial Dashboard">
</iframe>
```

---

## Step 5: Updates and Maintenance

### Updating the dashboard

1. Edit files locally (e.g., change assumptions in `config.py`, fix a chart in `dashboard.py`)
2. Commit and push:
```bash
git add -A
git commit -m "Update: description of changes"
git push
```
3. Streamlit Cloud auto-redeploys within ~1 minute. The WordPress embed refreshes automatically.

### Monitoring

- Streamlit Cloud dashboard: https://share.streamlit.io (shows app status, logs, resource usage)
- Free tier limits: Apps sleep after ~7 days of inactivity. A visitor waking it up takes ~30 seconds.

### Keeping the app awake

If you want the app always responsive, you can set up a simple health check ping. But for a blog portfolio project, the ~30 second cold start is fine.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| App won't deploy | Check `requirements.txt` has all packages listed |
| Import errors | Make sure all `.py` files are committed and pushed |
| Charts not rendering | Verify `matplotlib` is in `requirements.txt` |
| WordPress iframe blank | Check the Streamlit URL works directly in browser first |
| CNAME not resolving | Wait 30 min for DNS propagation, verify in Namecheap Advanced DNS |
| App sleeping | Visit the URL directly to wake it, or upgrade Streamlit Cloud plan |

---

## File Checklist for GitHub

These files must be in your repo:

```
gaming-arena-financial-model/
├── .streamlit/
│   └── config.toml          ← Streamlit server config
├── .gitignore                ← Excludes __pycache__, .xlsx, etc.
├── requirements.txt          ← Python dependencies
├── config.py                 ← Module 1: Assumptions
├── model_engine.py           ← Module 2: 3-Statement Model
├── scenarios.py              ← Module 3: Scenarios & Sensitivity
├── excel_export.py           ← Module 4: Excel Export
├── dashboard.py              ← Module 5: Streamlit Dashboard (entry point)
├── main.py                   ← Module 6: CLI Runner
└── README.md                 ← Project documentation
```
