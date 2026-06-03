#!/usr/bin/env python3
"""
fetch_npb_results.py — Scrape recent NPB game results from npb.jp schedule pages.
Output: data/npb/results.json  (last 3 completed games per team)

URL pattern confirmed: https://npb.jp/games/{year}/schedule_{mm}.html
Completed games have href="/scores/..." and <td class="score"> cells.
Scheduled games have time (18:00) in state cell instead of scores.
"""
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE = "https://npb.jp/games"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "npb" / "results.json"
NOW = datetime.now(timezone.utc)
SEASON = str(NOW.year if NOW.month >= 3 else NOW.year - 1)

TEAMS_BY_NAME = {
    "阪神タイガース":               {"slug": "hanshin-tigers",       "league": "central", "color": "#fdef00", "accent": "#000000"},
    "横浜DeNAベイスターズ":         {"slug": "yokohama-dena",        "league": "central", "color": "#0091d2", "accent": "#ffffff"},
    "読売ジャイアンツ":             {"slug": "yomiuri-giants",       "league": "central", "color": "#f97709", "accent": "#000000"},
    "中日ドラゴンズ":               {"slug": "chunichi-dragons",     "league": "central", "color": "#002569", "accent": "#ffffff"},
    "広島東洋カープ":               {"slug": "hiroshima-carp",       "league": "central", "color": "#e60012", "accent": "#ffffff"},
    "東京ヤクルトスワローズ":       {"slug": "yakult-swallows",      "league": "central", "color": "#00913a", "accent": "#ffffff"},
    "オリックス・バファローズ":     {"slug": "orix-buffaloes",       "league": "pacific", "color": "#000019", "accent": "#b09b5b"},
    "福岡ソフトバンクホークス":     {"slug": "softbank-hawks",       "league": "pacific", "color": "#fbc600", "accent": "#000000"},
    "北海道日本ハムファイターズ":   {"slug": "nipponham-fighters",   "league": "pacific", "color": "#0a1f44", "accent": "#cdd1d4"},
    "東北楽天ゴールデンイーグルス": {"slug": "rakuten-eagles",       "league": "pacific", "color": "#860010", "accent": "#000000"},
    "埼玉西武ライオンズ":           {"slug": "seibu-lions",          "league": "pacific", "color": "#003e92", "accent": "#ffffff"},
    "千葉ロッテマリーンズ":         {"slug": "lotte-marines",        "league": "pacific", "color": "#000000", "accent": "#ffffff"},
}
# Reverse slug → name
SLUG_TO_NAME = {v["slug"]: k for k, v in TEAMS_BY_NAME.items()}

RE_GAME = re.compile(
    r'href="/scores/(\d{4})/(\d{2})(\d{2})/[^/"]+/"[^>]*class="link_block"'
    r'|class="link_block"[^>]*href="/scores/(\d{4})/(\d{2})(\d{2})/[^/"]+/"',
)
RE_BLOCK = re.compile(
    r'<a\s[^>]*href="/scores/\d{4}/\d{6}/[^/]+/"[^>]*>([\s\S]*?)</a>',
    re.DOTALL
)
RE_SCORE_ROW = re.compile(
    r'alt="([^"]+)"[\s\S]*?<td class="score">(\d+)</td>[\s\S]*?<td class="score">(\d+)</td>[\s\S]*?alt="([^"]+)"',
    re.DOTALL
)
RE_DATE_IN_HREF = re.compile(r'/scores/(\d{4})/(\d{2})(\d{2})/')


def fetch_html(url: str) -> str:
    req = Request(url, headers={
        "Accept": "text/html",
        "User-Agent": "baseballab-data-fetcher/1.0 (+https://baseballab.com)",
    })
    try:
        with urlopen(req, timeout=20) as res:
            return res.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, Exception) as e:
        print(f"  WARN {url}: {e}", file=sys.stderr)
        return ""


def parse_games(html: str) -> list[dict]:
    games = []
    # Find all completed-game <a> blocks
    for m in re.finditer(
        r'<a\s[^>]*href="(/scores/\d{4}/\d{4}/[^/"]+/)"[^>]*>([\s\S]*?)</a>',
        html, re.DOTALL
    ):
        href, block = m.group(1), m.group(2)
        dm = RE_DATE_IN_HREF.search(href)
        if not dm:
            continue
        date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"

        sm = RE_SCORE_ROW.search(block)
        if not sm:
            continue

        t1_name, s1, s2, t2_name = sm.group(1), int(sm.group(2)), int(sm.group(3)), sm.group(4)
        if t1_name not in TEAMS_BY_NAME or t2_name not in TEAMS_BY_NAME:
            continue

        r1, r2 = ("W", "L") if s1 > s2 else (("L", "W") if s1 < s2 else ("T", "T"))
        t1, t2 = TEAMS_BY_NAME[t1_name], TEAMS_BY_NAME[t2_name]

        games.append({"date": date, "slug": t1["slug"], "name": t1_name,
                       "opp": t2_name, "oppSlug": t2["slug"],
                       "home": False, "score": s1, "oppScore": s2, "result": r1})
        games.append({"date": date, "slug": t2["slug"], "name": t2_name,
                       "opp": t1_name, "oppSlug": t1["slug"],
                       "home": True, "score": s2, "oppScore": s1, "result": r2})
    return games


def main() -> None:
    all_games: list[dict] = []

    # Fetch current month + previous month
    months = []
    y, mo = NOW.year, NOW.month
    months.append((y, mo))
    if mo == 1:
        months.append((y - 1, 12))
    else:
        months.append((y, mo - 1))

    for year, month in months:
        url = f"{BASE}/{year}/schedule_{month:02d}.html"
        print(f"Fetching {url} ...")
        html = fetch_html(url)
        games = parse_games(html)
        count = len(games) // 2
        print(f"  {count} completed games")
        all_games.extend(games)

    # Sort descending by date; keep latest 3 per team
    all_games.sort(key=lambda g: g["date"], reverse=True)
    team_games: dict[str, list] = {}
    for g in all_games:
        sl = g["slug"]
        if sl not in team_games:
            team_games[sl] = []
        if len(team_games[sl]) < 3:
            team_games[sl].append({
                "date": g["date"],
                "opponent": g["opp"],
                "opponentSlug": g["oppSlug"],
                "home": g["home"],
                "score": g["score"],
                "opponentScore": g["oppScore"],
                "result": g["result"],
            })

    teams = []
    for name, meta in TEAMS_BY_NAME.items():
        slug = meta["slug"]
        teams.append({
            "slug": slug,
            "name": name,
            "league": meta["league"],
            "color": meta["color"],
            "accent": meta["accent"],
            "recentGames": team_games.get(slug, []),
        })

    result = {
        "fetchedAt": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season": SEASON,
        "asOfDate": NOW.strftime("%Y-%m-%d"),
        "teams": teams,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with_games = sum(1 for t in teams if t["recentGames"])
    print(f"Saved {OUTPUT.name} -- {with_games}/12 teams have recent game data")


if __name__ == "__main__":
    main()
