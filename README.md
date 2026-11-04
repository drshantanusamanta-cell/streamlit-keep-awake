# Streamlit Keep-Awake

Keeps your Streamlit Community Cloud apps from going to sleep. A GitHub Action opens every app in a real headless browser on a schedule and clicks **"Yes, get this app back up!"** if an app is asleep.

## Files

```
streamlit-keep-awake/
├── .github/
│   └── workflows/
│       └── keep-awake.yml   ← the schedule + steps
├── keep_awake.py            ← visits / wakes each app
├── apps.txt                 ← your app URLs (one per line)
├── last_run.txt             ← heartbeat file (auto-updated)
└── README.md
```

## Setup — step by step

### 1. Create the repo
1. Go to github.com → **+** → **New repository**.
2. Name it `streamlit-keep-awake`.
3. Choose **Public** (unlimited free Action minutes) or **Private** (2,000 free minutes/month — plenty at a 6-hour schedule).
4. Click **Create repository**.

### 2. Upload the files
1. On the empty repo page click **uploading an existing file**.
2. Unzip the package on your computer and drag in **everything inside** the `streamlit-keep-awake` folder, including the `.github` folder.
   - If your OS hides `.github`, create it manually instead: **Add file → Create new file**, type `.github/workflows/keep-awake.yml` as the name (the slashes create the folders), and paste the file's contents.
3. Click **Commit changes**.

### 3. Add your app URLs
1. Open `apps.txt` → pencil icon (Edit).
2. Replace the example lines with your real app URLs, one per line, e.g. `https://myapp.streamlit.app/`.
3. **Commit changes**.

### 4. Allow the workflow to commit (heartbeat)
1. Repo → **Settings** → **Actions** → **General**.
2. Under **Workflow permissions**, select **Read and write permissions**.
3. **Save**.

### 5. Test it once
1. Repo → **Actions** tab. If prompted, click **I understand my workflows, go ahead and enable them**.
2. Select **Keep Streamlit apps awake** → **Run workflow** → **Run workflow**.
3. Wait ~3–5 minutes. A green tick = success. Open the run → **Visit / wake every app** to see `AWAKE` / `WOKE` / `FAIL` for each URL.

### 6. Done
It now runs automatically on the schedule. If any app fails, the run turns red and GitHub emails you.

## Changing the schedule

Edit the `cron` line in `.github/workflows/keep-awake.yml`. Times are **UTC** (IST = UTC + 5:30). Stay under ~8 hours; apps sleep after 12 hours without traffic and GitHub sometimes starts scheduled runs late.

| Want | cron |
|---|---|
| Every 4 h | `17 */4 * * *` |
| Every 6 h (default) | `17 */6 * * *` |
| Every 8 h | `17 */8 * * *` |
| 3 runs/day, ~10 h apart | `17 0,10,20 * * *` |

## Adding or removing apps
Just edit `apps.txt`. Lines starting with `#` are ignored, so you can comment an app out temporarily.

## Troubleshooting
- **FAIL (timeout)** — the app may be crashing on start-up. Open it in your browser and check its logs on share.streamlit.io.
- **Workflow stopped running** — GitHub disables schedules after 60 days of no repo activity; the heartbeat commit prevents this. If it was disabled anyway, re-enable it in the Actions tab.
- **Heartbeat step fails with permission error** — redo step 4.
- **App still asleep** — wake it manually once, then check the URL in `apps.txt` matches exactly.

## Limits
This is a workaround, not a guarantee; Streamlit offers no always-on tier on Community Cloud. For an app that must be instantly available 24/7, use a paid host.
