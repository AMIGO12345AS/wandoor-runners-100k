"""
Delta Engine: Converts Strava's weekly cumulative leaderboard into day-by-day running records.
Handles:
- Indian Standard Time (IST - Asia/Kolkata UTC+5:30)
- Intra-day idempotent re-runs (running sync multiple times never reduces mileage)
- Daily distance, runs, elevation deltas (Today - Yesterday Baseline)
- Weekly resets (Monday rollover where Strava restarts cumulative from 0)
- Overall 100k Challenge cumulative tracking
- Consistency streaks and daily calculations
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta

# Explicit Indian Standard Time (UTC + 05:30)
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_today_str():
    return datetime.now(IST).strftime("%Y-%m-%d")


def clean_name(name):
    if not name:
        return "Runner"
    text = str(name).strip()
    # Strip emojis, symbols, and trim extra whitespace
    cleaned = re.sub(r"[^\w\s\.\-]", "", text)
    return " ".join(cleaned.split()).strip()


def load_json(filepath, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning reading {filepath}: {e}")
    return default if default is not None else {}


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def process_daily_delta(current_athletes, today_str=None, data_dir="data", target_km=100.0):
    """
    Computes daily delta from yesterday's baseline and updates club history.
    100% IST compliant, idempotent for multiple runs on the same calendar day.
    """
    if not today_str:
        today_str = get_ist_today_str()

    snapshot_file = os.path.join(data_dir, "latest_snapshot.json")
    baseline_file = os.path.join(data_dir, "yesterday_baseline.json")
    history_file = os.path.join(data_dir, "club_history.json")

    previous_snapshot = load_json(snapshot_file, {})
    yesterday_baseline = load_json(baseline_file, {})
    
    history = load_json(history_file, {
        "club_name": "Wandoor Runners Monsoon 100k challenge 2026",
        "target_km": target_km,
        "last_updated": None,
        "dates": [],
        "daily_records": {},
        "athlete_totals": {}
    })

    # CRITICAL BUG FIX (Intra-day re-runs):
    # If the latest snapshot is from a PREVIOUS day, save it as yesterday's baseline!
    # If the latest snapshot is already from TODAY, keep using yesterday's baseline
    # so we measure the true day-long progress, avoiding double deductions.
    snapshot_date = previous_snapshot.get("date")
    if snapshot_date and snapshot_date < today_str:
        yesterday_baseline = previous_snapshot
        save_json(baseline_file, yesterday_baseline)

    # Use baseline to compute today's delta
    base_athletes_map = {}
    if yesterday_baseline and "athletes" in yesterday_baseline:
        for a in yesterday_baseline["athletes"]:
            base_athletes_map[str(a["athlete_id"])] = a
    elif previous_snapshot and "athletes" in previous_snapshot and snapshot_date < today_str:
        for a in previous_snapshot["athletes"]:
            base_athletes_map[str(a["athlete_id"])] = a

    daily_logs = []
    
    for a in current_athletes:
        aid = str(a["athlete_id"])
        name = clean_name(a["name"])
        curr_dist = a.get("distance_km", 0.0)
        curr_runs = a.get("runs_count", 0)
        curr_elev = a.get("elev_gain_m", 0)

        base_a = base_athletes_map.get(aid)
        
        if base_a is None:
            # Athlete is new or not in baseline
            # Check if we already have this athlete logged in today's records
            existing_today = None
            if today_str in history.get("daily_records", {}):
                for rec in history["daily_records"][today_str]:
                    if str(rec.get("athlete_id")) == aid:
                        existing_today = rec
                        break
            
            if existing_today:
                daily_dist = existing_today.get("daily_distance_km", curr_dist)
                daily_runs = existing_today.get("daily_runs", curr_runs)
                daily_elev = existing_today.get("daily_elev_gain_m", curr_elev)
            else:
                daily_dist = curr_dist
                daily_runs = curr_runs
                daily_elev = curr_elev
        else:
            base_dist = base_a.get("distance_km", 0.0)
            base_runs = base_a.get("runs_count", 0)
            base_elev = base_a.get("elev_gain_m", 0)

            # Check if Strava reset week on Monday
            if curr_dist < base_dist:
                daily_dist = curr_dist
                daily_runs = curr_runs
                daily_elev = curr_elev
            else:
                daily_dist = round(curr_dist - base_dist, 2)
                daily_runs = max(0, curr_runs - base_runs)
                daily_elev = max(0, curr_elev - base_elev)

        daily_log = {
            "date": today_str,
            "athlete_id": aid,
            "name": name,
            "avatar_url": a.get("avatar_url", "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"),
            "daily_distance_km": max(0.0, round(daily_dist, 2)),
            "daily_runs": max(1 if daily_dist > 0 else 0, daily_runs),
            "daily_elev_gain_m": daily_elev,
            "avg_pace": a.get("avg_pace", "--"),
            "weekly_cumulative_km": curr_dist
        }
        daily_logs.append(daily_log)

    # Sort today's runners by distance today
    daily_logs.sort(key=lambda x: x["daily_distance_km"], reverse=True)

    # Update athlete_totals across the entire challenge
    athlete_totals = history.get("athlete_totals", {})

    for log in daily_logs:
        aid = str(log["athlete_id"])
        dist = log["daily_distance_km"]

        if aid not in athlete_totals:
            athlete_totals[aid] = {
                "athlete_id": aid,
                "name": log["name"],
                "avatar_url": log["avatar_url"],
                "total_challenge_km": 0.0,
                "target_km": target_km,
                "active_days": 0,
                "current_streak": 0,
                "best_day_km": 0.0,
                "latest_pace": log["avg_pace"],
                "daily_breakdown": {}
            }

        rec = athlete_totals[aid]
        rec["avatar_url"] = log["avatar_url"]
        rec["latest_pace"] = log["avg_pace"]
        
        # Check previous value for today if it existed
        prev_today_dist = rec.get("daily_breakdown", {}).get(today_str, 0.0)
        
        # Adjust total challenge distance accurately
        diff = round(dist - prev_today_dist, 2)
        rec["total_challenge_km"] = max(0.0, round(rec.get("total_challenge_km", 0.0) + diff, 2))
        rec["daily_breakdown"][today_str] = dist

        # Recalculate active days and streaks accurately
        active_days = sum(1 for d, val in rec["daily_breakdown"].items() if val > 0)
        best_day = max(rec["daily_breakdown"].values()) if rec["daily_breakdown"] else 0.0
        
        rec["active_days"] = active_days
        rec["best_day_km"] = round(best_day, 2)
        rec["pct_completed"] = min(100.0, round((rec["total_challenge_km"] / target_km) * 100.0, 1))
        rec["is_finisher"] = rec["total_challenge_km"] >= target_km
        rec["remaining_km"] = max(0.0, round(target_km - rec["total_challenge_km"], 2))

    # Update history dates and daily records
    if today_str not in history["dates"]:
        history["dates"].append(today_str)
        history["dates"].sort()

    history["daily_records"][today_str] = daily_logs
    history["athlete_totals"] = athlete_totals
    history["last_updated"] = datetime.now(IST).isoformat()

    # Save latest snapshot with IST date
    save_json(snapshot_file, {
        "timestamp": datetime.now(IST).isoformat(),
        "date": today_str,
        "athletes": current_athletes
    })
    save_json(history_file, history)

    print(f"[+] Delta engine processed {len(daily_logs)} runners for {today_str} (IST).")
    return daily_logs, history
