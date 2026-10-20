import type { Metadata } from "next";
import { RecordTable, type RecordRow } from "@/components/RecordTable";
import { Note, PageTitle, StatTile } from "@/components/ui";
import { EDGE_TIERS } from "@/lib/board";
import * as data from "@/lib/data";
import { fmtPct, fmtSigned, fmtSpread } from "@/lib/format";
import { formatDayShort } from "@/lib/time";

export const metadata: Metadata = { title: "Model record" };

export default function RecordPage() {
  const grades = data.modelGrades();
  const rows: RecordRow[] = (grades?.grades ?? [])
    .slice()
    .sort((a, b) => b.etDate.localeCompare(a.etDate) || a.gameId.localeCompare(b.gameId))
    .map((g) => {
      const game = data.game(g.gameId);
      return {
        gameId: g.gameId,
        dateLabel: formatDayShort(g.etDate),
        matchup: game ? `${game.away} at ${game.home}` : g.gameId,
        pick: `${g.side} ${fmtSpread(g.line)}`,
        edge: g.edge,
        line: g.line,
        closingLine: g.closingLine,
        clvPts: g.clvPts,
        finalScore: g.finalScore,
        result: g.result,
        profitU: g.profitU,
      };
    });
  const tiers = [{ key: "all", label: "All picks", min: 0 }, ...EDGE_TIERS.map((t) => ({ key: `e${t}`, label: `Edge ${t}+`, min: t }))];
  const all = grades?.summary.all;

  return (
    <div>
      <PageTitle eyebrow="NBA" title="Model record">
        Every finished game where the model had a projection and a market line, graded against the first line the
        pipeline ever saw. Lines are never re-priced as the market moves. Tap a tile to filter by edge size.
      </PageTitle>
      <RecordTable rows={rows} tiers={tiers} />
      {all && all.clvN > 0 && (
        <div className="grid grid-cols-2 gap-3 mt-6 max-w-md">
          <StatTile label="Avg CLV" value={fmtSigned(all.clvPtsAvg)} sub={`points vs close · n=${all.clvN}`} />
          <StatTile label="Beat the close" value={fmtPct(all.beatClosePct, 0)} sub="of graded picks" />
        </div>
      )}
      <div className="mt-8 space-y-2">
        <Note>Break-even at -110 is 52.4%. Every model pick is graded at -110, win +0.909u, loss -1u, push 0.</Note>
        <Note>
          At these sample sizes, any record is still noise. A few hundred picks are needed before a win rate says much
          about skill. The record is kept to be counted honestly, not to prove anything.
        </Note>
        <Note>
          Postponed, cancelled, or rescheduled games are void. A pick is never edited after it is locked.
        </Note>
      </div>
    </div>
  );
}
