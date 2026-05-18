// Baseballab — チームデータ型定義
// TASK-002: TypeScript型定義

export interface TeamStats {
  wins: number;          // 勝利
  losses: number;        // 敗戦
  winPct: number;        // 勝率
  runsScored: number;    // 得点
  runsAllowed: number;   // 失点
  teamAvg: number;       // チーム打率
  teamEra: number;       // チーム防御率
  teamOps: number;       // チームOPS
}

export interface TeamData {
  id: string;            // slug（例: los-angeles-dodgers）
  name: string;          // チーム正式名（英語）
  nameJa: string;        // チーム名（日本語）
  abbreviation: string;  // 略称（例: LAD）
  league: 'MLB' | 'NPB'; // リーグ
  division: string;      // 地区（例: NL West）
  city: string;          // 本拠地都市
  stadium: string;       // 球場名
  founded: number;       // 創設年
  stats: TeamStats;      // チーム成績
  season: number;        // 対象シーズン
  updatedAt: string;     // 最終更新日時（ISO形式）
}
