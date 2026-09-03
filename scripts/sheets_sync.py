"""
Google Sheets Sync Script
Sends processed daily logs and leaderboard stats to the Google Apps Script Webhook.
"""

import os
import sys
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def sync_to_google_sheet(webhook_url, payload):
    """
    POSTs payload to Google Sheet Webhook URL.
    Google Apps Script redirects 302 on POST, which standard urllib handles automatically.
    """
    if not webhook_url:
        print("[!] No Google Sheet Webhook URL provided. Skipping Sheet sync.")
        return False

    print(f"[*] Pushing data to Google Sheet Webhook...")
    data_bytes = json.dumps(payload).encode("utf-8")
    
    req = Request(
        webhook_url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "StravaClubTracker/1.0"
        }
    )

    try:
        with urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            print(f"[+] Google Sheet sync completed. Response: {resp_body[:100]}")
            return True
    except HTTPError as e:
        print(f"[!] HTTP error syncing to Google Sheet: {e.code} - {e.reason}")
        return False
    except URLError as e:
        print(f"[!] Network error syncing to Google Sheet: {e.reason}")
        return False
    except Exception as e:
        print(f"[!] Unexpected error syncing to Google Sheet: {e}")
        return False


if __name__ == "__main__":
    url = os.environ.get("GOOGLE_SHEET_WEBHOOK_URL")
    if not url:
        print("Usage: Set GOOGLE_SHEET_WEBHOOK_URL environment variable.")
        sys.exit(1)
        
    sample_payload = {
        "date": "2026-09-03",
        "target_km": 100,
        "daily_logs": [
            {"date": "2026-09-03", "athlete_id": "test", "name": "Test Runner", "daily_distance_km": 5.0, "daily_runs": 1, "avg_pace": "5:30", "daily_elev_gain_m": 50, "weekly_cumulative_km": 20.0}
        ],
        "athlete_totals": {
            "test": {"name": "Test Runner", "total_challenge_km": 25.0, "pct_completed": 25.0, "remaining_km": 75.0, "active_days": 5, "current_streak": 3}
        }
    }
    sync_to_google_sheet(url, sample_payload)
