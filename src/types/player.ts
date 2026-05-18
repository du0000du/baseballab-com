// Baseballab — 選手データ型定義
// TASK-002: TypeScript型定義

export interface PlayerStats {
  // 打撃成績
  avg: number;       // 打率
  obp: number;       // 出塁率
  slg: number;       // 長打率
  ops: number;       // OPS
  war: number;       // WAR
  hr: number;        // 本塁打
  rbi: number;       // 打点
  sb: number;        // 盗塁
  wrcPlus: number;   // wRC+

  // 投手成績（投手のみ使用）
  era?: number;      // 防御率
  fip?: number;      // FIP
  whip?: number;     // WHIP
  k9?: number;       // K/9
  bb9?: number;      // BB/9
  ip?: number;       // 投球回
}

export interface PlayerData {
  id: string;                   // slug（例: shohei-ohtani）
  name: string;                 // 選手名（英語）
  nameJa: string;               // 選手名（日本語）
  team: string;                 // チーム略称（例: LAD）
  teamId: string;               // チームslug
  position: string;             // ポジション（例: DH/SP）
  number: number;               // 背番号
  bats: 'R' | 'L' | 'S';      // 打席
  throws: 'R' | 'L';           // 投球腕
  birthDate: string;            // 生年月日（ISO形式）
  birthplace: string;           // 出身地
  height: string;               // 身長
  weight: string;               // 体重
  league: 'MLB' | 'NPB';       // リーグ
  stats: PlayerStats;           // 成績
  season: number;               // 対象シーズン
  updatedAt: string;            // 最終更新日時（ISO形式）
}
