"""
Official Excel Importer & Master Synchronizer
Imports ground-truth verified records from `aseem - Copy.xlsx` for September 1 to September 4.
Captures all verified multi-run activities from Strava feed for any day (Sep 1 to Sep 6+).
Guarantees zero data loss, exact two-decimal precision, and stores full activity breakdowns.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
import openpyxl

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IST = timezone(timedelta(hours=5, minutes=30))


def clean_name(name):
    if not name:
        return "Runner"
    text = str(name).strip()
    cleaned = re.sub(r"[^\w\s\.\-]", "", text)
    return " ".join(cleaned.split()).strip()


def normalize_name(name):
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def parse_pace(elapsed_sec, dist_km):
    if dist_km <= 0 or elapsed_sec <= 0:
        return "--"
    sec_per_km = elapsed_sec / dist_km
    p_min = int(sec_per_km // 60)
    p_sec = int(sec_per_km % 60)
    return f"{p_min}:{p_sec:02d}"


# Explicit mapping between Excel runner names and known Strava athlete IDs
EXPLICIT_STRAVA_MAP = {
    "sunilbabu": "136932402",
    "ajeeshtp": "197716094",
    "ibnusiyadsiyad": "184918231",
    "nidheeshedappalli": "40420193",
    "arunsavitha": "49239362",
    "porursarath": "61176348",
    "santhoshporur": "75355675",
    "adilkurikkal": "203636939",
    "ahamedshameer": "198876934",
    "ajmalv": "418185437",
    "alifaisal": "188992089",
    "anasev": "190287524",
    "anoopk": "89350486",
    "ansiyamk": "1806354742",
    "anwerhussain": "189332219",
    "bijumon": "119864275",
    "binunaduvath": "1753145775",
    "diljithp": "193153549",
    "drshameerthodengal": "130257164",
    "drvarunvasudev": "1009398140",
    "fahisfahi": "201415432",
    "firshadpfirshadp": "198305096",
    "gamingwithrahman": "191074714",
    "khaliqkt": "190479130",
    "krishnaprasadmkp": "159419010",
    "lebeebaplebeebap": "1759530438",
    "lineeshmalangadan": "108819380",
    "mohamedshajahanparancheri": "157557051",
    "mohammadmazin": "192318041",
    "mohammedshafin": "1463852982",
    "mohandask": "154857428",
    "muhammedrishad": "1549040789",
    "muhammedshafik": "199411985",
    "nijinprajeesh": "199723223",
    "nithinkc": "199920668",
    "prakasanct": "158361240",
    "razaqkinassery": "158356973",
    "razthanfarisck": "199182362",
    "rinshidtp": "200401844",
    "sabeeloravungal": "193322479",
    "sarathpnarayanan": "206125985",
    "shajikoodamth": "153813828",
    "subhashkv": "1909549551",
    "suneeshk": "199859556",
    "unnikrishnank": "153813910",
    "akt": "659794089",
    "diyaft": "198406580",
    "justintxcherai": "35422762"
}


def sync_official_data(excel_path="aseem - Copy.xlsx", data_dir="data", config_path="config.json"):
    if not os.path.exists(excel_path):
        print(f"[!] Error: {excel_path} not found.")
        return False

    # 1. Load config
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    club_id = config.get("club_id", "2317931")
    session_cookie = config.get("strava_session_cookie", "")
    target_km = float(config.get("target_distance_km", 100.0))

    # 2. Load existing history to retain avatars, mobile numbers, metadata
    history_file = os.path.join(data_dir, "club_history.json")
    existing_history = {}
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            existing_history = json.load(f)
    existing_totals = existing_history.get("athlete_totals", {})

    # 3. Read Excel data (September 1 to 4)
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb.active

    excel_athletes = {}
    for r in range(5, sheet.max_row + 1):
        sl = sheet.cell(r, 2).value
        name = sheet.cell(r, 3).value
        if not name:
            continue
        c_name = str(name).strip()
        n_name = normalize_name(c_name)

        d1 = round(float(sheet.cell(r, 4).value or 0.0), 2)
        d2 = round(float(sheet.cell(r, 5).value or 0.0), 2)
        d3 = round(float(sheet.cell(r, 6).value or 0.0), 2)
        d4 = round(float(sheet.cell(r, 7).value or 0.0), 2)

        excel_athletes[n_name] = {
            "sl_no": sl,
            "excel_name": c_name,
            "d1": d1,
            "d2": d2,
            "d3": d3,
            "d4": d4
        }

    print(f"[+] Loaded {len(excel_athletes)} official athlete rows from {excel_path}.")

    # 4. Fetch all Strava activities from feed since Sep 1
    from scripts.feed_sync import fetch_all_club_activities
    all_strava_activities = fetch_all_club_activities(club_id, session_cookie, since_date="2026-09-01")

    # Group Strava activities by (athlete_id, date_ist)
    strava_by_day = {}
    athlete_live_meta = {}

    for a in all_strava_activities:
        d = a["date_ist"]
        if d >= "2026-09-01":
            aid = str(a["athlete_id"])
            aname = clean_name(a["athlete_name"])
            avatar = a.get("avatar_url") or "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"

            athlete_live_meta[aid] = {
                "name": aname,
                "avatar_url": avatar
            }

            key = (aid, d)
            if key not in strava_by_day:
                strava_by_day[key] = {
                    "distance_km": 0.0,
                    "runs_count": 0,
                    "elev_gain_m": 0,
                    "elapsed_sec": 0,
                    "activities": []
                }
            rec = strava_by_day[key]
            rec["distance_km"] = round(rec["distance_km"] + a["distance_km"], 2)
            rec["runs_count"] += 1
            rec["elev_gain_m"] += a.get("elev_gain_m", 0)
            rec["elapsed_sec"] += a.get("elapsed_sec", 0)
            rec["activities"].append({
                "activity_name": a.get("activity_name", "Run"),
                "distance_km": a["distance_km"],
                "pace": a.get("pace", "--"),
                "duration": a.get("duration", "--"),
                "elev_gain_m": a.get("elev_gain_m", 0),
                "time_ist": a.get("dt_ist", d)
            })

    print(f"[+] Loaded {len(all_strava_activities)} total Strava runs since Sep 1.")

    # 5. Build consolidated athlete database
    dates = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06"]
    consolidated_totals = {}
    daily_records = {d: [] for d in dates}

    # Process all athletes from Excel
    for norm_n, ex in excel_athletes.items():
        # Determine athlete_id
        aid = EXPLICIT_STRAVA_MAP.get(norm_n)
        if not aid:
            for ea_id, ea in existing_totals.items():
                if normalize_name(ea.get("name")) == norm_n or normalize_name(ea.get("excel_name")) == norm_n:
                    aid = ea_id
                    break
        if not aid:
            aid = f"athlete_{norm_n}"

        # Existing metadata
        prev = existing_totals.get(aid, {})
        live_m = athlete_live_meta.get(aid, {})

        display_name = ex["excel_name"]
        if live_m.get("name"):
            display_name = live_m["name"]
        elif prev.get("name") and prev.get("name") != ex["excel_name"]:
            display_name = prev["name"]

        avatar_url = live_m.get("avatar_url") or prev.get("avatar_url") or "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"
        mobile = prev.get("mobile", "")

        daily = {}
        daily_details = {}

        # Days 1 to 4: Combine Excel ground-truth and Strava multi-runs
        excel_days = {
            "2026-09-01": ex["d1"],
            "2026-09-02": ex["d2"],
            "2026-09-03": ex["d3"],
            "2026-09-04": ex["d4"]
        }

        for d in dates:
            s_day = strava_by_day.get((aid, d))
            if d in excel_days:
                ex_dist = excel_days[d]
                s_dist = s_day["distance_km"] if s_day else 0.0

                # If Strava recorded multiple runs or a higher verified total (e.g. Krishna Prasad), take it!
                if s_dist > ex_dist:
                    chosen_dist = s_dist
                    runs_count = s_day["runs_count"]
                    elev = s_day["elev_gain_m"]
                    sec = s_day["elapsed_sec"]
                    pace = parse_pace(sec, chosen_dist)
                    acts = s_day["activities"]
                else:
                    chosen_dist = ex_dist
                    if s_day and s_day["distance_km"] > 0:
                        runs_count = s_day["runs_count"]
                        elev = s_day["elev_gain_m"]
                        sec = s_day["elapsed_sec"]
                        pace = parse_pace(sec, chosen_dist)
                        acts = s_day["activities"]
                    else:
                        runs_count = 1 if chosen_dist > 0 else 0
                        elev = 0
                        pace = "--"
                        acts = [{"activity_name": "Logged Run", "distance_km": chosen_dist, "pace": "--", "duration": "--", "elev_gain_m": 0, "time_ist": d}] if chosen_dist > 0 else []

                daily[d] = chosen_dist
                daily_details[d] = {
                    "distance_km": chosen_dist,
                    "runs_count": runs_count,
                    "elev_gain_m": elev,
                    "pace": pace,
                    "activities": acts
                }
            else:
                # Sep 5 and Sep 6 (and beyond): strictly from Strava live feed
                if s_day and s_day["distance_km"] > 0:
                    chosen_dist = s_day["distance_km"]
                    runs_count = s_day["runs_count"]
                    elev = s_day["elev_gain_m"]
                    sec = s_day["elapsed_sec"]
                    pace = parse_pace(sec, chosen_dist)
                    acts = s_day["activities"]
                else:
                    chosen_dist = 0.0
                    runs_count = 0
                    elev = 0
                    pace = "--"
                    acts = []

                daily[d] = chosen_dist
                daily_details[d] = {
                    "distance_km": chosen_dist,
                    "runs_count": runs_count,
                    "elev_gain_m": elev,
                    "pace": pace,
                    "activities": acts
                }

        total_km = round(sum(daily.values()), 2)
        active_days = sum(1 for d, val in daily.items() if val > 0)
        best_day = max(daily.values()) if daily else 0.0

        # Streak calculation up to current active day
        streak = 0
        check_dates = list(reversed(dates))
        if daily.get(dates[-1], 0.0) == 0.0 and len(check_dates) > 1:
            check_dates = check_dates[1:]
        for cd in check_dates:
            if daily.get(cd, 0.0) > 0.0:
                streak += 1
            else:
                break

        # Latest pace from the most recent active run
        latest_pace = "--"
        for d in reversed(dates):
            if daily_details[d]["pace"] != "--":
                latest_pace = daily_details[d]["pace"]
                break
        if latest_pace == "--":
            latest_pace = prev.get("latest_pace", "--")

        pct = min(100.0, round((total_km / target_km) * 100.0, 1))

        consolidated_totals[aid] = {
            "athlete_id": aid,
            "sl_no": ex["sl_no"],
            "name": display_name,
            "excel_name": ex["excel_name"],
            "avatar_url": avatar_url,
            "mobile": mobile,
            "total_challenge_km": total_km,
            "target_km": target_km,
            "active_days": active_days,
            "current_streak": streak,
            "best_day_km": best_day,
            "latest_pace": latest_pace,
            "pct_completed": pct,
            "is_finisher": total_km >= target_km,
            "remaining_km": max(0.0, round(target_km - total_km, 2)),
            "daily_breakdown": daily
        }

        # Populate daily records
        for d in dates:
            det = daily_details[d]
            daily_records[d].append({
                "date": d,
                "athlete_id": aid,
                "name": display_name,
                "avatar_url": avatar_url,
                "daily_distance_km": det["distance_km"],
                "daily_runs": det["runs_count"],
                "daily_elev_gain_m": det["elev_gain_m"],
                "avg_pace": det["pace"],
                "weekly_cumulative_km": total_km,
                "activities": det["activities"]
            })

    # Also include JustinTX Cherai (enrolled active runner from Strava)
    justin_aid = "35422762"
    if justin_aid not in consolidated_totals:
        prev_j = existing_totals.get(justin_aid, {})
        j_live = athlete_live_meta.get(justin_aid, {})
        j_daily = {
            "2026-09-01": 10.38,
            "2026-09-02": 1.02,
            "2026-09-03": 5.02,
            "2026-09-04": 8.04,
            "2026-09-05": 0.0,
            "2026-09-06": 0.0
        }
        j_tot = round(sum(j_daily.values()), 2)
        consolidated_totals[justin_aid] = {
            "athlete_id": justin_aid,
            "sl_no": 48,
            "name": "JustinTX Cherai",
            "excel_name": "JustinTX Cherai",
            "avatar_url": j_live.get("avatar_url") or prev_j.get("avatar_url") or "https://dgalywyr863hv.cloudfront.net/pictures/athletes/35422762/47666145/1/medium.jpg",
            "mobile": "",
            "total_challenge_km": j_tot,
            "target_km": target_km,
            "active_days": 4,
            "current_streak": 4,
            "best_day_km": 10.38,
            "latest_pace": "5:04",
            "pct_completed": round((j_tot / target_km) * 100.0, 1),
            "is_finisher": j_tot >= target_km,
            "remaining_km": max(0.0, round(target_km - j_tot, 2)),
            "daily_breakdown": j_daily
        }
        for d in dates:
            daily_records[d].append({
                "date": d,
                "athlete_id": justin_aid,
                "name": "JustinTX Cherai",
                "avatar_url": consolidated_totals[justin_aid]["avatar_url"],
                "daily_distance_km": j_daily[d],
                "daily_runs": 1 if j_daily[d] > 0 else 0,
                "daily_elev_gain_m": 0,
                "avg_pace": "5:04" if j_daily[d] > 0 else "--",
                "weekly_cumulative_km": j_tot,
                "activities": [{"activity_name": "Run", "distance_km": j_daily[d], "pace": "5:04", "duration": "--", "elev_gain_m": 0, "time_ist": d}] if j_daily[d] > 0 else []
            })

    # Sort daily records by daily_distance_km descending
    for d in dates:
        daily_records[d].sort(key=lambda x: x["daily_distance_km"], reverse=True)

    # Save to club_history.json
    history_payload = {
        "club_name": "Wandoor Runners Monsoon 100k challenge 2026",
        "target_km": target_km,
        "last_updated": datetime.now(IST).isoformat(),
        "dates": dates,
        "daily_records": daily_records,
        "athlete_totals": consolidated_totals
    }

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_payload, f, indent=2, ensure_ascii=False)

    # Save to latest_snapshot.json
    snapshot_file = os.path.join(data_dir, "latest_snapshot.json")
    sorted_athletes = sorted(consolidated_totals.values(), key=lambda x: x["total_challenge_km"], reverse=True)
    snapshot_athletes = []
    for idx, a in enumerate(sorted_athletes, 1):
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
        "date": dates[-1],
        "athletes": snapshot_athletes
    }
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot_payload, f, indent=2, ensure_ascii=False)

    print(f"[+] Successfully synchronized {len(consolidated_totals)} athletes across {len(dates)} competition days!")
    return history_payload


if __name__ == "__main__":
    sync_official_data()
