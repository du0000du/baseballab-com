// MLB チーム・所属選手の読み込み（リーグ別/チーム別選手一覧ページ用）
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

export interface MlbTeam {
  slug: string; id: number; name: string; abbr: string;
  league: 'al' | 'nl'; division: string;
}

export interface MlbRosterPlayer {
  slug: string; name: string; pos: string;
  group: string; // 'hitting' | 'pitching' | ''
  stat: any;
}

export function loadMlbTeams(): MlbTeam[] {
  const dir = join(process.cwd(), 'data/mlb/teams');
  const teams: MlbTeam[] = [];
  for (const f of readdirSync(dir).filter(f => f.endsWith('.json'))) {
    let info: any;
    try {
      info = JSON.parse(readFileSync(join(dir, f), 'utf-8')).info ?? {};
    } catch { continue; }
    if (!info.id) continue;
    teams.push({
      slug: f.replace('.json', ''),
      id: info.id,
      name: info.name ?? '',
      abbr: info.abbreviation ?? '',
      league: (info.league?.name ?? '').includes('American') ? 'al' : 'nl',
      division: info.division?.name ?? '',
    });
  }
  teams.sort((a, b) => a.name.localeCompare(b.name));
  return teams;
}

// 同一球団が別slugで重複している場合（例: athletics / oakland-athletics）は先勝ちで1つに
export function dedupeTeamsById(teams: MlbTeam[]): MlbTeam[] {
  const seen = new Set<number>();
  return teams.filter(t => (seen.has(t.id) ? false : (seen.add(t.id), true)));
}

function f3(v: any): string { if (v == null) return '—'; const n = Number(v); return isNaN(n) ? '—' : n.toFixed(3); }
function f2(v: any): string { if (v == null) return '—'; const n = Number(v); return isNaN(n) ? '—' : n.toFixed(2); }

export function statline(p: MlbRosterPlayer): string {
  if (p.group === 'hitting') {
    const hr = p.stat.homeRuns;
    return `打率 ${f3(p.stat.avg)}${hr != null ? `・${hr}本` : ''}`;
  }
  if (p.group === 'pitching') {
    const w = p.stat.wins;
    return `防御率 ${f2(p.stat.era)}${w != null ? `・${w}勝` : ''}`;
  }
  return '';
}

// リーグ別選手一覧ページ用: チームごとにグループ化した表示データを構築
export function buildLeagueGroups(league: 'al' | 'nl') {
  const teams = dedupeTeamsById(loadMlbTeams().filter(t => t.league === league));
  const byTeam = loadMlbPlayersByTeam();
  return teams
    .map(t => ({
      heading: t.name,
      anchor: t.slug,
      href: `/players/team/${t.slug}/`,
      players: (byTeam.get(t.id) ?? []).map(p => ({
        url: `/players/${p.slug}/`,
        pos: p.pos,
        name: p.name,
        statline: statline(p),
      })),
    }))
    .filter(g => g.players.length > 0);
}

export function loadMlbPlayersByTeam(): Map<number, MlbRosterPlayer[]> {
  const dir = join(process.cwd(), 'data/mlb/players');
  const map = new Map<number, MlbRosterPlayer[]>();
  for (const f of readdirSync(dir).filter(f => f.endsWith('.json'))) {
    let data: any;
    try {
      data = JSON.parse(readFileSync(join(dir, f), 'utf-8'));
    } catch { continue; }
    const entry = data.stats?.[0] ?? {};
    const split = entry.splits?.[0] ?? {};
    const teamId = split.team?.id;
    if (!teamId) continue;
    const list = map.get(teamId) ?? [];
    list.push({
      slug: f.replace('.json', ''),
      name: data.info?.fullName ?? f.replace('.json', ''),
      pos: data.info?.primaryPosition?.abbreviation ?? '—',
      group: entry.group?.displayName ?? '',
      stat: split.stat ?? {},
    });
    map.set(teamId, list);
  }
  for (const list of map.values()) {
    list.sort((a, b) =>
      a.group === b.group ? a.name.localeCompare(b.name) : a.group === 'hitting' ? -1 : 1);
  }
  return map;
}
