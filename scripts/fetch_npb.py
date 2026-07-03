#!/usr/bin/env python3
"""
fetch_npb.py — NPB（日本プロ野球）公式成績データ取得スクリプト

データ出典: NPB.jp 日本野球機構オフィシャルサイト（https://npb.jp/）
  ※掲載される「成績数値（事実データ）」のみを取得し、各ページに明確な出典表示を行う。
  ※HTML・画像・レイアウト等の二次利用は行わない（数値のみ抽出）。

依存: Python標準ライブラリ + pykakasi（ローマ字slug生成用）
  pip install pykakasi

シーズン判定: 3月以降は当年、1〜2月は前年（オフシーズン）。NPB_SEASON env varで上書き可。

使い方:
  python3 scripts/fetch_npb.py --mode all      # 全取得
  python3 scripts/fetch_npb.py --mode test     # 接続テスト

出力:
  data/npb/standings.json
  data/npb/leaders/{SEASON}.json
  data/npb/players/{slug}.json
  data/npb/meta.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
BASE = "https://npb.jp/bis"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "npb"

SEASON = str(int(
    os.environ.get("NPB_SEASON")
    or (datetime.now().year if datetime.now().month >= 3 else datetime.now().year - 1)
))

SOURCE_NAME = "NPB.jp 日本野球機構"
SOURCE_URL = "https://npb.jp/bis/{season}/stats/".format(season=SEASON)

# 球団メタ（成績表の (略号) 文字 -> slug / 正式名 / リーグ / ブランドカラー）
TEAMS = {
    # Central League
    "神":  {"slug": "hanshin-tigers",      "name": "阪神タイガース",            "abbr": "T",  "league": "central", "color": "#fdef00", "accent": "#000000"},
    "デ":  {"slug": "yokohama-dena",       "name": "横浜DeNAベイスターズ",      "abbr": "DB", "league": "central", "color": "#0091d2", "accent": "#ffffff"},
    "巨":  {"slug": "yomiuri-giants",      "name": "読売ジャイアンツ",          "abbr": "G",  "league": "central", "color": "#f97709", "accent": "#000000"},
    "中":  {"slug": "chunichi-dragons",    "name": "中日ドラゴンズ",            "abbr": "D",  "league": "central", "color": "#002569", "accent": "#ffffff"},
    "広":  {"slug": "hiroshima-carp",      "name": "広島東洋カープ",            "abbr": "C",  "league": "central", "color": "#e60012", "accent": "#ffffff"},
    "ヤ":  {"slug": "yakult-swallows",     "name": "東京ヤクルトスワローズ",    "abbr": "S",  "league": "central", "color": "#00913a", "accent": "#ffffff"},
    # Pacific League
    "オ":  {"slug": "orix-buffaloes",      "name": "オリックス・バファローズ",  "abbr": "B",  "league": "pacific", "color": "#000019", "accent": "#b09b5b"},
    "ソ":  {"slug": "softbank-hawks",      "name": "福岡ソフトバンクホークス",  "abbr": "H",  "league": "pacific", "color": "#fbc600", "accent": "#000000"},
    "日":  {"slug": "nipponham-fighters",  "name": "北海道日本ハムファイターズ", "abbr": "F", "league": "pacific", "color": "#0a1f44", "accent": "#cdd1d4"},
    "楽":  {"slug": "rakuten-eagles",      "name": "東北楽天ゴールデンイーグルス","abbr": "E", "league": "pacific", "color": "#860010", "accent": "#000000"},
    "西":  {"slug": "seibu-lions",         "name": "埼玉西武ライオンズ",        "abbr": "L",  "league": "pacific", "color": "#003e92", "accent": "#ffffff"},
    "ロ":  {"slug": "lotte-marines",       "name": "千葉ロッテマリーンズ",      "abbr": "M",  "league": "pacific", "color": "#000000", "accent": "#ffffff"},
}

LEAGUE_CODE = {"central": "c", "pacific": "p"}

# チーム別個人成績ページ（idb1/idp1_{code}.html）の URL コード
# リーグ成績ページ（bat/pit）は規定到達者のみのため、
# 規定未到達選手（例: 勝利数上位でも投球回不足の投手）はチーム別ページから補完する
TEAM_PAGE_CODE = {
    "神": "t", "デ": "db", "巨": "g", "中": "d", "広": "c", "ヤ": "s",
    "オ": "b", "ソ": "h", "日": "f", "楽": "e", "西": "l", "ロ": "m",
}

# ---------------------------------------------------------------------------
# ローマ字 slug 生成（pykakasi）
# ---------------------------------------------------------------------------
try:
    from npb_name_map import NAME_MAP, KANJI_NORM
except ImportError:  # scripts/ 直下実行でない場合
    import os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from npb_name_map import NAME_MAP, KANJI_NORM

_kks = None
def _get_kakasi():
    global _kks
    if _kks is None:
        import pykakasi
        _kks = pykakasi.kakasi()
    return _kks


def _norm_kanji(text: str) -> str:
    for a, b in KANJI_NORM.items():
        text = text.replace(a, b)
    return text


def romaji(text: str) -> str:
    """日本語（漢字/かな）+ カタカナ外国人名 をローマ字へ。"""
    parts = _get_kakasi().convert(_norm_kanji(text))
    out = " ".join(p["hepburn"] for p in parts if p["hepburn"].strip())
    return out.strip()


def _norm_key(name_ja: str) -> str:
    return re.sub(r"\s+", " ", name_ja.replace("　", " ")).strip()


def slugify_name(name_ja: str) -> str:
    """
    既知選手はマップから正確なslug、未登録はpykakasiフォールバック。
    '佐藤 輝明' -> 'teruaki-sato' / 'レイエス' -> 'reiesu'
    """
    key = _norm_key(name_ja)
    if key in NAME_MAP:
        return NAME_MAP[key][0]
    r = romaji(key).lower()
    r = re.sub(r"[^a-z0-9 ]", "", r)
    r = re.sub(r"\s+", "-", r).strip("-")
    return r or "player"


def romaji_display(name_ja: str) -> str:
    """表示用ローマ字（Given Family を Title Case）。"""
    key = _norm_key(name_ja)
    if key in NAME_MAP:
        return NAME_MAP[key][1]
    return " ".join(w.capitalize() for w in romaji(key).split())


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def fetch_html(url: str) -> str:
    req = Request(url, headers={
        "Accept": "text/html",
        "User-Agent": "baseballab-data-fetcher/1.0 (+https://baseballab.com)",
    })
    try:
        with urlopen(req, timeout=20) as res:
            raw = res.read()
            return raw.decode("utf-8", errors="replace")  # NPB.jp は UTF-8
    except HTTPError as e:
        print(f"  HTTP {e.code}: {url}", file=sys.stderr)
        return ""
    except URLError as e:
        print(f"  URLError: {e.reason}: {url}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"  ERROR: {e}: {url}", file=sys.stderr)
        return ""


# ---------------------------------------------------------------------------
# HTML テーブル抽出（標準ライブラリのみ）
# ---------------------------------------------------------------------------
class TableParser(HTMLParser):
    """全 <table> を [rows][cells] のテキストとして抽出。"""
    def __init__(self):
        super().__init__()
        self.tables = []
        self._cur_table = None
        self._cur_row = None
        self._cur_cell = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._cur_table = []
        elif tag == "tr" and self._cur_table is not None:
            self._cur_row = []
        elif tag in ("td", "th") and self._cur_row is not None:
            self._cur_cell = []
            self._in_cell = True
        elif tag == "br" and self._in_cell:
            self._cur_cell.append(" ")

    def handle_endtag(self, tag):
        if tag == "table" and self._cur_table is not None:
            self.tables.append(self._cur_table)
            self._cur_table = None
        elif tag == "tr" and self._cur_row is not None:
            self._cur_table.append(self._cur_row)
            self._cur_row = None
        elif tag in ("td", "th") and self._in_cell:
            text = "".join(self._cur_cell)
            text = re.sub(r"\s+", " ", text).strip()
            self._cur_row.append(text)
            self._cur_cell = None
            self._in_cell = False

    def handle_data(self, data):
        if self._in_cell:
            self._cur_cell.append(data)


def extract_tables(html: str):
    p = TableParser()
    p.feed(html)
    return p.tables


def find_as_of(html: str) -> str:
    """'2026年5月24日 現在' を抽出して ISO 日付に。"""
    m = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*現在", html)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ""


# ---------------------------------------------------------------------------
# 選手行パース
# ---------------------------------------------------------------------------
NAME_TEAM_RE = re.compile(r"^(.*?)[\(（]([^\)）]+)[\)）]\s*$")


def split_name_team(cell: str):
    """'佐藤 輝明(神)' -> ('佐藤 輝明', '神')。"""
    cell = cell.replace("　", " ").strip()
    m = NAME_TEAM_RE.match(cell)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return cell, ""


def rows_to_dicts(table):
    """ヘッダ行（順位/選手 or 投手 を含む）を見つけ、以降をdict化。"""
    header_idx = None
    header = None
    for i, row in enumerate(table):
        joined = "".join(row)
        if "順位" in joined and ("選手" in joined or "投手" in joined):
            header_idx = i
            header = row
            break
    if header_idx is None:
        return None, []
    records = []
    for row in table[header_idx + 1:]:
        if len(row) < len(header) - 1:
            continue
        if not re.match(r"^\d+$", row[0].strip()):
            continue
        rec = {h.strip(): v.strip() for h, v in zip(header, row)}
        records.append(rec)
    return header, records


def to_num(v: str):
    v = (v or "").strip()
    if v in ("", "-", "－", "−"):
        return None
    try:
        return float(v) if "." in v else int(v)
    except ValueError:
        return v


# ---------------------------------------------------------------------------
# 打撃 / 投手 フィールド対応
# ---------------------------------------------------------------------------
BAT_FIELDS = {
    "打率": "avg", "試合": "games", "打席": "pa", "打数": "ab", "得点": "runs",
    "安打": "hits", "二塁打": "doubles", "三塁打": "triples", "本塁打": "hr",
    "塁打": "tb", "打点": "rbi", "盗塁": "sb", "盗塁刺": "cs", "犠打": "sac",
    "犠飛": "sf", "四球": "bb", "故意四": "ibb", "死球": "hbp", "三振": "so",
    "併殺打": "gidp", "長打率": "slg", "出塁率": "obp",
}
PIT_FIELDS = {
    "防御率": "era", "登板": "games", "勝利": "wins", "敗北": "losses",
    "セーブ": "saves", "ホールド": "holds", "ＨＰ": "hp", "HP": "hp",
    "完投": "cg", "完封勝": "sho", "無四球": "nbb", "勝率": "winpct",
    "打者": "bf", "投球回": "ip", "安打": "hits", "本塁打": "hr",
    "四球": "bb", "故意四": "ibb", "死球": "hbp", "三振": "so",
    "暴投": "wp", "ボーク": "balk", "失点": "runs", "自責点": "er",
}


def build_player_record(rec: dict, group: str, league: str, fetched_at: str, as_of: str,
                        qualified: bool = True):
    """ヘッダ->値 dict から選手レコードを構築（live/seed共通）。"""
    name_col = "選手" if group == "batting" else "投手"
    field_map = BAT_FIELDS if group == "batting" else PIT_FIELDS
    name_ja, abbr = split_name_team(rec.get(name_col, ""))
    if not name_ja:
        return None
    team = TEAMS.get(abbr)
    stats = {}
    for jp, en in field_map.items():
        if jp in rec:
            stats[en] = to_num(rec[jp])
    # 派生指標
    if group == "batting":
        obp = stats.get("obp"); slg = stats.get("slg")
        if isinstance(obp, float) and isinstance(slg, float):
            stats["ops"] = round(obp + slg, 3)
    else:
        hits = stats.get("hits"); bb = stats.get("bb"); ip = stats.get("ip")
        if isinstance(ip, (int, float)) and ip:
            whole = int(ip); frac = round((ip - whole) * 10)
            ip_real = whole + (frac / 3.0 if frac in (1, 2) else 0)
            if ip_real and isinstance(hits, (int, float)) and isinstance(bb, (int, float)):
                stats["whip"] = round((hits + bb) / ip_real, 2)
    return {
        "slug": slugify_name(name_ja),
        "name": name_ja,
        "nameRomaji": romaji_display(name_ja),
        "teamAbbr": abbr,
        "teamSlug": team["slug"] if team else "",
        "teamName": team["name"] if team else "",
        "league": league,
        "group": group,
        "qualified": qualified,
        "season": SEASON,
        "rank": to_num(rec.get("順位")),
        "stats": stats,
        "asOf": as_of,
        "fetchedAt": fetched_at,
        "source": SOURCE_NAME,
        "sourceUrl": f"{BASE}/{SEASON}/stats/{'bat' if group=='batting' else 'pit'}_{LEAGUE_CODE[league]}.html",
    }


def parse_stat_page(html: str, group: str, league: str, fetched_at: str):
    """打撃/投手ページから選手レコード（複数テーブル統合・重複排除）を返す。"""
    as_of = find_as_of(html)
    name_col = "選手" if group == "batting" else "投手"
    players, order = {}, []
    stat_table_idx = 0  # 規定到達(qualified)は各ページ最初の成績テーブルのみ
    for table in extract_tables(html):
        header, recs = rows_to_dicts(table)
        if not recs or name_col not in header:
            continue
        qualified = (stat_table_idx == 0)
        stat_table_idx += 1
        for rec in recs:
            name_ja, abbr = split_name_team(rec.get(name_col, ""))
            key = (name_ja, abbr)
            if not name_ja or key in players:
                continue  # 規定表優先で重複排除
            player = build_player_record(rec, group, league, fetched_at, as_of, qualified)
            if player:
                players[key] = player
                order.append(key)
    return [players[k] for k in order], as_of


def parse_team_stat_page(html: str, group: str, league: str, abbr: str, fetched_at: str):
    """
    チーム別個人成績ページ（idb1/idp1_{code}.html）をパース。全所属選手が載る。
    リーグページとの相違: 「順位」列なし / 選手名にチーム略号なし / 利き腕記号（*・＋）付き。
    """
    as_of = find_as_of(html)
    marker = "打数" if group == "batting" else "投球回"
    name_col = "選手" if group == "batting" else "投手"
    out = []
    for table in extract_tables(html):
        header_idx = None
        for i, row in enumerate(table):
            if "選手" in row and marker in "".join(row):
                header_idx = i
                break
        if header_idx is None:
            continue
        header = table[header_idx]
        name_idx = header.index("選手")
        for row in table[header_idx + 1:]:
            if len(row) < len(header):
                continue
            name = re.sub(r"^[*+＊＋#]+", "", row[name_idx]).strip()
            if not name or name in ("選手", "計", "合計", "チーム計"):
                continue
            rec = {h.strip(): v.strip() for h, v in zip(header, row)}
            rec[name_col] = f"{name}({abbr})"
            p = build_player_record(rec, group, league, fetched_at, as_of, qualified=False)
            if p:
                prefix = "idb1" if group == "batting" else "idp1"
                p["sourceUrl"] = f"{BASE}/{SEASON}/stats/{prefix}_{TEAM_PAGE_CODE[abbr]}.html"
                out.append(p)
    return out, as_of


# ---------------------------------------------------------------------------
# 順位表
# ---------------------------------------------------------------------------
def parse_standings(html: str, league: str):
    as_of = find_as_of(html)
    rows_out = []
    for table in extract_tables(html):
        head = None
        for i, row in enumerate(table):
            j = "".join(row)
            if "試合" in j and "勝率" in j:
                head = i
                break
        if head is None:
            continue
        rank = 0
        for row in table[head + 1:]:
            cells = [c.strip() for c in row]
            if len(cells) < 6:
                continue
            team_cell = cells[0]
            matched = None
            for abbr, meta in TEAMS.items():
                if meta["league"] != league:
                    continue
                if meta["name"][:3] in team_cell or meta["name"] in team_cell:
                    matched = (abbr, meta)
                    break
            if not matched:
                continue
            _, meta = matched
            nums = cells[1:]
            rank += 1
            try:
                rows_out.append({
                    "rank": rank, "teamSlug": meta["slug"], "teamName": meta["name"],
                    "teamAbbr": meta["abbr"], "league": league,
                    "games": to_num(nums[0]), "wins": to_num(nums[1]),
                    "losses": to_num(nums[2]), "ties": to_num(nums[3]),
                    "pct": nums[4], "gb": nums[5] if len(nums) > 5 else "",
                })
            except IndexError:
                continue
        if rows_out:
            break
    return rows_out, as_of


# ---------------------------------------------------------------------------
# リーダーボード生成（選手データから算出）
# ---------------------------------------------------------------------------
def build_leaders(players):
    # レート系タイトル（首位打者/最優秀防御率等）は規定到達者のみ対象
    QUALIFIED_ONLY = {"avg", "ops", "obp", "slg", "era", "whip"}

    def top(group, league, key, n=10, asc=False):
        pool = [p for p in players if p["group"] == group and p["league"] == league
                and isinstance(p["stats"].get(key), (int, float))]
        if key in QUALIFIED_ONLY:
            pool = [p for p in pool if p.get("qualified")]
        pool.sort(key=lambda p: p["stats"][key], reverse=not asc)
        return [{
            "rank": i + 1, "slug": p["slug"], "player": p["name"],
            "team": p["teamAbbr"], "teamSlug": p["teamSlug"], "value": p["stats"][key],
        } for i, p in enumerate(pool[:n])]

    leaders = {"season": SEASON,
               "fetchedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    for lg in ("central", "pacific"):
        leaders[lg] = {
            "batting": {
                "avg": top("batting", lg, "avg"), "hr": top("batting", lg, "hr"),
                "rbi": top("batting", lg, "rbi"), "sb": top("batting", lg, "sb"),
                "ops": top("batting", lg, "ops"), "hits": top("batting", lg, "hits"),
            },
            "pitching": {
                "era": top("pitching", lg, "era", asc=True), "wins": top("pitching", lg, "wins"),
                "so": top("pitching", lg, "so"), "saves": top("pitching", lg, "saves"),
                "holds": top("pitching", lg, "holds"), "whip": top("pitching", lg, "whip", asc=True),
            },
        }
    return leaders


# ---------------------------------------------------------------------------
# 書き出し
# ---------------------------------------------------------------------------
def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe_slugs(all_players):
    seen = {}
    for p in all_players:
        s = p["slug"]
        if s in seen and seen[s] is not p:
            # サフィックスは URL 安全な ASCII の球団略号（F/H/…）を使う（teamAbbr は「日」等の和文字）
            team = TEAMS.get(p["teamAbbr"], {}).get("abbr", "x").lower()
            cand = f"{s}-{team}"
            if cand in seen:
                cand = f"{cand}-{p['group']}"
            n = 2
            base = cand
            while cand in seen:
                cand = f"{base}-{n}"
                n += 1
            p["slug"] = cand
        seen[p["slug"]] = p


def sync_leader_players(all_players: list, players_dir: Path, leaders: dict):
    """
    リーダーボード掲載選手のJSONを自動補完（安全網）。
    通常は run_all() の全スクレイプで全員カバーされるが、
    ページ取得失敗・slug衝突・外国人選手名のフォールバックで漏れた場合に対応。
    """
    player_map = {p["slug"]: p for p in all_players}
    existing = {f.stem for f in players_dir.glob("*.json")}

    missing: "list[tuple[str, str, str]]" = []  # (slug, player_name_ja, league/group/cat)
    for lg in ("central", "pacific"):
        for grp in ("batting", "pitching"):
            for cat, entries in leaders.get(lg, {}).get(grp, {}).items():
                for e in entries:
                    slug = e.get("slug")
                    if slug and slug not in existing:
                        missing.append((slug, e.get("player", "?"), f"{lg}/{grp}/{cat}"))

    if not missing:
        return  # 全員登録済み

    print(f"=== リーダーボード選手ファイル補完: {len(missing)}名 ===")
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    retried: "set[str]" = set()  # 再取得済みURL（二重取得防止）
    for slug, name_ja, location in missing:
        if slug in player_map:
            write_json(players_dir / f"{slug}.json", player_map[slug])
            existing.add(slug)
            print(f"  ✅ {name_ja} ({location}) → {slug}.json")
        else:
            # all_players にも存在しない（スクレイプ失敗）→ 該当ページを再取得
            league, group = location.split("/")[:2]
            code = LEAGUE_CODE[league]
            prefix = "bat" if group == "batting" else "pit"
            url = f"{BASE}/{SEASON}/stats/{prefix}_{code}.html"
            if url not in retried:
                print(f"  再取得: {url}")
                html = fetch_html(url)
                retried.add(url)
                if html:
                    recs, _ = parse_stat_page(html, group, league, fetched_at)
                    for p in recs:
                        if p["slug"] not in existing:
                            write_json(players_dir / f"{p['slug']}.json", p)
                            player_map[p["slug"]] = p
                            existing.add(p["slug"])
                time.sleep(0.5)
            if slug in player_map:
                print(f"  ✅ {name_ja} 再取得成功 → {slug}.json")
            else:
                print(f"  ⚠ {name_ja} ({slug}) 見つからず", file=sys.stderr)


def run_all():
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    players_dir = DATA_DIR / "players"
    players_dir.mkdir(parents=True, exist_ok=True)

    all_players, as_of_dates = [], []
    for league, code in LEAGUE_CODE.items():
        for group, prefix in (("batting", "bat"), ("pitching", "pit")):
            url = f"{BASE}/{SEASON}/stats/{prefix}_{code}.html"
            print(f"取得: {url}")
            html = fetch_html(url)
            if not html:
                print(f"  ⚠ 空応答: {url}", file=sys.stderr)
                continue
            recs, as_of = parse_stat_page(html, group, league, fetched_at)
            if as_of:
                as_of_dates.append(as_of)
            print(f"  {league}/{group}: {len(recs)}名")
            all_players.extend(recs)
            time.sleep(0.5)

    if not all_players:
        print("❌ 選手データ取得ゼロ。既存データを保持して終了。", file=sys.stderr)
        sys.exit(1)

    # チーム別ページから規定未到達選手を補完（リーグページ掲載者はスキップ）
    seen = {(p["name"], p["teamAbbr"], p["group"]) for p in all_players}
    for abbr, meta in TEAMS.items():
        code = TEAM_PAGE_CODE[abbr]
        team_recs = {"batting": [], "pitching": []}
        for group, prefix in (("batting", "idb1"), ("pitching", "idp1")):
            url = f"{BASE}/{SEASON}/stats/{prefix}_{code}.html"
            print(f"取得: {url}")
            html = fetch_html(url)
            if not html:
                print(f"  ⚠ 空応答: {url}", file=sys.stderr)
                continue
            recs, as_of = parse_team_stat_page(html, group, meta["league"], abbr, fetched_at)
            if as_of:
                as_of_dates.append(as_of)
            team_recs[group] = recs
            time.sleep(0.5)

        # 同一選手が打撃・投手の両ページに載る場合（投手の打席・野手の緊急登板）、
        # 主たる役割のレコードだけ残す。打席40以上かつ投球回10以上なら二刀流として両方残す。
        def _num(v):
            return float(v) if isinstance(v, (int, float)) else 0.0
        pit_by_name = {p["name"]: p for p in team_recs["pitching"]}
        merged = list(team_recs["pitching"])
        for p in team_recs["batting"]:
            q = pit_by_name.get(p["name"])
            if q is not None:
                pa = _num(p["stats"].get("pa"))
                ip = _num(q["stats"].get("ip"))
                if not (pa >= 40 and ip >= 10):
                    if ip * 4 >= pa:
                        continue  # 投手が主 → 打撃行を捨てる
                    merged.remove(q)  # 野手が主 → 登板行を捨てる
            merged.append(p)

        added = 0
        for p in merged:
            key = (p["name"], p["teamAbbr"], p["group"])
            if key in seen:
                continue
            seen.add(key)
            all_players.append(p)
            added += 1
        print(f"  {meta['name']}: +{added}名")

    dedupe_slugs(all_players)

    # 既存選手JSONを一旦掃除（離脱選手の残骸防止）してから書き出し
    if players_dir.exists():
        for old in players_dir.glob("*.json"):
            old.unlink()
    for p in all_players:
        write_json(players_dir / f"{p['slug']}.json", p)

    standings = {"season": SEASON, "fetchedAt": fetched_at, "central": [], "pacific": []}
    for league, code in LEAGUE_CODE.items():
        url = f"{BASE}/{SEASON}/stats/std_{code}.html"
        print(f"取得: {url}")
        html = fetch_html(url)
        if html:
            rows, as_of = parse_standings(html, league)
            standings[league] = rows
            if as_of:
                as_of_dates.append(as_of)
            print(f"  {league}: {len(rows)}球団")
        time.sleep(0.5)
    write_json(DATA_DIR / "standings.json", standings)

    # リーダーボード生成（players データから算出して毎回更新）
    leaders = build_leaders(all_players)
    write_json(DATA_DIR / "leaders" / f"{SEASON}.json", leaders)
    hr_c = len(leaders.get("central", {}).get("batting", {}).get("hr", []))
    hr_p = len(leaders.get("pacific", {}).get("batting", {}).get("hr", []))
    print(f"  leaders: HR central={hr_c}件, pacific={hr_p}件")

    # リーダーボード掲載選手の補完チェック（安全網）
    sync_leader_players(all_players, players_dir, leaders)

    as_of = max(as_of_dates) if as_of_dates else ""
    write_json(DATA_DIR / "meta.json", {
        "season": SEASON, "fetchedAt": fetched_at, "asOf": as_of,
        "playerCount": len(all_players), "source": SOURCE_NAME, "sourceUrl": SOURCE_URL,
    })
    print(f"\n[OK] done: {len(all_players)} players / as_of={as_of}\n   -> {DATA_DIR}")


def run_test():
    url = f"{BASE}/{SEASON}/stats/bat_c.html"
    print(f"=== NPB connection test: {url} ===")
    html = fetch_html(url)
    if not html:
        print("[FAIL] fetch failed")
        return False
    recs, as_of = parse_stat_page(html, "batting", "central", "")
    print(f"[OK] {len(recs)} players / as_of={as_of}")
    for p in recs[:3]:
        print(f"   {p['rank']} {p['name']} ({p['teamAbbr']}) avg={p['stats'].get('avg')} slug={p['slug']}")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="NPB official stats fetcher")
    ap.add_argument("--mode", choices=["test", "all"], default="all")
    args = ap.parse_args()
    run_test() if args.mode == "test" else run_all()
