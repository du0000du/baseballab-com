// src/lib/npb.ts — NPB データアクセス & 球団メタ
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const DATA = join(process.cwd(), 'data', 'npb');

export interface NpbTeam {
  slug: string; name: string; abbr: string;
  league: 'central' | 'pacific'; color: string; accent: string;
}

export const NPB_TEAMS: NpbTeam[] = [
  { slug: 'hanshin-tigers',      name: '阪神タイガース',              abbr: 'T',  league: 'central', color: '#fdef00', accent: '#000000' },
  { slug: 'yokohama-dena',       name: '横浜DeNAベイスターズ',        abbr: 'DB', league: 'central', color: '#0091d2', accent: '#ffffff' },
  { slug: 'yomiuri-giants',      name: '読売ジャイアンツ',            abbr: 'G',  league: 'central', color: '#f97709', accent: '#000000' },
  { slug: 'chunichi-dragons',    name: '中日ドラゴンズ',              abbr: 'D',  league: 'central', color: '#002569', accent: '#ffffff' },
  { slug: 'hiroshima-carp',      name: '広島東洋カープ',              abbr: 'C',  league: 'central', color: '#e60012', accent: '#ffffff' },
  { slug: 'yakult-swallows',     name: '東京ヤクルトスワローズ',      abbr: 'S',  league: 'central', color: '#00913a', accent: '#ffffff' },
  { slug: 'orix-buffaloes',      name: 'オリックス・バファローズ',    abbr: 'B',  league: 'pacific', color: '#000019', accent: '#b09b5b' },
  { slug: 'softbank-hawks',      name: '福岡ソフトバンクホークス',    abbr: 'H',  league: 'pacific', color: '#f4cd00', accent: '#000000' },
  { slug: 'nipponham-fighters',  name: '北海道日本ハムファイターズ',  abbr: 'F',  league: 'pacific', color: '#0a1f44', accent: '#cdd1d4' },
  { slug: 'rakuten-eagles',      name: '東北楽天ゴールデンイーグルス', abbr: 'E', league: 'pacific', color: '#860010', accent: '#000000' },
  { slug: 'seibu-lions',         name: '埼玉西武ライオンズ',          abbr: 'L',  league: 'pacific', color: '#003e92', accent: '#ffffff' },
  { slug: 'lotte-marines',       name: '千葉ロッテマリーンズ',        abbr: 'M',  league: 'pacific', color: '#221815', accent: '#ffffff' },
];

export function teamBySlug(slug: string): NpbTeam | undefined {
  return NPB_TEAMS.find(t => t.slug === slug);
}

export interface NpbPlayer {
  slug: string; name: string; nameRomaji: string;
  teamAbbr: string; teamSlug: string; teamName: string;
  league: 'central' | 'pacific'; group: 'batting' | 'pitching';
  qualified: boolean; season: string; rank: number | null;
  stats: Record<string, number | null>;
  asOf: string; fetchedAt: string; source: string; sourceUrl: string;
}

export function loadPlayers(): NpbPlayer[] {
  const dir = join(DATA, 'players');
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter(f => f.endsWith('.json'))
    .map(f => JSON.parse(readFileSync(join(dir, f), 'utf-8')) as NpbPlayer);
}

export function loadStandings(): any {
  const p = join(DATA, 'standings.json');
  return existsSync(p) ? JSON.parse(readFileSync(p, 'utf-8')) : { central: [], pacific: [] };
}

export function loadLeaders(season: string): any {
  const p = join(DATA, 'leaders', `${season}.json`);
  return existsSync(p) ? JSON.parse(readFileSync(p, 'utf-8')) : null;
}

export function loadMeta(): any {
  const p = join(DATA, 'meta.json');
  return existsSync(p) ? JSON.parse(readFileSync(p, 'utf-8')) : {};
}

export const NPB_SEASON = String(
  process.env.NPB_SEASON ||
  (new Date().getMonth() + 1 >= 3 ? new Date().getFullYear() : new Date().getFullYear() - 1)
);
