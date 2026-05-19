// src/lib/affiliate.ts
// TASK-016: アフィリエイトリンク生成ユーティリティ

export interface AffiliateLink {
  label: string;
  url: string;
  pr: boolean;
  description?: string;
}

export function buildAmazonUrl(asin: string, tag: string): string {
  return `https://www.amazon.co.jp/dp/${asin}?tag=${tag}`;
}

export function buildRakutenUrl(affiliateId: string, itemUrl: string): string {
  return `https://hb.afl.rakuten.co.jp/hgc/${affiliateId}/?pc=${encodeURIComponent(itemUrl)}`;
}

export function buildAmazonLinks(
  items: Array<{ label: string; asin: string; description?: string }>,
  tag: string
): AffiliateLink[] {
  return items.map(item => ({
    label: item.label,
    url: buildAmazonUrl(item.asin, tag),
    pr: true,
    description: item.description,
  }));
}
