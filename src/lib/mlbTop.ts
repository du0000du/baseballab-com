// MLB 選手のスコア順トップN算出。
// compare/[compare].astro と players/[slug].astro で同一の順序を保証するため共有化。
// 順序が食い違うと /compare/A-vs-B/ の URL 方向が一致せずリンク切れになる。
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

export interface TopPlayer {
  slug: string;
  name: string;
  group: string; // 'hitting' | 'pitching' | ''
  score: number;
  data: any;
}

export function getTopPlayers(limit = 60): TopPlayer[] {
  const dir = join(process.cwd(), 'data/mlb/players');
  const files = readdirSync(dir).filter(f => f.endsWith('.json'));

  const players: TopPlayer[] = [];
  for (const file of files) {
    const slug = file.replace('.json', '');
    let data: any;
    try {
      data = JSON.parse(readFileSync(join(dir, file), 'utf-8'));
    } catch { continue; }
    const info = data.info ?? {};
    const stat = data.stats?.[0]?.splits?.[0]?.stat ?? {};
    const group = data.stats?.[0]?.group?.displayName ?? '';
    let score = info.active ? 100 : 0;
    if (group === 'hitting') {
      score += Number(stat.gamesPlayed || 0) * 2;
      score += Number(stat.homeRuns || 0) * 4;
      score += Number(stat.rbi || 0);
      score += Number(stat.hits || 0) * 0.5;
    } else if (group === 'pitching') {
      score += Number(stat.gamesPlayed || 0) * 2;
      score += Number(stat.wins || 0) * 6;
      score += Number(stat.strikeOuts || 0) * 0.5;
      score += Number(stat.saves || 0) * 3;
    }
    players.push({ slug, name: info.fullName ?? 'Unknown', group, score, data });
  }

  players.sort((a, b) => b.score - a.score);
  return players.slice(0, limit);
}

// index ペア → 比較ページ URL（インデックスが小さい方が先＝生成時の順序と一致）
export function comparePairUrl(top: TopPlayer[], i: number, j: number): string {
  const [a, b] = i < j ? [top[i], top[j]] : [top[j], top[i]];
  return `/compare/${a.slug}-vs-${b.slug}/`;
}

// 対象選手（index i）に近いランクの相手を最大 count 名選ぶ（同グループ優先）
export function pickOpponents(top: TopPlayer[], i: number, count: number, exclude: number[] = []): number[] {
  const self = top[i];
  const candidates = top
    .map((_, k) => k)
    .filter(k => k !== i && !exclude.includes(k))
    .sort((a, b) => {
      const sameA = top[a].group === self.group ? 0 : 1;
      const sameB = top[b].group === self.group ? 0 : 1;
      if (sameA !== sameB) return sameA - sameB;
      return Math.abs(a - i) - Math.abs(b - i);
    });
  return candidates.slice(0, count);
}
