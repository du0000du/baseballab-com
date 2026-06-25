#!/usr/bin/env python3
"""
fetch_mlb_japanese.py — Fetch MLB stats for active Japanese players.
Output: data/mlb/japanese.json

Season stats update same-day via MLB Stats API.
Game log gives today's/most-recent game result.
"""
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE = "https://statsapi.mlb.com/api/v1"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "mlb" / "japanese.json"
NOW = datetime.now(timezone.utc)
SEASON = str(NOW.year if NOW.month >= 3 else NOW.year - 1)

JP_PLAYERS = [
    {"id": 660271, "ja": "大谷翔平",         "pos_type": "TWP"},
    {"id": 808967, "ja": "山本由伸",         "pos_type": "P"},
    {"id": 808963, "ja": "佐々木朗希",       "pos_type": "P"},
    {"id": 673548, "ja": "鈴木誠也",         "pos_type": "OF"},
    {"id": 684007, "ja": "今永昇太",         "pos_type": "P"},
    {"id": 673540, "ja": "千賀滉大",         "pos_type": "P"},
    {"id": 663457, "ja": "ラーズ・ヌートバー", "pos_type": "OF"},
    {"id": 608372, "ja": "菅野智之",         "pos_type": "P"},
    {"id": 506433, "ja": "ダルビッシュ有",   "pos_type": "P"},
    {"id": 673513, "ja": "松井裕樹",         "pos_type": "P"},
    {"id": 808959, "ja": "村上宗隆",         "pos_type": "IF"},
    {"id": 672960, "ja": "岡本和真",         "pos_type": "IF"},
    {"id": 837227, "ja": "今井達也",         "pos_type": "P"},
    {"id": 579328, "ja": "菊池雄星",         "pos_type": "P"},
    {"id": 807799, "ja": "吉田正尚",         "pos_type": "OF"},
]


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
                time.sleep(3)
    return {}


def fetch_season_stats(pid: int, group: str) -> dict:
    """Returns stat dict for the season, or empty dict."""
    d = fetch(f"/people/{pid}/stats?stats=season&season={SEASON}&group={group}")
    for s in d.get("stats", []):
        splits = s.get("splits", [])
        if splits:
            return splits[0].get("stat", {})
    return {}


def fetch_last_game(pid: int, group: str) -> dict | None:
    """Returns the most recent game log entry, or None."""
    d = fetch(f"/people/{pid}/stats?stats=gameLog&season={SEASON}&group={group}")
    for s in d.get("stats", []):
        splits = s.get("splits", [])
        if splits:
            last = splits[-1]  # gameLog is oldest-first; last = most recent
            return {
                "date": last.get("date", ""),
                "opponent": last.get("opponent", {}).get("name", ""),
                "isHome": last.get("isHome", False),
                "stat": last.get("stat", {}),
            }
    return None


def build_player(meta: dict) -> dict:
    pid = meta["id"]
    pos_type = meta["pos_type"]

    # Player info
    info_data = fetch(f"/people/{pid}?hydrate=currentTeam")
    info = (info_data.get("people") or [{}])[0]
    name_en = info.get("fullName", "")
    team = info.get("currentTeam", {}).get("name", "")
    team_abbr = info.get("currentTeam", {}).get("abbreviation", "")
    pos = info.get("primaryPosition", {}).get("abbreviation", "")
    active = info.get("active", False)

    result: dict = {
        "id": pid,
        "ja": meta["ja"],
        "en": name_en,
        "team": team,
        "teamAbbr": team_abbr,
        "position": pos,
        "posType": pos_type,
        "active": active,
        "season": {},
        "lastGame": None,
    }

    if pos_type == "TWP":
        # 大谷: both hitting and pitching
        hit = fetch_season_stats(pid, "hitting")
        pit = fetch_season_stats(pid, "pitching")
        result["season"] = {"hitting": hit, "pitching": pit}
        result["lastGame"] = fetch_last_game(pid, "hitting")
    elif pos_type == "P":
        pit = fetch_season_stats(pid, "pitching")
        result["season"] = {"pitching": pit}
        result["lastGame"] = fetch_last_game(pid, "pitching")
    else:
        hit = fetch_season_stats(pid, "hitting")
        result["season"] = {"hitting": hit}
        result["lastGame"] = fetch_last_game(pid, "hitting")

    return result


def main() -> None:
    players = []
    for meta in JP_PLAYERS:
        print(f"Fetching {meta['ja']} ({meta['id']}) ...")
        p = build_player(meta)
        players.append(p)
        print(f"  {p['en']} / {p['team']} / active={p['active']}")
        time.sleep(0.5)

    output = {
        "fetchedAt": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season": SEASON,
        "asOfDate": str(NOW.date()),
        "players": players,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {OUTPUT} ({len(players)} players)")


if __name__ == "__main__":
    main()
