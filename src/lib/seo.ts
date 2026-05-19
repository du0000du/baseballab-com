// src/lib/seo.ts
// TASK-010: SEO ユーティリティ — JSON-LD スキーマ生成

export interface PersonSchemaOptions {
  name: string;
  url: string;
  birthDate?: string | null;
  birthPlace?: string;
  nationality?: string;
  jobTitle?: string; // e.g. "プロ野球選手"
}

/**
 * Person JSON-LD スキーマを生成する
 */
export function buildPersonSchema(opts: PersonSchemaOptions): Record<string, unknown> {
  const schema: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'Person',
    name: opts.name,
    url: opts.url,
    jobTitle: opts.jobTitle ?? 'プロ野球選手',
    sport: 'Baseball',
  };

  if (opts.birthDate) {
    schema.birthDate = opts.birthDate;
  }
  if (opts.birthPlace) {
    schema.birthPlace = {
      '@type': 'Place',
      name: opts.birthPlace,
    };
  }
  if (opts.nationality) {
    schema.nationality = {
      '@type': 'Country',
      name: opts.nationality,
    };
  }

  return schema;
}

/**
 * WebPage JSON-LD スキーマを生成する（汎用）
 */
export function buildWebPageSchema(opts: {
  name: string;
  url: string;
  description?: string;
}): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: opts.name,
    url: opts.url,
    ...(opts.description ? { description: opts.description } : {}),
  };
}
