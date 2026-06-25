#!/usr/bin/env python3
"""
fetch_npb_results.py — Scrape recent NPB game results from npb.jp schedule pages.
Output: data/npb/results.json  (last 3 completed games per team)
        data/npb/standings.json (adds estimatedAsOf / estimatedCentral / estimatedPacific)

URL pattern confirmed: https://npb.jp/games/{year}/schedule_{mm}.html
Main games page:       https://npb.jp/games/{year}/
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
META = Path(__file__).resolve().parent.parent / "data" / "npb" / "meta.json"
STANDINGS = Path(__file__).resolve().parent.parent / "data" / "npb" / "standings.json"
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
SLUG_TO_NAME = {v["slug"]: k for k, v in TEAMS_BY_NAME.items()}

STADIUMS: dict[str, str] = {
    "hanshin-tigers":     "阪神甲子園球場",
    "yokohama-dena":      "横浜スタジアム",
    "yomiuri-giants":     "東京ドーム",
    "chunichi-dragons":   "バンテリンドームナゴヤ",
    "hiroshima-carp":     "MAZDA Zoom-Zoomスタジアム広島",
    "yakult-swallows":    "明治神宮野球場",
    "orix-buffaloes":     "京セラドームOSAKA",
    "softbank-hawks":     "みずほPayPayドーム福岡",
    "nipponham-fighters": "エスコンフィールドHOKKAIDO",
    "rakuten-eagles":     "楽天モバイルパーク宮城",
    "seibu-lions":        "ベルーナドーム",
    "lotte-marines":      "ZOZOマリンスタジアム",
}

# npb.jp/games/{year}/MMDD/CODE URL team code → slug
URL_CODE_TO_SLUG: dict[str, str] = {
    "t":  "hanshin-tigers",
    "db": "yokohama-dena",
    "g":  "yomiuri-giants",
    "d":  "chunichi-dragons",
    "c":  "hiroshima-carp",
    "s":  "yakult-swallows",
    "b":  "orix-buffaloes",
    "h":  "softbank-hawks",
    "f":  "nipponham-fighters",
    "e":  "rakuten-eagles",
    "l":  "seibu-lions",
    "m":  "lotte-marines",
}

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


def parse_games_monthly(html: str) -> list[dict]:
    """Parse completed games from monthly schedule page (home/away is reliable here)."""
    games = []
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
        stadium = STADIUMS.get(t2["slug"], "")  # t2 is always home team

        games.append({"date": date, "slug": t1["slug"], "opp": t2_name, "oppSlug": t2["slug"],
                       "home": False, "score": s1, "oppScore": s2, "result": r1, "stadium": stadium})
        games.append({"date": date, "slug": t2["slug"], "opp": t1_name, "oppSlug": t1["slug"],
                       "home": True,  "score": s2, "oppScore": s1, "result": r2, "stadium": stadium})
    return games


def fetch_latest_from_main_page() -> list[dict]:
    """
    Fetch completed games from https://npb.jp/games/{SEASON}/
    Returns one record per physical game: {date, t1, s1, t2, s2}
    t1 is the first team in URL (home in NPB's games page convention).
    """
    url = f"{BASE}/{SEASON}/"
    print(f"Fetching {url} (latest games for standings estimate) ...")
    html = fetch_html(url)
    if not html:
        return []

    DATE_PAT = re.compile(r'<div class="score_box date"><div>(\d{4})<br>(\d+)/(\d+)')
    GAME_PAT = re.compile(
        r'<a href="/scores/\d+/(\d{2})(\d{2})/([^/]+)/">'
        r'[\s\S]*?<div class="score">([^<]+)</div>',
        re.DOTALL,
    )

    date_matches = list(DATE_PAT.finditer(html))
    games: list[dict] = []

    for di, dm in enumerate(date_matches):
        y, mo, day = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        date_str = f"{y:04d}-{mo:02d}-{day:02d}"

        start = dm.end()
        end = date_matches[di + 1].start() if di + 1 < len(date_matches) else len(html)
        section = html[start:end]

        for gm in GAME_PAT.finditer(section):
            mm, dd, code, score = gm.group(1), gm.group(2), gm.group(3), gm.group(4).strip()
            sm = re.match(r"^(\d+)-(\d+)$", score)
            if not sm:
                continue

            s1, s2 = int(sm.group(1)), int(sm.group(2))

            # URL code "TEAM1-TEAM2-NN" → last segment is game number
            parts = code.split("-")
            if len(parts) < 3 or not parts[-1].isdigit():
                continue
            t1_code = parts[0]
            t2_code = "-".join(parts[1:-1])

            t1 = URL_CODE_TO_SLUG.get(t1_code)
            t2 = URL_CODE_TO_SLUG.get(t2_code)
            if not t1 or not t2:
                continue

            games.append({"date": date_str, "t1": t1, "s1": s1, "t2": t2, "s2": s2})

    print(f"  {len(games)} completed games from main page")
    return games


def update_standings_estimate(monthly_games: list[dict], latest_games: list[dict]) -> None:
    """Apply new-game results to official standings; write estimatedAsOf/Central/Pacific."""
    if not META.exists() or not STANDINGS.exists():
        print("  Skipping estimate: meta.json or standings.json not found")
        return

    meta = json.loads(META.read_text(encoding="utf-8"))
    official_as_of: str = meta.get("asOf", "")
    if not official_as_of:
        print("  Skipping estimate: no asOf in meta.json")
        return

    official = json.loads(STANDINGS.read_text(encoding="utf-8"))

    # Build canonical unique-game set from monthly pages
    unique: dict[tuple, dict] = {}
    for g in monthly_games:
        key = (g["date"], min(g["slug"], g["oppSlug"]), max(g["slug"], g["oppSlug"]))
        if key not in unique:
            unique[key] = {"date": g["date"], "t1": g["slug"], "s1": g["score"],
                           "t2": g["oppSlug"], "s2": g["oppScore"]}

    # Merge games from main page (may have games newer than monthly pages)
    for g in latest_games:
        key = (g["date"], min(g["t1"], g["t2"]), max(g["t1"], g["t2"]))
        if key not in unique:
            unique[key] = g

    new_games = sorted(
        [g for g in unique.values() if g["date"] > official_as_of],
        key=lambda g: g["date"],
    )
    if not new_games:
        print(f"  No games after {official_as_of} — standings estimate unchanged")
        # Remove stale estimate if official caught up
        if "estimatedAsOf" in official:
            del official["estimatedAsOf"]
            del official["estimatedCentral"]
            del official["estimatedPacific"]
            STANDINGS.write_text(json.dumps(official, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    estimated_as_of = new_games[-1]["date"]
    print(f"  Applying {len(new_games)} games: {official_as_of} → {estimated_as_of}")

    # Mutable standings keyed by slug
    team_rec: dict[str, dict] = {}
    for league in ("central", "pacific"):
        for rec in official.get(league, []):
            slug = rec["teamSlug"]
            team_rec[slug] = {k: rec[k] for k in rec}
            team_rec[slug]["league"] = league

    for g in new_games:
        t1, s1, t2, s2 = g["t1"], g["s1"], g["t2"], g["s2"]
        if t1 not in team_rec or t2 not in team_rec:
            continue
        if s1 > s2:
            team_rec[t1]["wins"]   += 1; team_rec[t2]["losses"] += 1
        elif s2 > s1:
            team_rec[t2]["wins"]   += 1; team_rec[t1]["losses"] += 1
        else:
            team_rec[t1]["ties"]   += 1; team_rec[t2]["ties"]   += 1
        team_rec[t1]["games"] += 1; team_rec[t2]["games"] += 1

    def sort_and_rank(recs: list[dict]) -> list[dict]:
        for r in recs:
            wl = r["wins"] + r["losses"]
            r["pct"] = f".{int(r['wins'] / wl * 1000):03d}" if wl > 0 else ".000"
        recs.sort(key=lambda r: -(r["wins"] / (r["wins"] + r["losses"])) if (r["wins"] + r["losses"]) > 0 else 0)
        leader_w = recs[0]["wins"] if recs else 0
        leader_l = recs[0]["losses"] if recs else 0
        for i, r in enumerate(recs):
            r["rank"] = i + 1
            if i == 0:
                r["gb"] = "--"
            else:
                gb = ((leader_w - r["wins"]) + (r["losses"] - leader_l)) / 2
                r["gb"] = str(int(gb)) if gb == int(gb) else f"{gb:.1f}"
        return recs

    est_central = sort_and_rank([r for r in team_rec.values() if r["league"] == "central"])
    est_pacific = sort_and_rank([r for r in team_rec.values() if r["league"] == "pacific"])

    official["estimatedAsOf"]     = estimated_as_of
    official["estimatedCentral"]  = est_central
    official["estimatedPacific"]  = est_pacific
    STANDINGS.write_text(json.dumps(official, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved estimated standings as of {estimated_as_of}")


def main() -> None:
    all_games: list[dict] = []

    # ── Monthly schedule pages (home/away reliable) ──────────────────────────
    months = []
    y, mo = NOW.year, NOW.month
    months.append((y, mo))
    months.append((y - 1, 12) if mo == 1 else (y, mo - 1))

    for year, month in months:
        url = f"{BASE}/{year}/schedule_{month:02d}.html"
        print(f"Fetching {url} ...")
        html = fetch_html(url)
        games = parse_games_monthly(html)
        print(f"  {len(games) // 2} completed games")
        all_games.extend(games)

    # ── Main games page: merge speed-report games not yet in monthly pages ────
    latest_games = fetch_latest_from_main_page()

    existing_keys: set[tuple] = {
        (g["date"], min(g["slug"], g["oppSlug"]), max(g["slug"], g["oppSlug"]))
        for g in all_games
    }
    new_from_main = 0
    for g in latest_games:
        key = (g["date"], min(g["t1"], g["t2"]), max(g["t1"], g["t2"]))
        if key in existing_keys:
            continue
        t1_name = SLUG_TO_NAME.get(g["t1"], "")
        t2_name = SLUG_TO_NAME.get(g["t2"], "")
        if not t1_name or not t2_name:
            continue
        r1, r2 = ("W", "L") if g["s1"] > g["s2"] else (("L", "W") if g["s1"] < g["s2"] else ("T", "T"))
        # URL convention: t1=visitor, t2=home → stadium is t2's
        stadium = STADIUMS.get(g["t2"], "")
        all_games.append({"date": g["date"], "slug": g["t1"], "opp": t2_name, "oppSlug": g["t2"],
                           "home": False, "score": g["s1"], "oppScore": g["s2"], "result": r1, "stadium": stadium})
        all_games.append({"date": g["date"], "slug": g["t2"], "opp": t1_name, "oppSlug": g["t1"],
                           "home": True,  "score": g["s2"], "oppScore": g["s1"], "result": r2, "stadium": stadium})
        existing_keys.add(key)
        new_from_main += 1
    if new_from_main:
        print(f"  +{new_from_main} new games from main page added to results")

    # ── Build results.json: last 3 per team ──────────────────────────────────
    all_games.sort(key=lambda g: g["date"], reverse=True)
    team_games: dict[str, list] = {}
    for g in all_games:
        sl = g["slug"]
        if sl not in team_games:
            team_games[sl] = []
        if len(team_games[sl]) < 3:
            team_games[sl].append({
                "date":          g["date"],
                "opponent":      g["opp"],
                "opponentSlug":  g["oppSlug"],
                "home":          g["home"],
                "score":         g["score"],
                "opponentScore": g["oppScore"],
                "result":        g["result"],
                "stadium":       g.get("stadium", ""),
            })

    teams = []
    for name, meta in TEAMS_BY_NAME.items():
        slug = meta["slug"]
        teams.append({
            "slug": slug, "name": name, "league": meta["league"],
            "color": meta["color"], "accent": meta["accent"],
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

    # ── Estimated standings: apply games newer than official asOf ─────────────
    update_standings_estimate(all_games, latest_games)


if __name__ == "__main__":
    main()
