/**
 * prebuild: validate every JSON file under data/ that has a schema, plus every card's frontmatter.
 * Exits non-zero on the first bad file so a broken pull can never ship.
 */
import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { CardFrontmatter } from "../src/lib/schemas";
import { VALIDATORS } from "../src/lib/validators";

const ROOT = process.cwd();
const DATA = path.join(ROOT, "data");
const SKIP = [/^history\//, /^logs\/.*\.jsonl$/, /^model\/priors-/];

function walk(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.name.startsWith(".")) return [];
    return e.isDirectory() ? walk(p) : [p];
  });
}

let checked = 0;
const errors: string[] = [];
for (const file of walk(DATA)) {
  const rel = path.relative(DATA, file).split(path.sep).join("/");
  if (!rel.endsWith(".json") || SKIP.some((r) => r.test(rel))) continue;
  const v = VALIDATORS.find((x) => x.pattern.test(rel));
  if (!v) {
    errors.push(`data/${rel}: no schema registered for this path`);
    continue;
  }
  const r = v.schema.safeParse(JSON.parse(fs.readFileSync(file, "utf8")));
  if (!r.success) errors.push(`data/${rel}:\n${r.error.message}`);
  checked++;
}

const cardsDir = path.join(ROOT, "content", "cards");
for (const f of fs.existsSync(cardsDir) ? fs.readdirSync(cardsDir) : []) {
  if (!f.endsWith(".mdx")) continue;
  if (!/^\d{4}-\d{2}-\d{2}\.mdx$/.test(f)) {
    errors.push(`content/cards/${f}: filename must be YYYY-MM-DD.mdx`);
    continue;
  }
  const r = CardFrontmatter.safeParse(matter(fs.readFileSync(path.join(cardsDir, f), "utf8")).data);
  if (!r.success) errors.push(`content/cards/${f}:\n${r.error.message}`);
  else if (r.data.date !== f.replace(".mdx", "")) errors.push(`content/cards/${f}: date does not match filename`);
  checked++;
}

if (errors.length) {
  console.error(`✗ ${errors.length} invalid file(s):\n\n${errors.join("\n\n")}`);
  process.exit(1);
}
console.log(`✓ validated ${checked} data and card files`);
