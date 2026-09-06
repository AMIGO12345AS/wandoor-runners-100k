"""
Official Excel Importer & Master Synchronizer
Imports ground-truth verified records from `aseem - Copy.xlsx` for September 1 to September 4.
Synchronizes live Strava runs for September 5 (yesterday) and September 6 (today).
Ensures 100% agreement with client data, multi-run support, and complete weekly reset immunity.
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
    "ansiyamk": "athlete_ansiyamk",
    "anwerhussain": "189332219",
    "bijumon": "119864275",
    "binunaduvath": "1753145775",
    "diljithp": "193153549",
    "drshameerthodengal": "130257164",
    "drvarunvasudev": "athlete_drvarunvasudev",
    "fahisfahi": "201415432",
    "firshadpfirshadp": "198305096",
    "gamingwithrahman": "191074714",
    "khaliqkt": "190479130",
    "krishnaprasadmkp": "159419010",
    "lebeebaplebeebap": "1759530438",
    "lineeshmalangadan": "athlete_lineeshmalangadan",
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
    "shajikoodamth": "athlete_shajikoodamth",
    "subhashkv": "1909549551",
    "suneeshk": "199859556",
    "unnikrishnank": "153813910",
    "akt": "athlete_akt",
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

    # 4. Fetch live Strava activities for Sep 5 (yesterday) and Sep 6 (today)
    from scripts.feed_sync import fetch_all_club_activities
    live_activities = fetch_all_club_activities(club_id, session_cookie, since_date="2026-09-05")

    sep5_6_runs = {}
    athlete_live_meta = {}

    for a in live_activities:
        d = a["date_ist"]
        if d in ["2026-09-05", "2026-09-06"]:
            aid = str(a["athlete_id"])
            aname = clean_name(a["athlete_name"])
            avatar = a.get("avatar_url") or "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"

            athlete_live_meta[aid] = {
                "name": aname,
                "avatar_url": avatar
            }

            key = (aid, d)
            if key not in sep5_6_runs:
                sep5_6_runs[key] = {
                    "distance_km": 0.0,
                    "runs_count": 0,
                    "elev_gain_m": 0,
                    "elapsed_sec": 0,
                    "pace": a.get("pace", "--")
                }
            rec = sep5_6_runs[key]
            rec["distance_km"] = round(rec["distance_km"] + a["distance_km"], 2)
            rec["runs_count"] += 1
            rec["elev_gain_m"] += a.get("elev_gain_m", 0)
            rec["elapsed_sec"] += a.get("elapsed_sec", 0)
            if a.get("pace") and a.get("pace") != "--":
                rec["pace"] = a["pace"]

    print(f"[+] Found {len(sep5_6_runs)} aggregated runs for Sep 5 and Sep 6.")

    # 5. Build consolidated athlete database
    dates = ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06"]
    consolidated_totals = {}
    daily_records = {d: [] for d in dates}

    # Process all athletes from Excel
    for norm_n, ex in excel_athletes.items():
        # Determine athlete_id
        aid = EXPLICIT_STRAVA_MAP.get(norm_n)
        if not aid:
            # check existing history
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
        # Use cleaner Strava display name if available
        if live_m.get("name"):
            display_name = live_m["name"]
        elif prev.get("name") and prev.get("name") != ex["excel_name"]:
            display_name = prev["name"]

        avatar_url = live_m.get("avatar_url") or prev.get("avatar_url") or "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"
        mobile = prev.get("mobile", "")

        # Days 1 to 4 from Excel
        d1 = ex["d1"]
        d2 = ex["d2"]
        d3 = ex["d3"]
        d4 = ex["d4"]

        # Days 5 and 6 from Strava
        d5_data = sep5_6_runs.get((aid, "2026-09-05"))
        d5 = d5_data["distance_km"] if d5_data else 0.0

        d6_data = sep5_6_runs.get((aid, "2026-09-06"))
        d6 = d6_data["distance_km"] if d6_data else 0.0

        daily = {
            "2026-09-01": d1,
            "2026-09-02": d2,
            "2026-09-03": d3,
            "2026-09-04": d4,
            "2026-09-05": d5,
            "2026-09-06": d6
        }

        total_km = round(d1 + d2 + d3 + d4 + d5 + d6, 2)
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

        latest_pace = "--"
        if d6_data and d6_data.get("pace"):
            latest_pace = d6_data["pace"]
        elif d5_data and d5_data.get("pace"):
            latest_pace = d5_data["pace"]
        else:
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

        # Daily records
        for d in dates:
            dist = daily[d]
            runs = 1 if dist > 0 else 0
            elev = 0
            pace = "--"
            if d == "2026-09-05" and d5_data:
                runs = d5_data["runs_count"]
                elev = d5_data["elev_gain_m"]
                pace = d5_data["pace"]
            elif d == "2026-09-06" and d6_data:
                runs = d6_data["runs_count"]
                elev = d6_data["elev_gain_m"]
                pace = d6_data["pace"]
            elif dist > 0:
                # Retain previous pace/elev if available
                prev_logs = {r["athlete_id"]: r for r in existing_history.get("daily_records", {}).get(d, [])}
                if aid in prev_logs:
                    elev = prev_logs[aid].get("daily_elev_gain_m", 0)
                    pace = prev_logs[aid].get("avg_pace", "--")

            daily_records[d].append({
                "date": d,
                "athlete_id": aid,
                "name": display_name,
                "avatar_url": avatar_url,
                "daily_distance_km": dist,
                "daily_runs": runs,
                "daily_elev_gain_m": elev,
                "avg_pace": pace,
                "weekly_cumulative_km": total_km
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
                "weekly_cumulative_km": j_tot
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
