#!/usr/bin/env python3
"""
MLB Stats API データ取得スクリプト
TASK-003: 接続テスト / TASK-004: 選手データ取得 / TASK-005: チームデータ取得
シーズン判定: 3月〜12月は当年、1〜2月は前年（オフシーズン）。MLB_SEASON env varで上書き可

使用方法:
  python3 scripts/fetch_mlb.py --mode test        # 接続テスト
  python3 scripts/fetch_mlb.py --mode players     # 選手JSONを取得
  python3 scripts/fetch_mlb.py --mode teams       # チームJSONを取得
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_URL = "https://statsapi.mlb.com/api/v1"
DATA_DIR = Path(__file__).parent.parent / "data" / "mlb"
# シーズン判定: 3月以降は当年、1〜2月はオフシーズン扱いで前年。MLB_SEASON env varで明示上書き可
SEASON = int(__import__("os").environ.get("MLB_SEASON") or (datetime.now().year if datetime.now().month >= 3 else datetime.now().year - 1))
# 取得対象選手ID（MLB主要選手）
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


def fetch_player_stats(pid: int, position_type: str = "") -> list:
    """
    選手の2024年成績を取得。
    TWP（二刀流）の場合は打撃・投球それぞれを試みる。
    position_type: "P" で投手優先、"TWP" で打撃+投球両方取得
    """
    # まず group=hitting を試す
    if position_type != "P":
        data = fetch(f"/people/{pid}/stats?stats=season&season={SEASON}&group=hitting")
        hitting = data.get("stats", [])
        if hitting and hitting[0].get("splits"):
            if position_type == "TWP":
                # 二刀流: 投球成績ア取得して追加
                data2 = fetch(f"/people/{pid}/stats?stats=season&season={SEASON}&group=pitching")
                pitching = data2.get("stats", [])
                if pitching and pitching[0].get("splits"):
                    return hitting + pitching
         return hitting

    # 投手 or 打撃データなし → 投球成績を試す
    data = fetch(f"/people/{pid}/stats?stats=season&season={SEASON}&group=pitching")
    pitching = data.get("stats", [])
    if pitching and pitching[0].get("splits"):
        return pitching

    # フォールバック: groupなしで試す
    data = fetch(f"/people/{pid}/stats?stats=season&season={SEASON}")
    return data.get("stats", [])


def test_connection():
    """TASK-003: 接続テスト"""
    print("=== MLB Stats API 接続テスト ===")

    # 選手情報テスト（Aaron Judge）
    data = fetch("/people/592450")
    if not data.get("people"):
        print("❌ 選手情報取得失敗")
        return False
    p = data["people"][0]
    print(f"✅ 選手情報: {p['fullName']} ({p['primaryPosition']['name']})")

    # 選手成績テスト（hitting）
    stats = fetch_player_stats(592450, "RF")
    if stats and stats[0].get("splits"):
        s = stats[0]["splits"][0]["stat"]
        group = stats[0]["group"]["displayName"]
        print(f"✅ {group}成績: AVG={s.get('avg','N/A')} HR={s.get('homeRuns','N/A')} RBI={s.get('rbi','N/A')}")
    else:
        print("⚠ 成績データなし")

    # チーム一覧テスト
    data = fetch(f"/teams?sportId=1&season={SEASON}")
    teams = data.get("teams", [])
    print(f"✅ チーム一覧: {len(teams)}チーム取得")

    print("\n✅ 全テスト成功")
    return True


def fetch_players():
    """TASK-004: 選手JSONをdata/mlb/players/に保存（TASK-036対応版）"""
    out_dir = DATA_DIR / "players"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== 選手データ取得 ({len(PLAYER_IDS)}名) ===")

    for pid in PLAYER_IDS:
        info = fetch(f"/people/{pid}")
        if not info.get("people"):
            print(f"  skip: {pid}")
            continue

        p = info["people"][0]
        pos_abbr = p.get("primaryPosition", {}).get("abbreviation", "")
        stats = fetch_player_stats(pid, pos_abbr)

        slug = p["fullName"].lower().replace(" ", "-").replace(".", "")
        result = {"info": p, "stats": stats, "season": SEASON}
        out_path = out_dir / f"{slug}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        # 成績サマリーを表示
        if stats and stats[0].get("splits"):
            s = stats[0]["splits"][0]["stat"]
            grp = stats[0]["group"]["displayName"]
            if grp == "hitting":
                summary = f"AVG={s.get('avg','?')} HR={s.get('homeRuns','?')} RBI={s.get('rbi','?')}"
            else:
                summary = f"ERA={s.get('era','?')} W={s.get('wins','?')} K={s.get('strikeOuts','?')}"
            print(f"  ✅ {p['fullName']} ({pos_abbr}) {summary}")
        else:
            print(f"  ⚠ {p['fullName']} ({pos_abbr}) 成績なし")

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
