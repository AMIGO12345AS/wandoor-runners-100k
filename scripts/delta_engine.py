"""
Delta Engine: Converts Strava's weekly cumulative leaderboard into day-by-day running records.
Handles:
- Indian Standard Time (IST - Asia/Kolkata UTC+5:30)
- Intra-day idempotent re-runs (running sync every hour never reduces mileage)
- Monday Weekly Reset (Strava resets to 0 on Monday; never subtracts Sunday's total)
- Activity deletion/privacy protection (prevents negative mileage)
- 100k Challenge cumulative tracking & streaks
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta

# Explicit Indian Standard Time (UTC + 05:30)
IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now():
    return datetime.now(IST)


def get_ist_today_str():
    return get_ist_now().strftime("%Y-%m-%d")


def clean_name(name):
    if not name:
        return "Runner"
    text = str(name).strip()
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
    Computes daily delta from baseline and updates club history.
    Handles hourly runs, Monday week rollovers, and protects historical data.
    """
    now_ist = get_ist_now()
    if not today_str:
        today_str = now_ist.strftime("%Y-%m-%d")

    # Day of week in IST: Monday is 0, Sunday is 6
    today_weekday = datetime.strptime(today_str, "%Y-%m-%d").weekday()
    is_monday = (today_weekday == 0)

    # Week start date (Monday) for current week
    today_dt = datetime.strptime(today_str, "%Y-%m-%d")
    current_monday_str = (today_dt - timedelta(days=today_weekday)).strftime("%Y-%m-%d")

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

    # Intra-day baseline handling:
    # If the previous snapshot is from a PRIOR day, save it as yesterday's baseline.
    snapshot_date = previous_snapshot.get("date")
    if snapshot_date and snapshot_date < today_str:
        yesterday_baseline = previous_snapshot
        save_json(baseline_file, yesterday_baseline)

    base_athletes_map = {}
    if not is_monday:
        # On Tue-Sun, we compare against yesterday's end-of-day reading from the same week
        if yesterday_baseline and "athletes" in yesterday_baseline:
            for a in yesterday_baseline["athletes"]:
                base_athletes_map[str(a["athlete_id"])] = a
        elif previous_snapshot and "athletes" in previous_snapshot and snapshot_date < today_str:
            for a in previous_snapshot["athletes"]:
                base_athletes_map[str(a["athlete_id"])] = a
    else:
        # On Monday, Strava starts at 0.0 km. Baseline is 0 for everyone!
        base_athletes_map = {}

    athlete_totals = history.get("athlete_totals", {})
    daily_logs = []
    
    for a in current_athletes:
        aid = str(a["athlete_id"])
        name = clean_name(a["name"])
        curr_dist = a.get("distance_km", 0.0)
        curr_runs = a.get("runs_count", 0)
        curr_elev = a.get("elev_gain_m", 0)

        if is_monday:
            # Monday: All mileage on Strava today is from today (started from 0)
            daily_dist = curr_dist
            daily_runs = curr_runs
            daily_elev = curr_elev
        else:
            base_a = base_athletes_map.get(aid)
            if base_a is None:
                # First time seeing athlete this week in baseline.
                # Guard: check if they already have logged runs in current week prior to today.
                rec_existing = athlete_totals.get(aid, {})
                prior_week_dist = sum(
                    dist for d, dist in rec_existing.get("daily_breakdown", {}).items()
                    if current_monday_str <= d < today_str
                )
                daily_dist = max(0.0, round(curr_dist - prior_week_dist, 2))
                daily_runs = curr_runs
                daily_elev = curr_elev
            else:
                base_dist = base_a.get("distance_km", 0.0)
                base_runs = base_a.get("runs_count", 0)
                base_elev = base_a.get("elev_gain_m", 0)

                # Check if athlete deleted activity or if Strava had a mid-week anomaly
                if curr_dist < base_dist:
                    # Protection: do not produce negative distance
                    daily_dist = 0.0
                    daily_runs = 0
                    daily_elev = 0
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

    # Ensure all enrolled challenge athletes have a daily log entry (rest day with 0.0 km if not active on Strava today)
    logged_aids = {log["athlete_id"] for log in daily_logs}
    for aid, rec in athlete_totals.items():
        if aid not in logged_aids:
            daily_logs.append({
                "date": today_str,
                "athlete_id": aid,
                "name": rec["name"],
                "avatar_url": rec.get("avatar_url", "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"),
                "daily_distance_km": 0.0,
                "daily_runs": 0,
                "daily_elev_gain_m": 0,
                "avg_pace": "--",
                "weekly_cumulative_km": 0.0
            })
            if today_str not in rec.get("daily_breakdown", {}):
                rec["daily_breakdown"][today_str] = 0.0

    # Sort today's runners by distance today
    daily_logs.sort(key=lambda x: x["daily_distance_km"], reverse=True)

    # Update athlete_totals across the entire challenge
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
        rec["name"] = log["name"]
        rec["avatar_url"] = log["avatar_url"]
        if log["avg_pace"] and log["avg_pace"] != "--":
            rec["latest_pace"] = log["avg_pace"]
        
        prev_today_dist = rec.get("daily_breakdown", {}).get(today_str, 0.0)
        diff = round(dist - prev_today_dist, 2)
        rec["total_challenge_km"] = max(0.0, round(rec.get("total_challenge_km", 0.0) + diff, 2))
        rec["daily_breakdown"][today_str] = dist

    # Fully recalculate streak, active days, best day, and progress for ALL athletes
    for aid, rec in athlete_totals.items():
        bd = rec.get("daily_breakdown", {})
        active_days = sum(1 for d, val in bd.items() if val > 0)
        best_day = max(bd.values()) if bd else 0.0
        
        rec["active_days"] = active_days
        rec["best_day_km"] = round(best_day, 2)
        rec["pct_completed"] = min(100.0, round((rec["total_challenge_km"] / target_km) * 100.0, 1))
        rec["is_finisher"] = rec["total_challenge_km"] >= target_km
        rec["remaining_km"] = max(0.0, round(target_km - rec["total_challenge_km"], 2))

        # Consecutive active streak leading up to today (or yesterday if today has not been run yet)
        streak = 0
        sorted_dates = sorted(bd.keys())
        if sorted_dates:
            last_date = sorted_dates[-1]
            check_dates = list(reversed(sorted_dates))
            if bd.get(last_date, 0.0) == 0.0 and len(check_dates) > 1:
                check_dates = check_dates[1:]
            for d in check_dates:
                if bd.get(d, 0.0) > 0.0:
                    streak += 1
                else:
                    break
        rec["current_streak"] = streak

    # Update history dates and daily records
    if today_str not in history["dates"]:
        history["dates"].append(today_str)
        history["dates"].sort()

    history["daily_records"][today_str] = daily_logs
    history["athlete_totals"] = athlete_totals
    history["last_updated"] = now_ist.isoformat()

    # Save latest snapshot with IST date
    save_json(snapshot_file, {
        "timestamp": now_ist.isoformat(),
        "date": today_str,
        "athletes": current_athletes
    })
    save_json(history_file, history)

    print(f"[+] Delta engine processed {len(daily_logs)} runners for {today_str} (IST). Monday={is_monday}")
    return daily_logs, history
