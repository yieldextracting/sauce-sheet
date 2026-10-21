import type { Metadata } from "next";
import Link from "next/link";
import { Note, PageTitle } from "@/components/ui";
import { lineLabel, slate, type BoardGame } from "@/lib/board";
import * as data from "@/lib/data";
import { fmtPts, fmtSpread } from "@/lib/format";
import { formatDayShort, formatTip } from "@/lib/time";

export const metadata: Metadata = { title: "Biggest gaps" };

const DAYS_AHEAD = 3;
const HIGHLIGHT = 3;

function upcoming(): BoardGame[] {
  const start = data.defaultBoardDay();
  if (!start) return [];
  const days = data.boardDays().filter((d) => d >= start).slice(0, DAYS_AHEAD);
  return days.flatMap((d) => slate(d)).filter((g) => g.gap !== null);
}

export default function GapsPage() {
  const games = upcoming().sort((a, b) => (b.gap ?? 0) - (a.gap ?? 0));
  return (
    <div>
      <PageTitle eyebrow="NBA" title="Biggest disagreements">
        Upcoming games ranked by how far the model is from the market, largest first. Games {HIGHLIGHT}+ points apart
        are marked. A large gap is a question worth asking, not a signal to follow.
      </PageTitle>
      {games.length === 0 ? (
        <p className="text-muted">No lines stored for upcoming games yet.</p>
      ) : (
        <ol className="divide-y divide-rule border-y border-rule">
          {games.map((g) => {
            const big = (g.gap ?? 0) >= HIGHLIGHT;
            const inj = g.projection?.contributions.find((c) => c.key === "injuries")?.pts ?? 0;
            return (
              <li key={g.game.id} className="py-3 grid grid-cols-[3.5rem_1fr] gap-3 items-start">
                <span className={`num text-2xl font-semibold ${big ? "text-accent" : ""}`}>{fmtPts(g.gap)}</span>
                <div className="min-w-0">
                  <Link href={`/nba/game/${g.game.id}`} className="font-medium hover:underline">
                    {g.game.away} at {g.game.home}
                  </Link>
                  <span className="text-sm text-muted num ml-2">
                    {formatDayShort(g.game.etDate)} · {formatTip(g.game.tipUtc)}
                  </span>
                  <p className="text-sm num mt-0.5">
                    Market {lineLabel(g.marketSpreadHome, g.game.away, g.game.home)} · model{" "}
                    {lineLabel(g.projection?.spreadHome, g.game.away, g.game.home)}
                    {g.pick && g.pick.side !== "none" && g.pickTeam && (
                      <span className="text-muted">
                        {" "}· locked {g.pickTeam} {fmtSpread(g.pick.line)}, edge at lock {fmtPts(g.lockedEdge)}
                      </span>
                    )}
                  </p>
                  {Math.abs(inj) >= 1 && (
                    <p className="text-xs text-muted mt-0.5 num">
                      Injuries move the model {fmtPts(Math.abs(inj))} pts toward {inj > 0 ? g.game.home : g.game.away}.
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      <div className="mt-6 space-y-2">
        <Note>
          Gap = points between the current model line and the current market consensus. The record grades the pick
          locked at first sight, against that first line, so its edge at lock can differ from today&apos;s gap.
        </Note>
        <Note>Early in the season the model leans on last year&apos;s ratings and knows nothing about offseason moves, so big gaps are expected and usually wrong.</Note>
      </div>
    </div>
  );
}
