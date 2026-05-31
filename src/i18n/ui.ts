export type Lang = 'ja' | 'en';

export const ui = {
  ja: {
    // Nav
    nav_mlb: 'MLB', nav_npb: 'NPB', nav_glossary: '指標解説', nav_gear: '機材', nav_streaming: '配信',
    // Footer cols
    footer_glossary: '指標解説', footer_batting: '打撃指標', footer_pitching: '投球指標', footer_data: 'データ',
    footer_all_glossary: 'すべての指標 →', footer_mlb_data: 'MLB データ', footer_mlb_ranking: 'MLB ランキング',
    footer_npb_data: 'NPB データ', footer_players: 'MLB 選手一覧', footer_teams: 'チーム一覧',
    footer_privacy: 'プライバシーポリシー', footer_disclaimer: '免責事項', footer_disclosure: '広告について',
    lang_switch: 'English',
    // Common labels
    see_more: '詳細を見る →', updated: '更新', rank: '順位', wins: '勝', losses: '敗', ties: '分',
    win_pct: '勝率', gb: 'ゲーム差', player: '選手', batting_avg: '打率', hr: '本', rbi: '点',
    ops: 'OPS', hits: '安打', sb: '盗塁', era: '防御率', so: '奪三振', ip: '投球回', saves: 'S',
    // Leaders
    batting_section: '🏏 打撃部門', pitching_section: '⚾ 投球部門',
    no_data: 'データを読み込み中です。しばらくお待ちください。',
    // Season
    season_data: 'シーズンデータ',
  },
  en: {
    // Nav
    nav_mlb: 'MLB', nav_npb: 'NPB', nav_glossary: 'Stats Guide', nav_gear: 'Gear', nav_streaming: 'Streaming',
    // Footer cols
    footer_glossary: 'Stats Guide', footer_batting: 'Batting Stats', footer_pitching: 'Pitching Stats', footer_data: 'Data',
    footer_all_glossary: 'All Stats →', footer_mlb_data: 'MLB Data', footer_mlb_ranking: 'MLB Rankings',
    footer_npb_data: 'NPB Data', footer_players: 'MLB Players', footer_teams: 'Teams',
    footer_privacy: 'Privacy Policy', footer_disclaimer: 'Disclaimer', footer_disclosure: 'Advertising',
    lang_switch: '日本語',
    // Common labels
    see_more: 'View Details →', updated: 'Updated', rank: 'Rank', wins: 'W', losses: 'L', ties: 'T',
    win_pct: 'PCT', gb: 'GB', player: 'Player', batting_avg: 'AVG', hr: 'HR', rbi: 'RBI',
    ops: 'OPS', hits: 'H', sb: 'SB', era: 'ERA', so: 'SO', ip: 'IP', saves: 'SV',
    // Leaders
    batting_section: '🏏 Batting', pitching_section: '⚾ Pitching',
    no_data: 'Data is loading. Please wait.',
    // Season
    season_data: 'Season Data',
  },
} as const;

export type UiKey = keyof typeof ui.ja;

export function t(lang: Lang, key: UiKey): string {
  return (ui[lang] as Record<string, string>)[key] ?? (ui.ja as Record<string, string>)[key] ?? key;
}
