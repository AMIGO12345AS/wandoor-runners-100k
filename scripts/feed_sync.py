"""
Strava Club Activity Feed Sync Engine
Fetches individual activities from Strava Club Feed and builds an exact day-by-day,
athlete-by-athlete running record strictly starting from September 1, 2026 (IST).
Filters out August 31st and pre-challenge runs completely.
Offline & online resilient.
"""

import os
import sys
import json
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.parse import urlencode

# Explicit Indian Standard Time (UTC + 05:30)
IST = timezone(timedelta(hours=5, minutes=30))
CHALLENGE_START_DATE = "2026-09-01"


def clean_name(name):
    if not name:
        return "Runner"
    text = str(name).strip()
    cleaned = re.sub(r"[^\w\s\.\-]", "", text)
    return " ".join(cleaned.split()).strip()


def parse_pace(elapsed_sec, dist_km):
    if dist_km <= 0 or elapsed_sec <= 0:
        return "--"
    sec_per_km = elapsed_sec / dist_km
    p_min = int(sec_per_km // 60)
    p_sec = int(sec_per_km % 60)
    return f"{p_min}:{p_sec:02d}"


def parse_activity_stats(act):
    dist_km = 0.0
    elev_m = 0
    time_str = "--"
    
    for s in act.get("stats", []):
        k = s.get("key", "")
        v = s.get("value", "")
        if k == "stat_one":
            m = re.search(r"([\d\.]+)", v)
            if m:
                dist_km = float(m.group(1))
        elif k == "stat_two":
            m = re.search(r"([\d\,]+)", v)
            if m:
                elev_m = int(m.group(1).replace(",", ""))
        elif k == "stat_three":
            clean_t = re.sub(r"<[^>]+>", " ", v)
            time_str = " ".join(clean_t.split()).strip()
            
    elapsed_sec = act.get("elapsedTime", 0)
    pace_str = parse_pace(elapsed_sec, dist_km)
    return dist_km, elev_m, elapsed_sec, time_str, pace_str


def fetch_all_club_activities(club_id="2317931", session_cookie=None, since_date=CHALLENGE_START_DATE):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    if session_cookie:
        session_cookie = session_cookie.strip()
        if not session_cookie.startswith("_strava4_session="):
            headers["Cookie"] = f"_strava4_session={session_cookie}"
        else:
            headers["Cookie"] = session_cookie

    all_activities = []
    cursor = None
    page = 1

    print(f"[*] Fetching Strava club activity feed for club {club_id} since {since_date} (IST)...")

    while True:
        params = {"feed_type": "club"}
        if cursor:
            params["cursor"] = cursor
        url = f"https://www.strava.com/clubs/{club_id}/feed?{urlencode(params)}"
        
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[!] Error fetching feed page {page}: {e}")
            break

        entries = data.get("entries", [])
        if not entries:
            print(f"[*] No more entries at page {page}.")
            break

        valid_count = 0
        for e in entries:
            act = e.get("activity")
            if not act or act.get("type") != "Run":
                continue

            start_str = act.get("startDate")
            if not start_str:
                continue

            dt_utc = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            dt_ist = dt_utc.astimezone(IST)
            date_ist_str = dt_ist.strftime("%Y-%m-%d")

            dist_km, elev_m, elapsed_sec, time_str, pace_str = parse_activity_stats(act)
            athlete_info = act.get("athlete", {})
            aid = str(athlete_info.get("athleteId"))
            aname = clean_name(athlete_info.get("athleteName"))
            avatar = athlete_info.get("avatarUrl") or "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"

            all_activities.append({
                "activity_id": str(act.get("id")),
                "activity_name": act.get("activityName", "Run"),
                "athlete_id": aid,
                "athlete_name": aname,
                "avatar_url": avatar,
                "date_ist": date_ist_str,
                "dt_ist": dt_ist.strftime("%Y-%m-%d %H:%M:%S"),
                "distance_km": dist_km,
                "elev_gain_m": elev_m,
                "elapsed_sec": elapsed_sec,
                "duration": time_str,
                "pace": pace_str
            })
            valid_count += 1

        last_startDate = entries[-1].get("activity", {}).get("startDate", "")
        if last_startDate:
            last_dt_utc = datetime.strptime(last_startDate, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            last_dt_ist = last_dt_utc.astimezone(IST)
            last_date_ist_str = last_dt_ist.strftime("%Y-%m-%d")
            # If we've reached earlier than Aug 30, stop pagination
            if last_date_ist_str < "2026-08-30":
                print(f"[*] Reached {last_date_ist_str} (before challenge start). Stopping pagination.")
                break

        last_cursor_data = entries[-1].get("cursorData")
        if not last_cursor_data or "updated_at" not in last_cursor_data:
            break
        cursor = last_cursor_data["updated_at"]
        page += 1
        time.sleep(0.2)

    print(f"[+] Total raw run activities collected: {len(all_activities)}")
    return all_activities


def sync_from_feed(data_dir="data", config_file="config.json"):
    config = {}
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

    club_id = config.get("club_id", "2317931")
    session_cookie = config.get("strava_session_cookie", "")
    target_km = float(config.get("target_distance_km", 100.0))

    history_file = os.path.join(data_dir, "club_history.json")
    history = {}
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)

    existing_totals = history.get("athlete_totals", {})

    # Fetch live activities
    activities = fetch_all_club_activities(club_id, session_cookie, since_date=CHALLENGE_START_DATE)

    # Filter strictly September 1 onwards
    sep_activities = [a for a in activities if a["date_ist"] >= CHALLENGE_START_DATE]
    print(f"[+] Filtered to {len(sep_activities)} run activities strictly from {CHALLENGE_START_DATE} onwards.")

    # Determine all competition dates up to today in IST
    today_ist = datetime.now(IST).strftime("%Y-%m-%d")
    all_dates_set = set(history.get("dates", []))
    all_dates_set.add(today_ist)
    for a in sep_activities:
        all_dates_set.add(a["date_ist"])
    
    sorted_dates = sorted(list(all_dates_set))
    print(f"[*] Competition date range: {sorted_dates[0]} to {sorted_dates[-1]} ({len(sorted_dates)} days)")

    # Group activities by (athlete_id, date_ist)
    athlete_day_map = {}
    athlete_meta = {}

    for a in sep_activities:
        aid = a["athlete_id"]
        d = a["date_ist"]

        if aid not in athlete_meta:
            athlete_meta[aid] = {
                "athlete_id": aid,
                "name": a["athlete_name"],
                "avatar_url": a["avatar_url"]
            }

        key = (aid, d)
        if key not in athlete_day_map:
            athlete_day_map[key] = {
                "distance_km": 0.0,
                "runs_count": 0,
                "elev_gain_m": 0,
                "elapsed_sec": 0,
                "latest_pace": a["pace"],
                "activity_name": a["activity_name"]
            }

        rec = athlete_day_map[key]
        rec["distance_km"] = round(rec["distance_km"] + a["distance_km"], 2)
        rec["runs_count"] += 1
        rec["elev_gain_m"] += a["elev_gain_m"]
        rec["elapsed_sec"] += a["elapsed_sec"]
        if a["pace"] != "--":
            rec["latest_pace"] = a["pace"]

    # Gather all athletes: existing enrolled + new runners discovered in Strava
    all_aids = set(existing_totals.keys()) | set(athlete_meta.keys())

    # Build updated athlete_totals
    updated_totals = {}
    daily_records = {d: [] for d in sorted_dates}

    for aid in all_aids:
        # Base metadata
        ex = existing_totals.get(aid, {})
        meta = athlete_meta.get(aid, {})

        display_name = meta.get("name") or ex.get("name") or "Runner"
        avatar_url = meta.get("avatar_url") or ex.get("avatar_url") or "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"

        daily_breakdown = {}
        total_dist = 0.0
        active_days = 0
        best_day = 0.0
        latest_pace = "--"

        for d in sorted_dates:
            day_data = athlete_day_map.get((aid, d))
            if day_data and day_data["distance_km"] > 0:
                dist = day_data["distance_km"]
                runs = day_data["runs_count"]
                elev = day_data["elev_gain_m"]
                sec = day_data["elapsed_sec"]
                pace = parse_pace(sec, dist)
                if pace != "--":
                    latest_pace = pace

                daily_breakdown[d] = dist
                total_dist = round(total_dist + dist, 2)
                active_days += 1
                if dist > best_day:
                    best_day = dist

                log_entry = {
                    "date": d,
                    "athlete_id": aid,
                    "name": display_name,
                    "avatar_url": avatar_url,
                    "daily_distance_km": dist,
                    "daily_runs": runs,
                    "daily_elev_gain_m": elev,
                    "avg_pace": pace,
                    "weekly_cumulative_km": total_dist
                }
            else:
                daily_breakdown[d] = 0.0
                log_entry = {
                    "date": d,
                    "athlete_id": aid,
                    "name": display_name,
                    "avatar_url": avatar_url,
                    "daily_distance_km": 0.0,
                    "daily_runs": 0,
                    "daily_elev_gain_m": 0,
                    "avg_pace": "--",
                    "weekly_cumulative_km": total_dist
                }

            daily_records[d].append(log_entry)

        # Calculate current consecutive streak
        streak = 0
        if sorted_dates:
            last_date = sorted_dates[-1]
            check_dates = list(reversed(sorted_dates))
            # If today has not been run yet, evaluate up to yesterday
            if daily_breakdown.get(last_date, 0.0) == 0.0 and len(check_dates) > 1:
                check_dates = check_dates[1:]
            for cd in check_dates:
                if daily_breakdown.get(cd, 0.0) > 0.0:
                    streak += 1
                else:
                    break

        pct = min(100.0, round((total_dist / target_km) * 100.0, 1))

        athlete_rec = {
            "athlete_id": aid,
            "sl_no": ex.get("sl_no"),
            "name": display_name,
            "excel_name": ex.get("excel_name"),
            "avatar_url": avatar_url,
            "mobile": ex.get("mobile", ""),
            "total_challenge_km": total_dist,
            "target_km": target_km,
            "active_days": active_days,
            "current_streak": streak,
            "best_day_km": best_day,
            "latest_pace": latest_pace if latest_pace != "--" else ex.get("latest_pace", "--"),
            "pct_completed": pct,
            "is_finisher": total_dist >= target_km,
            "remaining_km": max(0.0, round(target_km - total_dist, 2)),
            "daily_breakdown": daily_breakdown
        }
        updated_totals[aid] = athlete_rec

    # Sort daily records by distance descending
    for d in sorted_dates:
        daily_records[d].sort(key=lambda x: x["daily_distance_km"], reverse=True)

    # Save to club_history.json
    history_payload = {
        "club_name": history.get("club_name", "Wandoor Runners Monsoon 100k challenge 2026"),
        "target_km": target_km,
        "last_updated": datetime.now(IST).isoformat(),
        "dates": sorted_dates,
        "daily_records": daily_records,
        "athlete_totals": updated_totals
    }

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_payload, f, indent=2, ensure_ascii=False)

    print(f"[+] Successfully synchronized {len(updated_totals)} athletes with exact Strava activities!")

    # Also update latest_snapshot.json with the current overall leaderboard standings
    snapshot_file = os.path.join(data_dir, "latest_snapshot.json")
    sorted_for_snapshot = sorted(updated_totals.values(), key=lambda x: x["total_challenge_km"], reverse=True)
    snapshot_athletes = []
    for idx, a in enumerate(sorted_for_snapshot, 1):
        snapshot_athletes.append({
            "rank": idx,
            "athlete_id": a["athlete_id"],
            "name": a["name"],
            "avatar_url": a["avatar_url"],
            "distance_km": a["total_challenge_km"],
            "runs_count": a["active_days"],
            "longest_km": a["best_day_km"],
            "avg_pace": a.get("latest_pace", "--"),
            "elev_gain_m": 0
        })

    snapshot_payload = {
        "timestamp": datetime.now(IST).isoformat(),
        "date": today_ist,
        "athletes": snapshot_athletes
    }
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot_payload, f, indent=2, ensure_ascii=False)

    print(f"[+] Updated {snapshot_file} with {len(snapshot_athletes)} ranked athletes.")
    return history_payload


if __name__ == "__main__":
    sync_from_feed()
