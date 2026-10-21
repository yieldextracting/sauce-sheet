import type { Metadata } from "next";
import Link from "next/link";
import { Note, PageTitle } from "@/components/ui";
import { slate } from "@/lib/board";
import * as data from "@/lib/data";
import { fmtInt, fmtSigned } from "@/lib/format";
import type { TSpot } from "@/lib/schemas";
import { formatDayLong, formatTip } from "@/lib/time";

export const metadata: Metadata = { title: "Rest and schedule spots" };

const DAYS_AHEAD = 3;
const LONG_TRAVEL_KM = 1500;

function Chips({ s, altitude }: { s: TSpot | null; altitude: boolean }) {
  if (!s) return <span className="text-muted">—</span>;
  const chips: string[] = [];
  if (s.b2b) chips.push("Back-to-back");
  if (s.threeInFour) chips.push("3 in 4");
  if (s.travelKm >= LONG_TRAVEL_KM) chips.push("Long trip");
  if (altitude) chips.push("At altitude");
  return chips.length ? (
    <span className="flex flex-wrap gap-1">
      {chips.map((c) => (
        <span key={c} className="eyebrow text-[0.6rem] border border-accent/70 text-accent rounded-sm px-1.5 py-0.5">{c}</span>
      ))}
    </span>
  ) : (
    <span className="text-muted text-xs">none</span>
  );
}

export default function RestPage() {
  const start = data.defaultBoardDay();
  const days = start ? data.boardDays().filter((d) => d >= start).slice(0, DAYS_AHEAD) : [];
  return (
    <div>
      <PageTitle eyebrow="NBA" title="Rest and schedule spots">
        Back-to-backs, three games in four nights, travel since the last game, and altitude, all on ET game dates. The
        last column is what the model gives these spots in points.
      </PageTitle>
      {days.map((day) => {
        const games = slate(day);
        return (
          <section key={day} className="mb-8" aria-labelledby={`r-${day}`}>
            <h2 id={`r-${day}`} className="eyebrow mb-2">{formatDayLong(day)}</h2>
            <div className="overflow-x-auto -mx-4 px-4">
              <table className="w-full text-sm num min-w-[600px]">
                <caption className="sr-only">Schedule spots, {formatDayLong(day)}</caption>
                <thead>
                  <tr className="text-left text-muted border-b border-rule">
                    <th scope="col" className="font-normal py-1.5 pr-3">Game</th>
                    <th scope="col" className="font-normal py-1.5 pr-3">Team</th>
                    <th scope="col" className="font-normal py-1.5 pr-3 text-right">Rest</th>
                    <th scope="col" className="font-normal py-1.5 pr-3 text-right">Travel</th>
                    <th scope="col" className="font-normal py-1.5 pr-3">Spots</th>
                    <th scope="col" className="font-normal py-1.5 text-right">Rest/travel pts</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((g) => {
                    const spots = g.projection?.spots;
                    const rt = g.projection?.contributions.find((c) => c.key === "rest_travel")?.pts ?? null;
                    return (["away", "home"] as const).map((side, i) => {
                      const s = spots?.[side] ?? null;
                      const team = g.game[side];
                      return (
                        <tr key={`${g.game.id}-${side}`} className={i === 0 ? "border-t border-rule" : ""}>
                          {i === 0 && (
                            <td rowSpan={2} className="py-1.5 pr-3 align-top">
                              <Link href={`/nba/game/${g.game.id}`} className="hover:underline">{g.game.away} at {g.game.home}</Link>
                              <span className="block text-xs text-muted">{formatTip(g.game.tipUtc)}</span>
                            </td>
                          )}
                          <td className="py-1.5 pr-3 font-medium">{team}</td>
                          <td className="py-1.5 pr-3 text-right">{s ? (s.restDays === null ? "opener" : `${s.restDays}d`) : "—"}</td>
                          <td className="py-1.5 pr-3 text-right">{s ? `${fmtInt(s.travelKm)} km` : "—"}</td>
                          <td className="py-1.5 pr-3"><Chips s={s} altitude={side === "away" && !!spots?.home?.atAltitude && !g.game.neutralSite} /></td>
                          {i === 0 && (
                            <td rowSpan={2} className="py-1.5 text-right align-top">
                              {rt === null ? "—" : `${fmtSigned(rt)} ${rt >= 0 ? g.game.home : g.game.away}`}
                            </td>
                          )}
                        </tr>
                      );
                    });
                  })}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
      <Note>
        Rest = full days off since the previous game. Travel is great-circle distance from the previous game&apos;s city.
        Altitude applies to visitors in Denver and Salt Lake City (venues above 1,000 m, from Open-Meteo elevation data).
        The point values come from coefficients fit on 2022-23 and 2023-24.
      </Note>
    </div>
  );
}
