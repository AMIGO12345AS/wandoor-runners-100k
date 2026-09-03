"""
Strava Club Leaderboard Scraper
Fetches full club leaderboard using Strava's internal AJAX JSON endpoint with session cookie.
Zero external dependencies (pure standard Python).
"""

import os
import sys
import json
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def format_pace(velocity_ms):
    """Converts velocity (m/s) to pace string (min:sec /km)"""
    if not velocity_ms or velocity_ms <= 0:
        return "--"
    sec_per_km = 1000.0 / float(velocity_ms)
    minutes = int(sec_per_km // 60)
    seconds = int(sec_per_km % 60)
    return f"{minutes}:{seconds:02d}"


def fetch_club_leaderboard(club_id="2317931", session_cookie=None):
    """
    Fetches the live club leaderboard from Strava.
    Uses Strava's JSON endpoint: /clubs/{club_id}/leaderboard with XMLHttpRequest header.
    """
    url = f"https://www.strava.com/clubs/{club_id}/leaderboard"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://www.strava.com/clubs/{club_id}/leaderboard"
    }

    if session_cookie:
        session_cookie = session_cookie.strip()
        if not session_cookie.startswith("_strava4_session="):
            cookie_header = f"_strava4_session={session_cookie}"
        else:
            cookie_header = session_cookie
        headers["Cookie"] = cookie_header

    req = Request(url, headers=headers)
    athletes = []

    try:
        with urlopen(req, timeout=25) as response:
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)
            
            items = data.get("data", [])
            for item in items:
                fname = item.get("athlete_firstname", "").strip()
                lname = item.get("athlete_lastname", "").strip()
                name = f"{fname} {lname}".strip() or "Runner"
                
                dist_meters = float(item.get("distance", 0.0))
                dist_km = round(dist_meters / 1000.0, 2)
                
                longest_meters = float(item.get("best_activities_distance", 0.0))
                longest_km = round(longest_meters / 1000.0, 2)
                
                elev_m = int(round(float(item.get("elev_gain", 0.0))))
                runs = int(item.get("num_activities", 0))
                velocity = float(item.get("velocity", 0.0))
                pace = format_pace(velocity)
                
                avatar = item.get("athlete_picture_url") or "https://d3nn82uaxijpm6.cloudfront.net/sweaters/assets/large.png"
                aid = str(item.get("athlete_id") or item.get("athlete_id_str"))

                athletes.append({
                    "rank": int(item.get("rank", len(athletes) + 1)),
                    "athlete_id": aid,
                    "name": name,
                    "avatar_url": avatar,
                    "distance_km": dist_km,
                    "runs_count": runs,
                    "longest_km": longest_km,
                    "avg_pace": pace,
                    "elev_gain_m": elev_m
                })

            return athletes, raw_data

    except HTTPError as e:
        print(f"[!] HTTP Error {e.code} while fetching club {club_id}: {e.reason}")
        return [], None
    except URLError as e:
        print(f"[!] Network error while fetching club {club_id}: {e.reason}")
        return [], None
    except json.JSONDecodeError:
        print(f"[!] Warning: Did not receive valid JSON. Page might require authentication.")
        return [], None


if __name__ == "__main__":
    cookie = os.environ.get("STRAVA_SESSION_COOKIE")
    cid = sys.argv[1] if len(sys.argv) > 1 else "2317931"
    
    print(f"[*] Fetching live leaderboard for club {cid}...")
    athletes, _ = fetch_club_leaderboard(cid, cookie)
    print(f"[+] Successfully retrieved {len(athletes)} live athletes!")
    for a in athletes[:10]:
        print(f"  #{a['rank']} {a['name']}: {a['distance_km']} km ({a['runs_count']} runs, pace: {a['avg_pace']}/km, elev: {a['elev_gain_m']}m)")
