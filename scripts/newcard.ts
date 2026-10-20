/**
 * npm run newcard            -> scaffolds content/cards/<today ET>.mdx
 * npm run newcard 2026-10-22 -> a specific ET game day
 *
 * Prefills the slate (model line, market line, first-seen line, edge, rest flags) and live injury
 * status from ESPN inside an MDX comment, so it helps you write but never renders on the site.
 * Refuses to overwrite an existing card.
 */
import fs from "node:fs";
import path from "node:path";
import {
  CurrentLines,
  FirstSeen,
  ModelPick,
  ProjectionDay,
  Schedule,
  type TGame,
} from "../src/lib/schemas";
import { formatDayLong, formatTip, formatUpdated, todayEt } from "../src/lib/time";
import siteJson from "../config/site.json";

const ROOT = process.cwd();
const DATA = path.join(ROOT, "data");

function readJson<T>(rel: string, parse: (x: unknown) => T): T | null {
  const p = path.join(DATA, rel);
  return fs.existsSync(p) ? parse(JSON.parse(fs.readFileSync(p, "utf8"))) : null;
}

function line(spreadHome: number | null | undefined, g: TGame): string {
  if (spreadHome === null || spreadHome === undefined) return "—";
  if (spreadHome === 0) return "PK";
  return `${spreadHome < 0 ? g.home : g.away} -${Math.abs(spreadHome)}`;
}

type Inj = { team: string; name: string; status: string; detail: string };

async function injuries(): Promise<Inj[] | null> {
  try {
    const r = await fetch("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries", {
      headers: { "User-Agent": "SauceSheet/1.0 (newcard)" },
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = (await r.json()) as {
      injuries: { injuries: { status: string; details?: { type?: string; detail?: string }; athlete: { displayName: string; team?: { abbreviation?: string } } }[] }[];
    };
    const norm: Record<string, string> = { GS: "GSW", NO: "NOP", NY: "NYK", SA: "SAS", UTAH: "UTA", WSH: "WAS" };
    return d.injuries.flatMap((t) =>
      t.injuries.map((i) => {
        const ab = i.athlete.team?.abbreviation ?? "";
        return {
          team: norm[ab] ?? ab,
          name: i.athlete.displayName,
          status: i.status,
          detail: [i.details?.type, i.details?.detail].filter(Boolean).join(" "),
        };
      }),
    );
  } catch (e) {
    console.warn(`! injuries unavailable: ${(e as Error).message}`);
    return null;
  }
}

async function main() {
  const day = process.argv[2] ?? todayEt();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new Error(`bad date ${day}; use YYYY-MM-DD`);
  const out = path.join(ROOT, "content", "cards", `${day}.mdx`);
  if (fs.existsSync(out)) {
    console.error(`! ${path.relative(ROOT, out)} already exists. Not overwriting.`);
    process.exit(1);
  }

  const sched = readJson(`schedule/${siteJson.season}.json`, (x) => Schedule.parse(x));
  const games = (sched?.games ?? [])
    .filter((g) => g.etDate === day && g.status !== "cancelled")
    .sort((a, b) => a.tipUtc.localeCompare(b.tipUtc));
  const proj = readJson(`projections/${day}.json`, (x) => ProjectionDay.parse(x))?.games ?? [];
  const cur = readJson("lines/current.json", (x) => CurrentLines.parse(x)) ?? {};
  const inj = await injuries();

  const blocks = games.map((g) => {
    const p = proj.find((x) => x.gameId === g.id);
    const fs1 = readJson(`lines/first-seen/${g.id}.json`, (x) => FirstSeen.parse(x));
    const pick = readJson(`picks/model/${g.id}.json`, (x) => ModelPick.parse(x));
    const c = cur[g.id];
    const market = c?.consensus.spreadHome ?? fs1?.consensus.spreadHome ?? null;
    const edge = p && market !== null ? Math.abs(p.spreadHome - market).toFixed(1) : "—";
    const pickTxt =
      pick && pick.side !== "none" && pick.line !== null
        ? `${g[pick.side]} ${pick.line > 0 ? "+" : ""}${pick.line} (locked, edge ${Math.abs(pick.edge ?? 0).toFixed(1)})`
        : "not locked yet";
    const injFor = (t: string) =>
      inj === null
        ? "unavailable"
        : inj.filter((i) => i.team === t).map((i) => `${i.name} (${i.status}${i.detail ? `, ${i.detail}` : ""})`).join("; ") || "none listed";
    return [
      `${formatTip(g.tipUtc).padEnd(11)} ${g.away} at ${g.home}    game: ${g.id}`,
      `  market   ${line(market, g)} · total ${c?.consensus.total ?? fs1?.consensus.total ?? "—"}${fs1 ? ` · first seen ${line(fs1.consensus.spreadHome, g)}` : ""}`,
      `  model    ${p ? `${line(p.spreadHome, g)} · total ${p.total} · ${g.away} ${p.awayPts}-${p.homePts} ${g.home}` : "no projection yet"}`,
      `  gap      ${edge} pts · pick ${pickTxt}`,
      `  spots    ${p?.flags.length ? p.flags.join(", ") : "none"}`,
      `  inj ${g.away.padEnd(4)} ${injFor(g.away)}`,
      `  inj ${g.home.padEnd(4)} ${injFor(g.home)}`,
    ].join("\n");
  });

  const example = games[0];
  const exampleSide = example ? example.away : "BOS";
  const text = `---
date: ${day}
# One block per play. Delete the leading "# " to activate. Units = amount risked.
# market: spread | total | moneyline | prop
# side: team abbr for spread/moneyline, over/under for total/prop
# prop picks also need  player: "Full Name"  and  stat: pts | reb | ast | fg3m | pra
picks: []
# picks:
#   - id: 1
#     game: ${example?.id ?? "YYYYMMDD-AWY-HOM"}
#     market: spread
#     side: ${exampleSide}
#     line: -1.5
#     odds: -110
#     units: 1
#     confidence: 3
#     why: One line on why.
amendments: []
---

{/*
SLATE · ${formatDayLong(day)} · ${games.length} games · generated ${formatUpdated(new Date().toISOString().replace(/\.\d{3}Z$/, "Z")).replace("UPDATED ", "")}
This block is a comment: it helps you write and is not shown on the site.

${blocks.join("\n\n") || "No games found for this date. Is the schedule pulled?"}
*/}

Write your takes here. Everything below the comment is public.
`;
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, text);
  console.log(`✓ wrote ${path.relative(ROOT, out)} (${games.length} games${inj === null ? ", injuries unavailable" : ""})`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
