/** League-relative views of team ratings for the game page (sections 05 and 06). Server-only. */
import "server-only";
import * as data from "./data";
import type { z } from "zod";
import type { FourFactors } from "./schemas";

type FF = z.infer<typeof FourFactors>;

/** Use this season's four factors once a team has 5 games, else last season's (labelled). */
export const MIN_GP_FOR_SEASON_FF = 5;

export type Metric = {
  key: string;
  label: string;
  side: "off" | "def" | "both";
  higherIsBetter: boolean;
  fmt: (v: number) => string;
  get: (abbr: string) => number | null;
};

function ff(abbr: string): { v: FF | null; season: "this" | "last" } {
  const t = data.ratings()?.teams[abbr];
  if (!t) return { v: null, season: "this" };
  if (t.fourFactors && t.fourFactors.gp >= MIN_GP_FOR_SEASON_FF) return { v: t.fourFactors, season: "this" };
  return { v: t.fourFactorsLastSeason ?? null, season: "last" };
}

export function ffSeason(abbr: string): "this" | "last" {
  return ff(abbr).season;
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const one = (v: number) => v.toFixed(1);

export const METRICS: Metric[] = [
  { key: "ortg", label: "Adj. offense (pts/100)", side: "off", higherIsBetter: true, fmt: one, get: (a) => data.ratings()?.teams[a]?.ortg ?? null },
  { key: "efg", label: "Effective FG%", side: "off", higherIsBetter: true, fmt: pct, get: (a) => ff(a).v?.off.efg ?? null },
  { key: "tov", label: "Turnover rate", side: "off", higherIsBetter: false, fmt: pct, get: (a) => ff(a).v?.off.tov ?? null },
  { key: "orb", label: "Off. rebound rate", side: "off", higherIsBetter: true, fmt: pct, get: (a) => ff(a).v?.off.orb ?? null },
  { key: "ftr", label: "Free throw rate", side: "off", higherIsBetter: true, fmt: pct, get: (a) => ff(a).v?.off.ftr ?? null },
  { key: "drtg", label: "Adj. defense (pts/100 allowed)", side: "def", higherIsBetter: false, fmt: one, get: (a) => data.ratings()?.teams[a]?.drtg ?? null },
  { key: "defg", label: "Opp. effective FG%", side: "def", higherIsBetter: false, fmt: pct, get: (a) => ff(a).v?.def.efg ?? null },
  { key: "dtov", label: "Turnovers forced", side: "def", higherIsBetter: true, fmt: pct, get: (a) => ff(a).v?.def.tov ?? null },
  { key: "dorb", label: "Opp. off. rebound rate", side: "def", higherIsBetter: false, fmt: pct, get: (a) => ff(a).v?.def.orb ?? null },
  { key: "dftr", label: "Opp. free throw rate", side: "def", higherIsBetter: false, fmt: pct, get: (a) => ff(a).v?.def.ftr ?? null },
  {
    key: "pace", label: "Pace (poss/48)", side: "both", higherIsBetter: true, fmt: one,
    get: (a) => {
      const r = data.ratings();
      const t = r?.teams[a];
      return r && t ? r.muPace / 2 + t.pace : null;
    },
  },
];

/** Percentile vs the league, 0-100 where 100 = best (or fastest, for pace). */
export function percentile(m: Metric, abbr: string): number | null {
  const all = data.teams().map((t) => m.get(t.abbr)).filter((v): v is number => v !== null);
  const v = m.get(abbr);
  if (v === null || all.length < 2) return null;
  const better = all.filter((x) => (m.higherIsBetter ? x < v : x > v)).length;
  const ties = all.filter((x) => x === v).length - 1;
  return Math.round(((better + ties / 2) / (all.length - 1)) * 100);
}
