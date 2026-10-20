/**
 * Data contracts. Every JSON file under data/ and every card's frontmatter is parsed with these
 * at build time. A bad file fails the build instead of shipping garbage.
 */
import { z } from "zod";

export const UtcIso = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/, "UTC ISO with Z");
export const EtDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
export const GameId = z.string().regex(/^\d{8}-[A-Z]{2,3}-[A-Z]{2,3}$/);
export const Abbr = z.string().regex(/^[A-Z]{2,3}$/);
export const American = z
  .number()
  .int()
  .refine((n) => n <= -100 || n >= 100, "American odds must be <= -100 or >= 100");
const Hex = z.string().regex(/^[0-9a-f]{6}$/i);

export const Team = z.object({
  abbr: Abbr,
  espnId: z.string(),
  name: z.string(),
  shortName: z.string(),
  color: Hex,
  altColor: Hex,
  logoUrl: z.string().url().optional(), // hook for later; no logos today
});
export const Teams = z.array(Team).length(30);

export const GameStatus = z.enum(["scheduled", "live", "final", "postponed", "cancelled"]);
export const Game = z.object({
  id: GameId,
  season: z.string(),
  etDate: EtDate,
  tipUtc: UtcIso,
  away: Abbr,
  home: Abbr,
  espnId: z.string(),
  oddsEventId: z.string().nullable(),
  status: GameStatus,
  neutralSite: z.boolean(),
  venue: z.string().nullable(),
  venueKey: z.string().nullable(),
  rescheduledFrom: EtDate.optional(),
});
export const Schedule = z.object({
  season: z.string(),
  pulledAt: UtcIso,
  source: z.string(),
  games: z.array(Game),
});

export const BookLine = z.object({
  book: z.string(),
  spreadHome: z.number().nullable(),
  spreadHomePrice: American.nullable(),
  spreadAwayPrice: American.nullable(),
  total: z.number().nullable(),
  overPrice: American.nullable(),
  underPrice: American.nullable(),
  mlHome: American.nullable(),
  mlAway: American.nullable(),
  lastUpdate: UtcIso,
});
export const Consensus = z.object({
  spreadHome: z.number().nullable(),
  total: z.number().nullable(),
  nBooks: z.number().int(),
});
export const GameLines = z.object({
  gameId: GameId,
  oddsEventId: z.string().nullable(),
  books: z.array(BookLine).min(1),
  consensus: Consensus,
});
export const LineSnapshot = z.object({
  takenAt: UtcIso,
  provider: z.string(),
  games: z.array(GameLines),
});
export const CurrentLine = GameLines.extend({ takenAt: UtcIso, provider: z.string(), snapshot: z.string() });
export const CurrentLines = z.record(GameId, CurrentLine);
export const FirstSeen = GameLines.extend({ seenAt: UtcIso, provider: z.string(), snapshot: z.string() });

export const ModelPick = z.object({
  gameId: GameId,
  lockedAt: UtcIso,
  modelVersion: z.string(),
  marketSpreadHome: z.number().nullable(),
  marketTotal: z.number().nullable(),
  price: American,
  side: z.enum(["home", "away", "none"]),
  line: z.number().nullable(),
  edge: z.number().nullable(), // model spread minus market spread, home perspective (points)
  modelSpreadHome: z.number().nullable(),
  modelTotal: z.number().nullable(),
  reason: z.string().nullable(),
});

export const ContributionKey = z.enum(["offense", "defense", "pace", "home", "rest_travel", "injuries"]);
export const Projection = z.object({
  gameId: GameId,
  generatedAt: UtcIso,
  ratingsAsOf: UtcIso,
  modelVersion: z.string(),
  awayPts: z.number(),
  homePts: z.number(),
  margin: z.number(), // home minus away
  spreadHome: z.number(), // = -margin, betting convention
  total: z.number(),
  pace: z.number(),
  homeWinProb: z.number().min(0).max(1),
  fairMlHome: American,
  fairMlAway: American,
  contributions: z.array(z.object({ key: ContributionKey, pts: z.number() })).length(6), // sum to margin
  sample: z.object({ awayGP: z.number().int(), homeGP: z.number().int(), priorWeight: z.number() }),
  flags: z.array(z.string()),
});
export const ProjectionDay = z.object({ etDate: EtDate, games: z.array(Projection) });

const TeamBox = z.object({
  fgm: z.number(), fga: z.number(), fg3m: z.number(), fg3a: z.number(), ftm: z.number(), fta: z.number(),
  oreb: z.number(), dreb: z.number(), ast: z.number(), stl: z.number(), blk: z.number(), tov: z.number(),
  pf: z.number(),
});
export const PlayerBox = z.object({
  name: z.string(), espnId: z.string(), team: Abbr, starter: z.boolean(), dnp: z.boolean(),
  dnpReason: z.string().nullable(), min: z.number(), pts: z.number(), reb: z.number(), ast: z.number(),
  fg3m: z.number(), fgm: z.number(), fga: z.number(), fg3a: z.number(), ftm: z.number(), fta: z.number(),
  oreb: z.number(), dreb: z.number(), stl: z.number(), blk: z.number(), tov: z.number(), pf: z.number(),
  pm: z.number(),
});
export const Result = z.object({
  gameId: GameId,
  status: z.enum(["final", "postponed", "cancelled", "pending"]),
  awayPts: z.number().int().nullable(),
  homePts: z.number().int().nullable(),
  periods: z.number().int().nullable(),
  finalizedAt: UtcIso,
  box: z.object({ home: TeamBox, away: TeamBox }).nullable(),
  players: z.array(PlayerBox),
});

export const TeamRating = z.object({
  off: z.number(), def: z.number(), pace: z.number(), ortg: z.number(), drtg: z.number(), net: z.number(),
  gp: z.number().int(), priorWeight: z.number(), w: z.number().int(), l: z.number().int(),
});
export const Ratings = z.object({
  season: z.string(),
  asOf: UtcIso,
  etDate: EtDate,
  modelVersion: z.string(),
  gamesUsed: z.number().int(),
  mu: z.number(),
  muPace: z.number(),
  k: z.number(),
  sigma: z.number(),
  betas: z.record(z.string(), z.number()),
  teams: z.record(Abbr, TeamRating),
});

export const ModelParams = z.object({
  modelVersion: z.string(),
  fittedAt: UtcIso,
  fitSeason: z.string(),
  priorSeasonForFit: z.string(),
  k: z.number(),
  regression: z.number(),
  sigma: z.number(),
  fitSeasonMeanError: z.number(),
  betas: z.record(z.string(), z.number()),
  betasFrom: z.array(z.string()),
  grid: z.array(z.object({ regression: z.number(), k: z.number(), marginRmse: z.number(), n: z.number() })),
  note: z.string(),
});

export const Outcome = z.enum(["win", "loss", "push", "void", "pending"]);
export const Grade = z.object({
  source: z.enum(["model", "card"]),
  gameId: GameId,
  etDate: EtDate,
  pickId: z.string(),
  market: z.enum(["spread", "total", "moneyline", "prop"]),
  side: z.string(),
  player: z.string().nullable().optional(),
  stat: z.string().nullable().optional(),
  line: z.number().nullable(),
  price: American,
  units: z.number(),
  confidence: z.number().int().optional(),
  result: Outcome,
  profitU: z.number(),
  edge: z.number().nullable(),
  closingLine: z.number().nullable(),
  clvPts: z.number().nullable(),
  finalScore: z.string().nullable(),
  amendment: z.string().nullable().optional(),
});
export const Summary = z.object({
  w: z.number().int(), l: z.number().int(), p: z.number().int(), pending: z.number().int(),
  units: z.number(), risked: z.number(), roi: z.number().nullable(),
  clvPtsAvg: z.number().nullable(), beatClosePct: z.number().nullable(), clvN: z.number().int(),
});
export const Grades = z.object({
  generatedAt: UtcIso,
  grades: z.array(Grade),
  summary: z.record(z.string(), Summary),
});

export const PipelineState = z.object({
  days: z.record(EtDate, z.record(z.string(), z.unknown())),
  lastUpdatedAt: UtcIso.nullable(),
});

// ---- My Card (content/cards/YYYY-MM-DD.mdx frontmatter) ----
export const CardPick = z
  .object({
    id: z.coerce.string(),
    game: GameId,
    market: z.enum(["spread", "total", "moneyline", "prop"]),
    side: z.string(), // team abbr for spread/moneyline, "over"/"under" for total/prop
    player: z.string().optional(),
    stat: z.enum(["pts", "reb", "ast", "fg3m", "pra"]).optional(),
    line: z.number().nullable().optional(),
    odds: American,
    units: z.number().positive(),
    confidence: z.number().int().min(1).max(5),
    why: z.string().optional(),
  })
  .superRefine((p, ctx) => {
    if (p.market !== "moneyline" && (p.line === undefined || p.line === null))
      ctx.addIssue({ code: "custom", message: `${p.market} pick needs a line` });
    if ((p.market === "total" || p.market === "prop") && !["over", "under"].includes(p.side))
      ctx.addIssue({ code: "custom", message: "total/prop side must be over or under" });
    if (p.market === "prop" && (!p.player || !p.stat))
      ctx.addIssue({ code: "custom", message: "prop pick needs player and stat" });
  });
export const CardFrontmatter = z.object({
  // YAML parses an unquoted 2026-10-20 as a Date (midnight UTC); normalise back to the ET date string.
  date: z.preprocess((v) => (v instanceof Date ? v.toISOString().slice(0, 10) : v), EtDate),
  picks: z.array(CardPick).default([]),
  amendments: z
    .array(z.object({ at: UtcIso, pickId: z.coerce.string(), note: z.string().min(1) }))
    .default([]),
});

export type TGame = z.infer<typeof Game>;
export type TTeam = z.infer<typeof Team>;
export type TProjection = z.infer<typeof Projection>;
export type TModelPick = z.infer<typeof ModelPick>;
export type TCurrentLine = z.infer<typeof CurrentLine>;
export type TFirstSeen = z.infer<typeof FirstSeen>;
export type TGrade = z.infer<typeof Grade>;
export type TSummary = z.infer<typeof Summary>;
export type TRatings = z.infer<typeof Ratings>;
export type TCardPick = z.infer<typeof CardPick>;
export type TCard = z.infer<typeof CardFrontmatter>;
export type TResult = z.infer<typeof Result>;
