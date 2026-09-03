#!/usr/bin/env python3
"""
Master Sync Script for Wandoor Runners Strava Club Tracker.
Fetches leaderboard -> Computes daily delta -> Updates Google Sheet -> Updates Dashboard Data.
"""

import os
import sys
import json
from datetime import datetime, date

from scripts.scraper import fetch_club_leaderboard
from scripts.delta_engine import process_daily_delta, load_json, save_json
from scripts.sheets_sync import sync_to_google_sheet

def main():
    print("=" * 60)
    print("  WANDOOR RUNNERS - MONSOON 100K CHALLENGE TRACKER")
    print("=" * 60)

    # 1. Load config
    config = load_json("config.json", {})
    club_id = os.environ.get("STRAVA_CLUB_ID", config.get("club_id", "2317931"))
    target_km = float(os.environ.get("TARGET_DISTANCE_KM", config.get("target_distance_km", 100.0)))
    session_cookie = os.environ.get("STRAVA_SESSION_COOKIE", config.get("strava_session_cookie", "")).strip()
    webhook_url = os.environ.get("GOOGLE_SHEET_WEBHOOK_URL", config.get("google_sheet_webhook_url", "")).strip()
    today_str = date.today().isoformat()

    print(f"[*] Club ID: {club_id}")
    print(f"[*] Target Challenge: {target_km} km")
    print(f"[*] Date: {today_str}")

    # 2. Fetch from Strava
    athletes = []
    if session_cookie:
        print("[*] Fetching live leaderboard with Strava session...")
        athletes, _ = fetch_club_leaderboard(club_id, session_cookie)
    else:
        print("[!] No STRAVA_SESSION_COOKIE provided.")
        print("[*] Attempting unauthenticated/public fetch...")
        athletes, _ = fetch_club_leaderboard(club_id, None)

    # Fallback to initial seed data if fetch failed (e.g. cookie needed for invite-only club)
    if not athletes:
        print("[!] Live fetch returned 0 athletes (requires session cookie for invite-only club).")
        sample_file = os.path.join("data", "sample_initial_data.json")
        if os.path.exists(sample_file):
            print("[*] Loading baseline seed data from data/sample_initial_data.json...")
            sample_data = load_json(sample_file, {})
            athletes = sample_data.get("athletes", [])
        else:
            print("[X] Error: No data available to process.")
            sys.exit(1)

    print(f"[+] Successfully loaded {len(athletes)} athletes.")

    # 3. Compute daily delta & update history
    daily_logs, history = process_daily_delta(athletes, today_str=today_str, target_km=target_km)

    # 4. Sync to Google Sheets if configured
    if webhook_url:
        payload = {
            "date": today_str,
            "target_km": target_km,
            "daily_logs": daily_logs,
            "athlete_totals": history.get("athlete_totals", {})
        }
        sync_to_google_sheet(webhook_url, payload)
    else:
        print("[*] Google Sheet sync skipped (Set GOOGLE_SHEET_WEBHOOK_URL to enable).")

    # 5. Print Daily Summary
    print("\n" + "-" * 50)
    print(f"🔥 TODAY'S TOP RUNNERS ({today_str})")
    print("-" * 50)
    top_today = [l for l in daily_logs if l["daily_distance_km"] > 0][:5]
    if top_today:
        for idx, runner in enumerate(top_today, 1):
            print(f"  {idx}. {runner['name']}: {runner['daily_distance_km']} km (Pace: {runner['avg_pace']}/km)")
    else:
        print("  No new runs logged yet today.")

    print("\n🏆 OVERALL 100K LEADERBOARD (TOP 5):")
    totals = list(history.get("athlete_totals", {}).values())
    totals.sort(key=lambda x: x["total_challenge_km"], reverse=True)
    for idx, a in enumerate(totals[:5], 1):
        status = "🏅 FINISHED!" if a.get("is_finisher") else f"{a.get('remaining_km', 0)} km left"
        print(f"  {idx}. {a['name']}: {a['total_challenge_km']} / {target_km} km ({a.get('pct_completed', 0)}%) - {status}")

    print("=" * 60)
    print("✅ Sync complete! Open index.html to view the interactive dashboard.")
    print("=" * 60)


if __name__ == "__main__":
    main()
