/** Assembles what the board and game pages show for each game. Server-only. */
import "server-only";
import * as data from "./data";
import type { TGame, TGrade, TModelPick, TProjection, TTeam } from "./schemas";
import { record } from "./format";
import modelCfg from "../../config/model.json";

export const EDGE_TIERS: number[] = modelCfg.edgeTiers;
export const SAMPLE_BADGE_GAMES: number = modelCfg.sampleBadgeGames;

export type BoardGame = {
  game: TGame;
  away: TTeam;
  home: TTeam;
  awayRecord: string;
  homeRecord: string;
  projection: TProjection | null;
  marketSpreadHome: number | null; // current consensus
  marketTotal: number | null;
  marketTakenAt: string | null;
  marketProvider: string | null;
  firstSeenSpreadHome: number | null;
  pick: TModelPick | null;
  pickTeam: string | null; // abbr of the locked pick side
  gap: number | null; // current |model - market| in points (what the gaps page and strip rank by)
  lockedEdge: number | null; // |edge| at lock, which is what the record grades
  grade: TGrade | null;
  result: { awayPts: number; homePts: number } | null;
};

/** "DET -1.5" from a home-perspective spread. */
export function lineLabel(spreadHome: number | null | undefined, away: string, home: string): string {
  if (spreadHome === null || spreadHome === undefined) return "—";
  if (spreadHome === 0) return "PK";
  const fav = spreadHome < 0 ? home : away;
  const n = Math.abs(spreadHome);
  return `${fav} -${Number.isInteger(n) ? n : n.toFixed(1)}`;
}

export function boardGame(game: TGame): BoardGame {
  const tm = data.teamMap();
  const ratings = data.ratings();
  const cur = data.currentLines()[game.id] ?? null;
  const fs = data.firstSeen(game.id);
  const pick = data.modelPick(game.id);
  const projection = data.projection(game.id, game.etDate);
  const res = data.result(game.id);
  const grade = (data.modelGrades()?.grades ?? []).find((g) => g.gameId === game.id) ?? null;
  const market = cur?.consensus.spreadHome ?? fs?.consensus.spreadHome ?? null;
  const gap = projection && market !== null ? Math.abs(projection.spreadHome - market) : null;
  const lockedEdge = pick && pick.edge !== null ? Math.abs(pick.edge) : null;
  const rec = (abbr: string) => {
    const t = ratings?.teams[abbr];
    return t ? record(t.w, t.l) : "0-0";
  };
  return {
    game,
    away: tm[game.away],
    home: tm[game.home],
    awayRecord: rec(game.away),
    homeRecord: rec(game.home),
    projection,
    marketSpreadHome: market,
    marketTotal: cur?.consensus.total ?? fs?.consensus.total ?? null,
    marketTakenAt: cur?.takenAt ?? fs?.seenAt ?? null,
    marketProvider: cur?.provider ?? fs?.provider ?? null,
    firstSeenSpreadHome: fs?.consensus.spreadHome ?? null,
    pick,
    pickTeam: pick && pick.side !== "none" ? game[pick.side] : null,
    gap: gap === null ? null : Math.round(gap * 10) / 10,
    lockedEdge,
    grade,
    result: res && res.status === "final" && res.awayPts !== null && res.homePts !== null
      ? { awayPts: res.awayPts, homePts: res.homePts }
      : null,
  };
}

export function slate(day: string): BoardGame[] {
  return data.gamesOn(day).filter((g) => g.status !== "cancelled").map(boardGame);
}

export function slateRecord(games: BoardGame[]) {
  const g = games.map((x) => x.grade).filter((x): x is TGrade => !!x);
  const done = g.filter((x) => ["win", "loss", "push"].includes(x.result));
  return {
    w: done.filter((x) => x.result === "win").length,
    l: done.filter((x) => x.result === "loss").length,
    p: done.filter((x) => x.result === "push").length,
    units: done.reduce((s, x) => s + x.profitU, 0),
    n: done.length,
  };
}
