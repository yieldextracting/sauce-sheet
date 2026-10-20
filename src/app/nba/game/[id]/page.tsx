import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MarginChart } from "@/components/charts/MarginChart";
import { SampleBadge } from "@/components/GameCard";
import { Note, ResultTag, SectionHeader, TeamMark } from "@/components/ui";
import { boardGame, lineLabel } from "@/lib/board";
import * as data from "@/lib/data";
import { fmtPct, fmtPrice, fmtPts, fmtSpread } from "@/lib/format";
import { formatDayLong, formatTip, formatUpdated } from "@/lib/time";

export const dynamicParams = false;

export function generateStaticParams() {
  const days = new Set(data.boardDays());
  return data
    .schedule()
    .filter((g) => days.has(g.etDate))
    .map((g) => ({ id: g.id }));
}

export async function generateMetadata({ params }: PageProps<"/nba/game/[id]">): Promise<Metadata> {
  const { id } = await params;
  const g = data.game(id);
  if (!g) return {};
  return { title: `${g.away} at ${g.home}, ${formatDayLong(g.etDate)}` };
}

export default async function GamePage({ params }: PageProps<"/nba/game/[id]">) {
  const { id } = await params;
  const game = data.game(id);
  if (!game) notFound();
  const bg = boardGame(game);
  const { away, home, projection: p, pick } = bg;
  const fs = data.firstSeen(id);
  const close = data.closingLine(id);

  return (
    <article>
      <div className="pt-6">
        <Link href={`/nba/${game.etDate}`} className="eyebrow hover:text-ink">
          ← Board · {formatDayLong(game.etDate)}
        </Link>
      </div>
      <header className="pt-4 pb-2">
        <p className="eyebrow num">
          {formatTip(game.tipUtc)}
          {game.venue && ` · ${game.venue}`}
          {game.neutralSite && " · neutral site"}
        </p>
        <h1 className="font-serif text-3xl sm:text-4xl font-semibold tracking-tight mt-2">
          {away.name} <span className="text-muted font-normal">at</span> {home.name}
        </h1>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-3">
          <TeamMark team={away} record={bg.awayRecord} size="lg" />
          <TeamMark team={home} record={bg.homeRecord} size="lg" />
          {p && <SampleBadge awayGP={p.sample.awayGP} homeGP={p.sample.homeGP} />}
        </div>
      </header>

      <SectionHeader n={1} title="The number" />
      {p ? (
        <>
          <table className="w-full max-w-xl text-sm num">
            <thead>
              <tr className="text-left text-muted">
                <th scope="col" className="font-normal py-2"></th>
                <th scope="col" className="font-normal py-2">Spread</th>
                <th scope="col" className="font-normal py-2">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule border-t border-rule">
              <tr>
                <th scope="row" className="text-left font-normal py-2 text-muted">Market, first seen</th>
                <td className="py-2">{fs ? lineLabel(fs.consensus.spreadHome, game.away, game.home) : "—"}</td>
                <td className="py-2">{fmtPts(fs?.consensus.total)}</td>
              </tr>
              <tr>
                <th scope="row" className="text-left font-normal py-2 text-muted">Market, latest</th>
                <td className="py-2">{lineLabel(bg.marketSpreadHome, game.away, game.home)}</td>
                <td className="py-2">{fmtPts(bg.marketTotal)}</td>
              </tr>
              {close && (
                <tr>
                  <th scope="row" className="text-left font-normal py-2 text-muted">Market, close</th>
                  <td className="py-2">{lineLabel(close.consensus.spreadHome, game.away, game.home)}</td>
                  <td className="py-2">{fmtPts(close.consensus.total)}</td>
                </tr>
              )}
              <tr>
                <th scope="row" className="text-left font-normal py-2 text-muted">Model, at lock</th>
                <td className="py-2">{pick?.modelSpreadHome != null ? lineLabel(pick.modelSpreadHome, game.away, game.home) : "—"}</td>
                <td className="py-2">{fmtPts(pick?.modelTotal)}</td>
              </tr>
              <tr>
                <th scope="row" className="text-left font-normal py-2 text-muted">Model, current</th>
                <td className="py-2">{lineLabel(p.spreadHome, game.away, game.home)}</td>
                <td className="py-2">{fmtPts(p.total)}</td>
              </tr>
              <tr className="font-semibold">
                <th scope="row" className="text-left py-2">Gap</th>
                <td className="py-2 text-accent" colSpan={2}>
                  {bg.gap !== null ? `${fmtPts(bg.gap)} pts` : "—"}
                  {pick && pick.side !== "none" && bg.pickTeam && (
                    <span className="text-ink font-normal">
                      {" "}
                      · locked pick {bg.pickTeam} {fmtSpread(pick.line)} at {fmtPrice(pick.price)}
                    </span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>
          {bg.grade && bg.grade.result !== "pending" && (
            <p className="mt-3 flex items-center gap-2 text-sm">
              <ResultTag result={bg.grade.result} /> Final {bg.grade.finalScore} ({game.away}–{game.home}), graded
              against the first-seen line.
            </p>
          )}
          <div className="mt-4 space-y-2">
            <Note>
              No backtest against closing lines is published yet (it ships with the methodology page). Until it is, treat
              every gap as unproven: a large gap is a question worth asking, not a signal to follow.
            </Note>
            {fs && (
              <Note>
                First line seen {formatUpdated(fs.seenAt).replace("UPDATED ", "")} from {fs.provider === "espn" ? "a single book via ESPN" : `${fs.consensus.nBooks} books`}. That line and the model pick are written once and never changed.
              </Note>
            )}
          </div>
        </>
      ) : (
        <Note>No projection for this game yet.</Note>
      )}

      <SectionHeader n={2} title="Projected score" />
      {p ? (
        <div>
          <div className="grid grid-cols-2 gap-4 max-w-md">
            <div>
              <p className="eyebrow">{game.away}</p>
              <p className="num text-4xl font-semibold">{fmtPts(p.awayPts)}</p>
              <p className="text-sm text-muted num">Win {fmtPct(1 - p.homeWinProb, 0)} · fair {fmtPrice(p.fairMlAway)}</p>
            </div>
            <div>
              <p className="eyebrow">{game.home}</p>
              <p className="num text-4xl font-semibold">{fmtPts(p.homePts)}</p>
              <p className="text-sm text-muted num">Win {fmtPct(p.homeWinProb, 0)} · fair {fmtPrice(p.fairMlHome)}</p>
            </div>
          </div>
          <p className="text-sm text-muted mt-3 num">
            Total {fmtPts(p.total)} · {fmtPts(p.pace)} possessions · ratings as of {formatUpdated(p.ratingsAsOf).replace("UPDATED ", "")}
          </p>
          {bg.result && (
            <p className="text-sm mt-1 num">
              Actual: {game.away} {bg.result.awayPts}, {game.home} {bg.result.homePts}
            </p>
          )}
        </div>
      ) : (
        <Note>Not projected yet.</Note>
      )}

      <SectionHeader n={3} title="Where the margin comes from" />
      {p ? (
        <>
          <MarginChart contributions={p.contributions} away={game.away} home={game.home} pendingKeys={["injuries"]} />
          <div className="mt-3">
            <Note>
              Offense and defense are opponent-adjusted ratings per 100 possessions, shrunk toward last season early on
              (prior weight {fmtPct(p.sample.priorWeight, 0)} for this game). Pace is the extra margin from the expected
              number of possessions. Home court and rest/travel coefficients were fit on 2022-23 and 2023-24, seasons the backtest does not use.
            </Note>
          </div>
        </>
      ) : (
        <Note>Not projected yet.</Note>
      )}
    </article>
  );
}
