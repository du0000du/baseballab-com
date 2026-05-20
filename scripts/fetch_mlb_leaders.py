#!/usr/bin/env python3
"""
fetch_mlb_leaders.py
MLB シーズン成績リーダーボードデータを取得してJSONに保存する

プロジェクトルール: SEASON = 現在の年 - 1 (直前シーズン)
例: 2026年実行 → 2025シーズンデータを取得

使い方:
  python scripts/fetch_mlb_leaders.py

出力先:
  data/mlb/leaders/{SEASON}.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# プロジェクトルール: 現在の年 - 1 = 直前シーズン
SEASON = str(datetime.now().year - 1)
BASE = "https://statsapi.mlb.com/api/v1"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "mlb", "leaders")


def fetch(path: str) -> dict:
    url = f"{BASE}{path}"
    req = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "baseballab-fetcher/1.0",
        },
    )
    try:
        with urlopen(req, timeout=10) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as e:
        print(f"  HTTP {e.code}: {url}", file=sys.stderr)
        return {}
    except URLError as e:
        print(f"  URLError: {e.reason}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  ERROR: {e}", file=sys.stderr)
        return {}


def get_leaders(group: str, sort_stat: str, limit: int = 10) -> list:
    path = (
        f"/stats"
        f"?stats=season"
        f"&season={SEASON}"
        f"&group={group}"
        f"&sortStat={sort_stat}"
        f"&limit={limit}"
        f"&gameType=R"
        f"&hydrate=person,team"
    )
    data = fetch(path)
    if not data.get("stats"):
        return []

    splits = data["stats"][0].get("splits", [])
    result = []
    for i, item in enumerate(splits):
        stat = item.get("stat", {})
        player = item.get("player", {})
        team = item.get("team", {})

        value = stat.get(sort_stat)
        if value is None:
            value = stat.get(sort_stat[0].lower() + sort_stat[1:], "")

        result.append(
            {
                "rank": item.get("rank", i + 1),
                "playerId": player.get("id"),
                "player": player.get("fullName", ""),
                "team": team.get("abbreviation", team.get("teamName", "")),
                "value": value if value is not None else "",
            }
        )
    return result


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"=== MLB {SEASON} リーダーボードデータ取得 ===")

    batting_defs = [
        ("homeRuns",    "ホームラン"),
        ("avg",         "打率"),
        ("rbi",         "打点"),
        ("stolenBases", "盗塁"),
    ]
    pitching_defs = [
        ("era",          "防御率"),
        ("wins",         "勝利"),
        ("strikeOuts",   "奪三振"),
        ("saves",        "セーブ"),
    ]

    batting = {}
    for stat_key, label in batting_defs:
        print(f"  打撃/{label} ({stat_key})...")
        batting[stat_key] = get_leaders("hitting", stat_key)
        print(f"    {len(batting[stat_key])} 件取得")
        time.sleep(0.4)

    pitching = {}
    for stat_key, label in pitching_defs:
        print(f"  投球/{label} ({stat_key})...")
        pitching[stat_key] = get_leaders("pitching", stat_key)
        print(f"    {len(pitching[stat_key])} 件取得")
        time.sleep(0.4)

    output = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season": SEASON,
        "batting": batting,
        "pitching": pitching,
    }

    out_path = os.path.join(OUTPUT_DIR, f"{SEASON}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 保存完了: {out_path}")

    print("\n--- サマリー ---")
    hr_top = batting.get("homeRuns", [{}])
    if hr_top:
        top = hr_top[0]
        print(f"HR 1位: {top.get('player')} ({top.get('team')}) {top.get('value')}本")
    era_top = pitching.get("era", [{}])
    if era_top:
        top = era_top[0]
        print(f"ERA 1位: {top.get('player')} ({top.get('team')}) {top.get('value')}")


if __name__ == "__main__":
    main()
