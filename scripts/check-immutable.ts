/**
 * CI guard. Fails if a push:
 *   1. modifies, renames or deletes anything under data/lines/first-seen/ or data/picks/model/
 *   2. edits a My Card pick for a game that had already tipped, without adding an amendment note
 *   3. adds a pick for a game that had already tipped, or removes one
 *   4. edits the card's written takes (the MDX body) after the slate's first tip without an
 *      amendment whose pickId is "takes"
 *
 * Usage: tsx scripts/check-immutable.ts <base-sha> <head-sha>
 * "Tipped" is judged against the head commit's committer time.
 */
import { execFileSync } from "node:child_process";
import matter from "gray-matter";
import { CardFrontmatter, Schedule, type TCard, type TCardPick } from "../src/lib/schemas";
import siteJson from "../config/site.json";

const EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904";
const LOCKED_DIRS = ["data/lines/first-seen/", "data/picks/model/"];

function git(...args: string[]): string {
  return execFileSync("git", args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
}

function show(rev: string, file: string): string | null {
  try {
    return git("show", `${rev}:${file}`);
  } catch {
    return null;
  }
}

type ParsedCard = TCard & { body: string };

function parseCard(text: string | null): ParsedCard | null {
  if (text === null) return null;
  const m = matter(text);
  return { ...CardFrontmatter.parse(m.data), body: m.content.trim() };
}

const same = (a: TCardPick, b: TCardPick) => JSON.stringify(a) === JSON.stringify(b);

export function checkCardChange(
  oldCard: ParsedCard | null,
  newCard: ParsedCard | null,
  tipOf: (gameId: string) => Date | null,
  at: Date,
  file: string,
  firstTipOfDay: Date | null = null,
): string[] {
  const errs: string[] = [];
  const oldPicks = new Map((oldCard?.picks ?? []).map((p) => [p.id, p]));
  const newPicks = new Map((newCard?.picks ?? []).map((p) => [p.id, p]));
  const amendCount = (c: TCard | null, id: string) => (c?.amendments ?? []).filter((a) => a.pickId === id).length;
  const started = (gameId: string) => {
    const t = tipOf(gameId);
    return t !== null && t <= at;
  };
  for (const id of new Set([...oldPicks.keys(), ...newPicks.keys()])) {
    const o = oldPicks.get(id);
    const n = newPicks.get(id);
    if (n && tipOf(n.game) === null) errs.push(`${file}: pick ${id} references unknown game ${n.game}`);
    if (o && !n && started(o.game)) errs.push(`${file}: pick ${id} removed after ${o.game} tipped`);
    if (!o && n && started(n.game)) errs.push(`${file}: pick ${id} added after ${n.game} tipped`);
    if (o && n && !same(o, n) && (started(o.game) || started(n.game))) {
      if (amendCount(newCard, id) <= amendCount(oldCard, id))
        errs.push(`${file}: pick ${id} changed after tip without a new amendment note`);
    }
  }
  if (oldCard && newCard && oldCard.body !== newCard.body && firstTipOfDay && firstTipOfDay <= at) {
    if (amendCount(newCard, "takes") <= amendCount(oldCard, "takes"))
      errs.push(`${file}: takes edited after the first tip without an amendment (pickId: takes)`);
  }
  return errs;
}

function main() {
  const [baseArg, head = "HEAD"] = process.argv.slice(2);
  const base = !baseArg || /^0+$/.test(baseArg) ? EMPTY_TREE : baseArg;
  const errors: string[] = [];

  const diff = git("diff", "--name-status", "--no-renames", base, head).trim();
  const changes = diff ? diff.split("\n").map((l) => l.split("\t") as [string, string]) : [];

  for (const [status, file] of changes) {
    if (LOCKED_DIRS.some((d) => file.startsWith(d)) && status !== "A")
      errors.push(`${file}: write-once file was ${status === "D" ? "deleted" : "modified"}`);
  }

  const cardChanges = changes.filter(([, f]) => /^content\/cards\/\d{4}-\d{2}-\d{2}\.mdx$/.test(f));
  if (cardChanges.length) {
    const at = new Date(git("log", "-1", "--format=%cI", head).trim());
    const schedText = show(head, `data/schedule/${siteJson.season}.json`);
    const games = schedText ? Schedule.parse(JSON.parse(schedText)).games : [];
    const tips = new Map(games.map((g) => [g.id, new Date(g.tipUtc)]));
    const tipOf = (id: string) => tips.get(id) ?? null;
    for (const [, file] of cardChanges) {
      const before = base === EMPTY_TREE ? null : parseCard(show(base, file));
      const after = parseCard(show(head, file));
      const day = file.slice(-14, -4);
      const dayTips = games.filter((g) => g.etDate === day).map((g) => new Date(g.tipUtc).getTime());
      const first = dayTips.length ? new Date(Math.min(...dayTips)) : null;
      errors.push(...checkCardChange(before, after, tipOf, at, file, first));
    }
  }

  if (errors.length) {
    console.error(`✗ immutability check failed:\n  ${errors.join("\n  ")}`);
    process.exit(1);
  }
  console.log(`✓ immutability check passed (${changes.length} changed files, ${cardChanges.length} cards)`);
}

if (process.argv[1]?.endsWith("check-immutable.ts")) main();
