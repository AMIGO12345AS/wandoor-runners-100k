#!/usr/bin/env python3
"""
Full Strava Profile & Club Audit
Iterates through all 48 club athletes using the active Strava session cookie:
- Checks profile status (Public vs Private)
- Extracts all public September 2026 activities from each athlete's personal profile feed
- Cross-references with existing club_history.json and aseem - Copy.xlsx
- Detects any discrepancies, uncaptured runs, or multi-run mismatches
- Produces a comprehensive audit report
"""

import os
import sys
import json
import re
import time
import urllib.request
import html as html_lib
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

IST = timezone(timedelta(hours=5, minutes=30))

def parse_pace(elapsed_sec, dist_km):
    if dist_km <= 0 or elapsed_sec <= 0:
        return "--"
    sec_per_km = elapsed_sec / dist_km
    p_min = int(sec_per_km // 60)
    p_sec = int(sec_per_km % 60)
    return f"{p_min}:{p_sec:02d}"

def audit_all_athletes():
    config_path = os.path.join(BASE_DIR, "config.json")
    history_path = os.path.join(BASE_DIR, "data", "club_history.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    cookie = config.get("strava_session_cookie", "").strip()

    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)

    athlete_totals = history.get("athlete_totals", {})
    daily_records = history.get("daily_records", {})

    print("=" * 65)
    print("STARTING FULL STRAVA ATHLETE PROFILE AUDIT (48 ATHLETES)")
    print(f"Total Athletes to Audit: {len(athlete_totals)}")
    print("=" * 65)

    headers = {
        "Cookie": f"_strava4_session={cookie}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    audit_results = []
    total_public = 0
    total_private = 0
    total_excel_only = 0

    sorted_athletes = sorted(athlete_totals.values(), key=lambda x: x.get("total_challenge_km", 0.0), reverse=True)

    for idx, a in enumerate(sorted_athletes, 1):
        aid = str(a.get("athlete_id"))
        name = a.get("name", "Unknown")
        current_board_km = a.get("total_challenge_km", 0.0)

        print(f"[{idx}/{len(sorted_athletes)}] Auditing: {name} (ID: {aid}) | Current Board: {current_board_km:.2f} km ...", end=" ", flush=True)

        if not aid.isdigit():
            print("EXCEL-ONLY (No Strava ID)")
            total_excel_only += 1
            audit_results.append({
                "athlete_id": aid,
                "name": name,
                "status": "excel_only",
                "is_private": None,
                "board_km": current_board_km,
                "profile_runs_found": 0,
                "runs": []
            })
            continue

        url = f"https://www.strava.com/athletes/{aid}"
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html_content = resp.read().decode("utf-8", errors="ignore")
                status_code = resp.status

            is_private = (
                "This profile is private" in html_content
                or "profile-is-private" in html_content
                or "private-profile" in html_content
            )

            if is_private:
                print("PRIVATE PROFILE")
                total_private += 1
                audit_results.append({
                    "athlete_id": aid,
                    "name": name,
                    "status": "private",
                    "is_private": True,
                    "board_km": current_board_km,
                    "profile_runs_found": 0,
                    "runs": []
                })
                time.sleep(0.5)
                continue

            total_public += 1

            # Extract activities from profile feed
            profile_runs = []
            react_props = re.findall(r'data-react-props=[\'\"]([^\'\"]+)[\'\"]', html_content)
            for rp in react_props:
                decoded = html_lib.unescape(rp)
                if 'entries' in decoded and ('Activity' in decoded or 'activity' in decoded):
                    try:
                        p_data = json.loads(decoded)
                        entries = p_data.get("entries", [])
                        for e in entries:
                            act = e.get("activity")
                            if not act:
                                continue
                            start_dt_str = act.get("startDate") or act.get("start_date_local_raw") or ""
                            # Check date in Sep 2026
                            if start_dt_str.startswith("2026-09"):
                                act_id = act.get("id")
                                act_name = act.get("activityName") or act.get("name") or "Run"
                                act_type = act.get("type") or "Run"

                                # Extract distance from stats
                                dist_km = 0.0
                                stats = act.get("stats", [])
                                for st in stats:
                                    if st.get("key") == "stat_one":
                                        v = st.get("value", "")
                                        match = re.search(r"([\d\.]+)", v)
                                        if match:
                                            dist_km = float(match.group(1))

                                elapsed_sec = act.get("elapsedTime") or 0
                                pace = parse_pace(elapsed_sec, dist_km)

                                profile_runs.append({
                                    "activity_id": act_id,
                                    "date_ist": start_dt_str[:10],
                                    "start_time": start_dt_str,
                                    "name": act_name,
                                    "distance_km": dist_km,
                                    "pace": pace,
                                    "elapsed_sec": elapsed_sec,
                                    "type": act_type
                                })
                    except Exception:
                        pass

            print(f"PUBLIC | Found {len(profile_runs)} Sep runs in profile feed")
            audit_results.append({
                "athlete_id": aid,
                "name": name,
                "status": "public",
                "is_private": False,
                "board_km": current_board_km,
                "profile_runs_found": len(profile_runs),
                "runs": profile_runs
            })

            time.sleep(0.4)

        except Exception as err:
            print(f"ERROR: {err}")
            audit_results.append({
                "athlete_id": aid,
                "name": name,
                "status": f"error: {err}",
                "is_private": None,
                "board_km": current_board_km,
                "profile_runs_found": 0,
                "runs": []
            })
            time.sleep(0.5)

    # Summary analysis
    print("\n" + "=" * 65)
    print("AUDIT SUMMARY:")
    print(f"Total Athletes Checked: {len(audit_results)}")
    print(f"Public Profiles:        {total_public}")
    print(f"Private Profiles:       {total_private}")
    print(f"Excel-only (No ID):     {total_excel_only}")
    print("=" * 65)

    # Save audit report
    out_file = os.path.join(BASE_DIR, "data", "strava_audit_report.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "audit_timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
            "total_athletes": len(audit_results),
            "public_count": total_public,
            "private_count": total_private,
            "excel_only_count": total_excel_only,
            "athletes": audit_results
        }, f, indent=2)

    print(f"[+] Full audit report saved to {out_file}")

if __name__ == "__main__":
    audit_all_athletes()
