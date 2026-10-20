/** My Card: content/cards/YYYY-MM-DD.mdx. Frontmatter is validated; the body is rendered as MDX. */
import "server-only";
import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { CardFrontmatter, type TCard } from "./schemas";

const DIR = path.join(process.cwd(), "content", "cards");

export type CardFile = TCard & { body: string; file: string };

let all: CardFile[] | null = null;

export function cards(): CardFile[] {
  if (all) return all;
  if (!fs.existsSync(DIR)) return (all = []);
  all = fs
    .readdirSync(DIR)
    .filter((f) => /^\d{4}-\d{2}-\d{2}\.mdx$/.test(f))
    .sort()
    .map((f) => {
      const raw = fs.readFileSync(path.join(DIR, f), "utf8");
      const { data, content } = matter(raw);
      const parsed = CardFrontmatter.safeParse(data);
      if (!parsed.success) throw new Error(`content/cards/${f} frontmatter invalid:\n${parsed.error.message}`);
      if (parsed.data.date !== f.replace(".mdx", ""))
        throw new Error(`content/cards/${f}: frontmatter date ${parsed.data.date} does not match filename`);
      return { ...parsed.data, body: content.trim(), file: f };
    });
  return all;
}

export function cardFor(day: string): CardFile | null {
  return cards().find((c) => c.date === day) ?? null;
}
