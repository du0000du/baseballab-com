import { defineCollection, z } from 'astro:content';

const glossary = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    abbr: z.string().optional(),
    category: z.enum(['batting', 'pitching', 'fielding', 'baserunning', 'general']),
    difficulty: z.enum(['basic', 'intermediate', 'advanced']),
    atomicAnswer: z.string(),
    relatedTerms: z.array(z.string()).optional(),
    publishedAt: z.string(),
  }),
});

export const collections = { glossary };
