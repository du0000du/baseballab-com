#!/usr/bin/env python3
"""
validate_data.py — NPB/MLB data freshness and completeness checks.
Exit 0 if all checks pass, exit 1 if any fail.
Writes a markdown table to $GITHUB_STEP_SUMMARY when running in Actions.
"""
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SUMMARY_FILE = os.environ.get("GITHUB_STEP_SUMMARY", "")
NOW_UTC = datetime.now(timezone.utc)
SEASON = str(NOW_UTC.year if NOW_UTC.month >= 3 else NOW_UTC.year - 1)

rows: list[tuple[bool, str, str]] = []
errors: list[str] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    rows.append((ok, name, detail))
    if not ok:
        errors.append(f"{name}: {detail}")


def days_old(date_str: str) -> int:
    if not date_str:
        return 999
    try:
        d = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return (NOW_UTC - d).days
    except Exception:
        return 999


# --- NPB -------------------------------------------------------------------
npb_meta = ROOT / "data" / "npb" / "meta.json"
if npb_meta.exists():
    m = json.loads(npb_meta.read_text(encoding="utf-8"))
    age = days_old(m.get("fetchedAt", ""))
    count = m.get("playerCount", 0)
    check(age <= 3, "NPB fetchedAt freshness", f"{m.get('fetchedAt', '?')[:10]} ({age}d ago)")
    check(count >= 50, "NPB playerCount", f"{count}")
    players_dir = ROOT / "data" / "npb" / "players"
    n_files = len(list(players_dir.glob("*.json"))) if players_dir.exists() else 0
    check(n_files >= 50, "NPB player files on disk", f"{n_files} files")
else:
    check(False, "NPB meta.json", "file missing")

# --- MLB players -----------------------------------------------------------
mlb_players = ROOT / "data" / "mlb" / "players"
if mlb_players.exists():
    files = list(mlb_players.glob("*.json"))
    check(len(files) >= 10, "MLB player count", f"{len(files)}")
    if files:
        sample = json.loads(files[0].read_text(encoding="utf-8"))
        check(bool(sample.get("stats")), "MLB player has stats", files[0].stem)
else:
    check(False, "MLB players dir", "data/mlb/players/ missing")

# --- MLB leaders -----------------------------------------------------------
leaders_file = ROOT / "data" / "mlb" / "leaders" / f"{SEASON}.json"
if leaders_file.exists():
    ld = json.loads(leaders_file.read_text(encoding="utf-8"))
    age = days_old(ld.get("fetched_at", ld.get("fetchedAt", "")))
    bat_hr = len(ld.get("batting", {}).get("homeRuns", []))
    pit_era = len(ld.get("pitching", {}).get("era", []))
    check(age <= 3, "MLB leaders freshness", f"{ld.get('fetched_at','?')[:10]} ({age}d ago)")
    check(bat_hr >= 5, "MLB leaders batting list", f"{bat_hr} HR entries")
    check(pit_era >= 5, "MLB leaders pitching list", f"{pit_era} ERA entries")
else:
    check(False, "MLB leaders file", f"data/mlb/leaders/{SEASON}.json missing")


# --- Output ----------------------------------------------------------------
header = f"## Data Validation — {NOW_UTC.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
table = "| | Check | Detail |\n|---|---|---|\n"
for ok, name, detail in rows:
    icon = "✅" if ok else "❌"
    table += f"| {icon} | {name} | {detail} |\n"

footer = "\n### ✅ All checks passed\n" if not errors else (
    f"\n### ❌ {len(errors)} check(s) failed\n" +
    "".join(f"- {e}\n" for e in errors)
)

summary = header + table + footer

if SUMMARY_FILE:
    with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
        f.write(summary)

print(summary)
sys.exit(1 if errors else 0)
