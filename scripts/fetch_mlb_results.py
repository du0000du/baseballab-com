#!/usr/bin/env python3
"""
fetch_mlb_results.py — Fetch recent MLB game results via Stats API.
Output: data/mlb/results.json  (last 3 completed games per team)
"""
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE = "https://statsapi.mlb.com/api/v1"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "mlb" / "results.json"
NOW = datetime.now(timezone.utc)
SEASON = str(NOW.year if NOW.month >= 3 else NOW.year - 1)

# Division short names for display
DIV_SHORT = {
    "American League East":    "AL East",
    "American League Central": "AL Central",
    "American League West":    "AL West",
    "National League East":    "NL East",
    "National League Central": "NL Central",
    "National League West":    "NL West",
}
LEAGUE_SHORT = {
    "American League": "AL",
    "National League": "NL",
}


def fetch(path: str, retries: int = 3) -> dict:
    url = BASE + path
    req = Request(url, headers={"User-Agent": "baseballab-data-fetcher/1.0"})
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=15) as res:
                return json.loads(res.read())
        except (HTTPError, URLError, Exception) as e:
            print(f"  WARN attempt {attempt+1}: {e}: {url}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(5)
    return {}


def main() -> None:
    # Fetch completed games from the last 20 days
    end_date = NOW.date()
    start_date = end_date - timedelta(days=20)
    print(f"Fetching schedule {start_date} → {end_date} ...")

    sched = fetch(
        f"/schedule?sportId=1&startDate={start_date}&endDate={end_date}"
        f"&gameType=R&hydrate=team,linescore"
    )

    # Build per-team game list (sorted newest first)
    team_games: dict[int, list] = {}
    for date_entry in sorted(sched.get("dates", []), key=lambda d: d["date"], reverse=True):
        game_date = date_entry["date"]
        for game in date_entry.get("games", []):
            if game.get("status", {}).get("abstractGameState") != "Final":
                continue
            away = game["teams"]["away"]
            home = game["teams"]["home"]
            a_score = away.get("score", 0)
            h_score = home.get("score", 0)
            a_winner = away.get("isWinner", False)
            h_winner = home.get("isWinner", False)

            for team, opp, my_score, opp_score, won, is_home in [
                (away["team"], home["team"], a_score, h_score, a_winner, False),
                (home["team"], away["team"], h_score, a_score, h_winner, True),
            ]:
                tid = team["id"]
                if tid not in team_games:
                    team_games[tid] = []
                if len(team_games[tid]) < 3:
                    team_games[tid].append({
                        "date": game_date,
                        "opponent": opp["name"],
                        "opponentAbbr": opp.get("abbreviation", ""),
                        "home": is_home,
                        "score": my_score,
                        "opponentScore": opp_score,
                        "result": "W" if won else ("T" if my_score == opp_score else "L"),
                    })

    # Fetch team metadata
    print("Fetching team metadata ...")
    teams_data = fetch(f"/teams?sportId=1&season={SEASON}&sportId=1")
    teams = []
    for t in teams_data.get("teams", []):
        if t.get("sport", {}).get("id") != 1:
            continue
        division_name = t.get("division", {}).get("name", "")
        league_name = t.get("league", {}).get("name", "")
        tid = t["id"]
        teams.append({
            "id": tid,
            "name": t["name"],
            "abbreviation": t.get("abbreviation", ""),
            "league": league_name,
            "leagueShort": LEAGUE_SHORT.get(league_name, league_name),
            "division": division_name,
            "divisionShort": DIV_SHORT.get(division_name, division_name),
            "recentGames": team_games.get(tid, []),
        })

    # Sort by league, division, team name
    teams.sort(key=lambda t: (t["league"], t["division"], t["name"]))

    result = {
        "fetchedAt": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season": SEASON,
        "asOfDate": str(end_date),
        "teams": teams,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with_games = sum(1 for t in teams if t["recentGames"])
    print(f"Saved {OUTPUT.name} -- {with_games}/{len(teams)} teams have recent game data")


if __name__ == "__main__":
    main()
