#!/usr/bin/env python3
"""
MLB Stats API データ取得スクリプト
TASK-003: 接続テスト / TASK-004: 選手データ取得 / TASK-005: チームデータ取得

使用方法:
  python3 scripts/fetch_mlb.py --mode test        # 接続テスト
  python3 scripts/fetch_mlb.py --mode players     # 選手50名のJSONを取得
  python3 scripts/fetch_mlb.py --mode teams       # チーム30チームのJSONを取得
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "https://statsapi.mlb.com/api/v1"
DATA_DIR = Path(__file__).parent.parent / "data" / "mlb"
SEASON = 2024

# 取得対象選手ID（MLB主要選手50名）
# 大谷翔平=660271, ムーキー・ベッツ=605141 など
PLAYER_IDS = [
    660271,  # 大谷翔平
    605141,  # Mookie Betts
    592518,  # Freddie Freeman
    682998,  # Yoshinobu Yamamoto
    668939,  # Juan Soto
    665742,  # Fernando Tatis Jr.
    641355,  # Julio Rodriguez
    666023,  # Elly De La Cruz
    683737,  # Jackson Merrill
    686469,  # Gunnar Henderson
    671096,  # Bobby Witt Jr.
    663728,  # Jeremy Pena
    694973,  # Corbin Carroll
    595978,  # Bryce Harper
    621566,  # Trea Turner
    543760,  # Nolan Arenado
    642133,  # Rafael Devers
    596019,  # Jose Ramirez
    514888,  # Miguel Cabrera
    477132,  # Albert Pujols
    592450,  # Gerrit Cole
    656302,  # Spencer Strider
    669923,  # Shane McClanahan
    677951,  # Logan Webb
    641154,  # Tyler Glasnow
    663158,  # Pablo Lopez
    676979,  # Zack Wheeler
    608566,  # Brandon Woodruff
    554430,  # Clayton Kershaw
    592332,  # Max Scherzer
]


def fetch(path: str) -> dict:
    """MLB Stats APIにリクエストを送る"""
    url = BASE_URL + path
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "baseballab-data-fetcher/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {url}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  Error: {e}: {url}", file=sys.stderr)
        return {}


def test_connection():
    """TASK-003: 接続テスト"""
    print("=== MLB Stats API 接続テスト ===")

    # 選手情報テスト（大谷翔平）
    data = fetch("/people/660271")
    if not data.get("people"):
        print("❌ 選手情報取得失敗")
        return False
    p = data["people"][0]
    print(f"✅ 選手情報: {p['fullName']} ({p['primaryPosition']['name']} #{p['primaryNumber']})")

    # 選手成績テスト
    data = fetch(f"/people/660271/stats?stats=season&season={SEASON}")
    stats_list = data.get("stats", [])
    if stats_list and stats_list[0].get("splits"):
        s = stats_list[0]["splits"][0]["stat"]
        print(f"✅ 打撃成績: AVG={s.get('avg','N/A')} HR={s.get('homeRuns','N/A')} RBI={s.get('rbi','N/A')}")

    # チーム一覧テスト
    data = fetch(f"/teams?sportId=1&season={SEASON}")
    teams = data.get("teams", [])
    print(f"✅ チーム一覧: {len(teams)}チーム取得")
    for t in teams[:3]:
        print(f"   - {t['name']} ({t['abbreviation']})")

    print("\n✅ 全テスト成功")
    return True


def fetch_players():
    """TASK-004: 選手JSONをdata/mlb/players/に保存"""
    out_dir = DATA_DIR / "players"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== 選手データ取得 ({len(PLAYER_IDS)}名) ===")

    for pid in PLAYER_IDS:
        info = fetch(f"/people/{pid}")
        stats = fetch(f"/people/{pid}/stats?stats=season&season={SEASON}")
        if not info.get("people"):
            print(f"  skip: {pid}")
            continue

        p = info["people"][0]
        slug = p["fullName"].lower().replace(" ", "-").replace(".", "")
        result = {"info": p, "stats": stats.get("stats", []), "season": SEASON}
        out_path = out_dir / f"{slug}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"  ✅ {p['fullName']} → {out_path.name}")
        time.sleep(0.3)  # レートリミット対策

    print(f"\n保存先: {out_dir}")


def fetch_teams():
    """TASK-005: チームJSONをdata/mlb/teams/に保存"""
    out_dir = DATA_DIR / "teams"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== チームデータ取得 ===")

    data = fetch(f"/teams?sportId=1&season={SEASON}")
    teams = data.get("teams", [])
    print(f"{len(teams)}チーム取得")

    for t in teams:
        team_id = t["id"]
        slug = t["name"].lower().replace(" ", "-")
        stats_data = fetch(f"/teams/{team_id}/stats?stats=season&season={SEASON}")
        result = {"info": t, "stats": stats_data.get("stats", []), "season": SEASON}
        out_path = out_dir / f"{slug}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"  ✅ {t['name']} ({t['abbreviation']}) → {out_path.name}")
        time.sleep(0.2)

    print(f"\n保存先: {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLB Stats API データ取得")
    parser.add_argument("--mode", choices=["test", "players", "teams", "all"],
                        default="test", help="実行モード")
    args = parser.parse_args()

    if args.mode == "test":
        test_connection()
    elif args.mode == "players":
        fetch_players()
    elif args.mode == "teams":
        fetch_teams()
    elif args.mode == "all":
        test_connection()
        fetch_players()
        fetch_teams()
