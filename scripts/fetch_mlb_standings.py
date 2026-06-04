#!/usr/bin/env python3
"""
fetch_mlb_standings.py -- Fetch MLB team standings from Stats API.
Computes Pythagorean win% (RS^1.83 / (RS^1.83 + RA^1.83)) and luck delta.
Output: data/mlb/standings.json
"""
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "https://statsapi.mlb.com/api/v1"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "mlb" / "standings.json"
NOW = datetime.now(timezone.utc)
SEASON = str(NOW.year if NOW.month >= 3 else NOW.year - 1)
EXP = 1.83  # Pythagenport exponent (Smyth, Baseball Reference)

# MLB Stats API returns league/division as {id, link} — name field is empty.
# Map IDs directly.
LEAGUE_ID_MAP = {
    103: ("American League", "AL"),
    104: ("National League", "NL"),
}
DIV_ID_MAP = {
    200: ("American League West",    "AL West"),
    201: ("American League East",    "AL East"),
    202: ("American League Central", "AL Central"),
    203: ("National League West",    "NL West"),
    204: ("National League East",    "NL East"),
    205: ("National League Central", "NL Central"),
}


def fetch(path: str, retries: int = 3) -> dict:
    url = BASE + path
    req = Request(url, headers={"User-Agent": "baseballab-data-fetcher/1.0"})
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=15) as res:
                return json.loads(res.read())
        except (HTTPError, URLError, Exception) as e:
            print(f"  WARN attempt {attempt+1}: {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(5)
    return {}


def pythagorean(rs: int, ra: int) -> float:
    if rs == 0 and ra == 0:
        return 0.5
    rs_e = rs ** EXP
    ra_e = ra ** EXP
    return round(rs_e / (rs_e + ra_e), 4)


def main() -> None:
    print(f"Fetching MLB standings {SEASON} ...")
    raw = fetch(f"/standings?leagueId=103,104&season={SEASON}&hydrate=team")

    teams = []
    for record in raw.get("records", []):
        lg_id = record.get("league", {}).get("id", 0)
        div_id = record.get("division", {}).get("id", 0)
        lg_name, lg_short = LEAGUE_ID_MAP.get(lg_id, ("", ""))
        div_name, div_short = DIV_ID_MAP.get(div_id, ("", ""))

        for tr in record.get("teamRecords", []):
            team = tr.get("team", {})
            w = tr.get("wins", 0)
            l = tr.get("losses", 0)
            rs = tr.get("runsScored", 0)
            ra = tr.get("runsAllowed", 0)
            games = w + l
            gp = tr.get("gamesPlayed", games)
            gb = tr.get("gamesBack", "-")
            actual_pct = round(w / games, 4) if games > 0 else 0.0
            pyth_pct = pythagorean(rs, ra)
            luck_delta = round(actual_pct - pyth_pct, 4)

            teams.append({
                "id": team.get("id"),
                "name": team.get("name", ""),
                "abbreviation": team.get("abbreviation", ""),
                "league": lg_name,
                "leagueShort": lg_short,
                "division": div_name,
                "divisionShort": div_short,
                "wins": w,
                "losses": l,
                "games": games,
                "gamesPlayed": gp,
                "gamesBack": gb,
                "winPct": actual_pct,
                "runsScored": rs,
                "runsAllowed": ra,
                "runDiff": rs - ra,
                "pythWinPct": pyth_pct,
                "luckDelta": luck_delta,
            })

    teams.sort(key=lambda t: (t["league"], t["division"], -t["winPct"]))

    result = {
        "fetchedAt": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season": SEASON,
        "teams": teams,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {OUTPUT.name} -- {len(teams)} teams")


if __name__ == "__main__":
    main()
