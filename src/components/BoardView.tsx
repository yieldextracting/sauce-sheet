import Link from "next/link";
import { slate, slateRecord, lineLabel } from "@/lib/board";
import { cardFor } from "@/lib/cards";
import * as data from "@/lib/data";
import { fmtPts, fmtUnits, record } from "@/lib/format";
import { formatDayLong, formatDayShort, formatUpdated } from "@/lib/time";
import { GameCard } from "./GameCard";
import { MyCard } from "./MyCard";
import { StatTile } from "./ui";

export function BoardView({ day }: { day: string }) {
  const games = slate(day);
  const card = cardFor(day);
  const rec = slateRecord(games);
  const season = data.modelGrades()?.summary.all;
  const disagree = games.filter((g) => (g.gap ?? 0) >= 3).length;
  const biggest = [...games].filter((g) => g.gap !== null).sort((a, b) => (b.gap ?? 0) - (a.gap ?? 0))[0];
  const state = data.pipelineState();
  const days = data.boardDays();
  const i = days.indexOf(day);
  const prev = i > 0 ? days[i - 1] : null;
  const next = i >= 0 && i < days.length - 1 ? days[i + 1] : null;

  return (
    <div>
      <div className="pt-8 pb-2 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow mb-1">NBA board</p>
          <h1 className="font-serif text-3xl sm:text-4xl font-semibold tracking-tight">{formatDayLong(day)}</h1>
        </div>
        <nav aria-label="Other days" className="flex gap-4 text-sm">
          {prev && (
            <Link href={`/nba/${prev}`} className="text-muted hover:text-ink">
              ← {formatDayShort(prev)}
            </Link>
          )}
          {next && (
            <Link href={`/nba/${next}`} className="text-muted hover:text-ink">
              {formatDayShort(next)} →
            </Link>
          )}
        </nav>
      </div>
      {state?.lastUpdatedAt && <p className="eyebrow num mb-4">{formatUpdated(state.lastUpdatedAt)}</p>}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatTile
          label="This slate ATS"
          value={rec.n ? record(rec.w, rec.l, rec.p) : "—"}
          sub={
            <>
              {rec.n ? fmtUnits(rec.units) : "no graded games"}
              {season && season.w + season.l + season.p > 0 && ` · season ${record(season.w, season.l, season.p)}`}
            </>
          }
          href="/nba/record"
        />
        <StatTile label="Games" value={games.length} sub="this slate" href="#board" />
        <StatTile label="Model disagrees 3+" value={disagree} sub="points off the market" />
        <StatTile
          label="Biggest gap"
          value={biggest ? fmtPts(biggest.gap) : "—"}
          sub={biggest ? `${biggest.game.away} at ${biggest.game.home}` : "no lines yet"}
          href={biggest ? `/nba/game/${biggest.game.id}` : undefined}
        />
      </div>

      {card && (
        <div className="mb-8">
          <MyCard card={card} />
        </div>
      )}

      <h2 id="board" className="eyebrow mb-3">
        Model board · {games.length} {games.length === 1 ? "game" : "games"}
      </h2>
      {games.length === 0 ? (
        <p className="text-muted">No games on this date.</p>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {games.map((g) => (
            <GameCard key={g.game.id} g={g} />
          ))}
        </div>
      )}
      <p className="text-sm text-muted mt-6 max-w-2xl leading-relaxed">
        Market line is the current consensus (median across books
        {games[0]?.marketProvider === "espn" ? "; until the odds feed is connected, a single book shown on ESPN" : ""}).
        The model pick is locked against the first line the pipeline ever saw and is graded only against that line.
        Number in brackets: points between model and market at lock. The strip above uses today&apos;s numbers.
        {biggest && ` Biggest gap today: ${lineLabel(biggest.projection?.spreadHome, biggest.game.away, biggest.game.home)} model vs ${lineLabel(biggest.marketSpreadHome, biggest.game.away, biggest.game.home)} market.`}
      </p>
    </div>
  );
}
