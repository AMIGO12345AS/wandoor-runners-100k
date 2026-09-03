"""
Delta Engine: Converts Strava's weekly cumulative leaderboard into day-by-day running records.
Handles:
- Daily distance, runs, elevation deltas (Today - Yesterday)
- Weekly resets (Monday rollover where Strava restarts cumulative from 0)
- Overall 100k Challenge cumulative tracking
- Consistency streaks and daily podium calculations
"""

import os
import json
from datetime import datetime, date

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
    Computes daily delta from previous snapshot and updates club history.
    """
    if not today_str:
        today_str = date.today().isoformat()

    snapshot_file = os.path.join(data_dir, "latest_snapshot.json")
    history_file = os.path.join(data_dir, "club_history.json")

    previous_snapshot = load_json(snapshot_file, {})
    history = load_json(history_file, {
        "club_name": "Wandoor Runners Monsoon 100k challenge 2026",
        "target_km": target_km,
        "last_updated": None,
        "dates": [],
        "daily_records": {},
        "athlete_totals": {}
    })

    prev_athletes_map = {}
    if previous_snapshot and "athletes" in previous_snapshot:
        for a in previous_snapshot["athletes"]:
            prev_athletes_map[a["athlete_id"]] = a

    daily_logs = []
    
    for a in current_athletes:
        aid = a["athlete_id"]
        name = a["name"]
        curr_dist = a.get("distance_km", 0.0)
        curr_runs = a.get("runs_count", 0)
        curr_elev = a.get("elev_gain_m", 0)

        prev_a = prev_athletes_map.get(aid)
        
        if prev_a is None:
            # First time seeing this athlete today
            daily_dist = curr_dist
            daily_runs = curr_runs
            daily_elev = curr_elev
        else:
            prev_dist = prev_a.get("distance_km", 0.0)
            prev_runs = prev_a.get("runs_count", 0)
            prev_elev = prev_a.get("elev_gain_m", 0)

            # Check if Strava reset week (e.g. Monday morning)
            if curr_dist < prev_dist:
                daily_dist = curr_dist
                daily_runs = curr_runs
                daily_elev = curr_elev
            else:
                daily_dist = round(curr_dist - prev_dist, 2)
                daily_runs = max(0, curr_runs - prev_runs)
                daily_elev = max(0, curr_elev - prev_elev)

        # Build daily log entry
        daily_log = {
            "date": today_str,
            "athlete_id": aid,
            "name": name,
            "avatar_url": a.get("avatar_url", ""),
            "daily_distance_km": max(0.0, daily_dist),
            "daily_runs": daily_runs,
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
        aid = log["athlete_id"]
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
        
        # Check if already logged for today
        already_logged_today = today_str in rec["daily_breakdown"]
        
        if not already_logged_today:
            rec["total_challenge_km"] = round(rec["total_challenge_km"] + dist, 2)
            rec["daily_breakdown"][today_str] = dist
            if dist > 0.0:
                rec["active_days"] += 1
                rec["current_streak"] += 1
                if dist > rec["best_day_km"]:
                    rec["best_day_km"] = dist
            else:
                rec["current_streak"] = 0
        else:
            # Overwrite today's entry
            prev_today_dist = rec["daily_breakdown"][today_str]
            diff = dist - prev_today_dist
            rec["total_challenge_km"] = round(rec["total_challenge_km"] + diff, 2)
            rec["daily_breakdown"][today_str] = dist

        rec["pct_completed"] = min(100.0, round((rec["total_challenge_km"] / target_km) * 100.0, 1))
        rec["is_finisher"] = rec["total_challenge_km"] >= target_km
        rec["remaining_km"] = max(0.0, round(target_km - rec["total_challenge_km"], 2))

    # Update history dates and daily records
    if today_str not in history["dates"]:
        history["dates"].append(today_str)
        history["dates"].sort()

    history["daily_records"][today_str] = daily_logs
    history["athlete_totals"] = athlete_totals
    history["last_updated"] = datetime.now().isoformat()

    # Save latest snapshot and updated history
    save_json(snapshot_file, {
        "timestamp": datetime.now().isoformat(),
        "date": today_str,
        "athletes": current_athletes
    })
    save_json(history_file, history)

    print(f"[+] Delta engine processed {len(daily_logs)} runners for {today_str}.")
    return daily_logs, history
