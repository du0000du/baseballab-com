import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://baseballab.com',
  trailingSlash: 'always',
  integrations: [
    sitemap({
      changefreq: 'daily',
      priority: 0.7,
      lastmod: new Date(),
      customPages: [],
      filter: (page) => !page.includes('/404'),
      serialize(item) {
        // data pages: daily high priority
        if (/\/(standings|leaders|results|trends)\/$/.test(item.url)) {
          return { ...item, changefreq: 'daily', priority: 0.9 };
        }
        // glossary entries: weekly
        if (item.url.includes('/glossary/') && item.url !== 'https://baseballab.com/glossary/') {
          return { ...item, changefreq: 'weekly', priority: 0.8 };
        }
        // hub pages: daily
        if (/\/(mlb|npb|players|teams|glossary)\/$/.test(item.url)) {
          return { ...item, changefreq: 'daily', priority: 0.85 };
        }
        // NPB/MLB player & team detail pages: primary content (ja + en)
        if (/\/(npb|players|teams)\/[^/]+\/$/.test(item.url)) {
          return { ...item, changefreq: 'daily', priority: 0.8 };
        }
        // root and main hubs
        if (item.url === 'https://baseballab.com/' || item.url === 'https://baseballab.com/en/') {
          return { ...item, changefreq: 'daily', priority: 1.0 };
        }
        return item;
      },
    }),
  ],
});
