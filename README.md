# 🏃 Wandoor Runners - Monsoon 100k Challenge 2026
**Automated Day-by-Day Strava Club Tracker & Dashboard**  
*Club ID: 2317931*

This system solves Strava's limitation (which only shows weekly cumulative totals) by calculating true **day-by-day running mileage**, automatically updating your **Google Sheet**, and displaying an interactive **public web leaderboard**.

---

## 🌟 Key Features

1. **Daily Delta Engine:** Converts Strava's weekly cumulative numbers into exact daily distances:
   $$\text{Today's Run (km)} = \text{Today's Cumulative} - \text{Yesterday's Cumulative}$$
   *Automatically handles Monday week resets.*
2. **Google Sheets Sync:** Automatically logs daily runs and updates the all-time 100k Challenge Leaderboard.
3. **100% Cloud Automation:** GitHub Actions runs automatically every night at 23:45 IST (11:45 PM).
4. **Interactive Dashboard:**
   - 🔥 **Daily Podium:** Today's top 3 runners with medals and pace.
   - 📅 **Day-by-Day View:** Filter by any date to see who ran on that specific day.
   - 🏆 **100k Challenge Progress:** Progress bars, remaining km, active days, and "Finisher" badges.
   - 📱 **WhatsApp Share Generator:** 1-click copy formatted daily summary to send to your club's WhatsApp group!
   - ⚡ **1-Click Bookmarklet:** On-demand sync directly from your open Chrome tab.

---

## 🚀 Quick Start (Local Run)

To test and run locally right now:

```bash
# 1. Run the sync script
python3 run_sync.py

# 2. View the dashboard
# Open index.html directly in your browser, or start a local server:
python3 -m http.server 8080
# Visit http://localhost:8080
```

---

## ⚙️ Setup Instructions (Step-by-Step)

### Step 1: Get Your Strava Session Cookie (Takes 30 seconds)
Since the club is private/invite-only, the script uses your session cookie to view the leaderboard:

1. Open Chrome and go to `https://www.strava.com/clubs/2317931/leaderboard`.
2. Right-click anywhere and choose **Inspect** (or press `Cmd + Option + I` on Mac).
3. Go to the **Application** tab (or **Storage** tab) at the top of DevTools.
4. On the left sidebar, click **Cookies** > `https://www.strava.com`.
5. Find the cookie named **`_strava4_session`**.
6. Double-click its **Value** and copy it.

---

### Step 2: Set Up Google Sheet (Takes 1 minute)

1. Create a new Google Sheet (e.g. named *"Wandoor Runners 100k Tracker"*).
2. Click **Extensions** > **Apps Script** in the top menu.
3. Delete any code in the editor, and paste the code from [`scripts/google_apps_script.js`](scripts/google_apps_script.js).
4. Click **Save** (💾 icon).
5. Click **Deploy** (top right) > **New deployment**.
6. Click the gear icon next to "Select type" and choose **Web app**:
   - **Description**: `Strava Sync`
   - **Execute as**: `Me`
   - **Who has access**: `Anyone`
7. Click **Deploy** and copy the **Web app URL**.

---

### Step 3: Configure GitHub Secrets (For 100% Automated Cloud Runs)

When you push this repository to GitHub:

1. Go to your GitHub repository > **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret** and add:
   - `STRAVA_SESSION_COOKIE`: *(Paste the `_strava4_session` cookie from Step 1)*
   - `GOOGLE_SHEET_WEBHOOK_URL`: *(Paste the Google Web app URL from Step 2)*
3. That's it! GitHub Actions will now automatically run every night at **23:45 IST** (`.github/workflows/daily_sync.yml`).
4. You can also trigger it manually anytime by going to the **Actions** tab on GitHub and clicking **Run workflow**.

---

### Step 4 (Bonus): 1-Click Chrome Bookmarklet
If you want to sync the leaderboard on-demand with one click while viewing Strava in Chrome:
- Check [`scripts/bookmarklet.js`](scripts/bookmarklet.js) for instructions on creating a one-click browser button!

---

## 📁 Project Structure

```
├── .github/workflows/
│   └── daily_sync.yml           # Scheduled GitHub Actions cron (23:45 IST)
├── data/
│   ├── sample_initial_data.json # Baseline club data
│   ├── latest_snapshot.json     # Cached latest fetch
│   └── club_history.json        # Aggregated daily records & 100k totals
├── scripts/
│   ├── scraper.py               # Strava HTML parser & fetcher
│   ├── delta_engine.py          # Day-by-day mileage calculator & streak tracker
│   ├── sheets_sync.py           # Google Sheet webhook poster
│   ├── google_apps_script.js    # Code to paste into Google Apps Script
│   └── bookmarklet.js           # 1-Click browser sync button
├── css/
│   └── style.css                # Premium runner dark UI styling
├── js/
│   └── app.js                   # Interactive dashboard frontend logic
├── index.html                   # Web dashboard
├── run_sync.py                  # Master sync script
├── config.json                  # Local configuration
└── README.md
```
