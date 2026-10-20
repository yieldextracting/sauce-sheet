import type { Metadata } from "next";
import Link from "next/link";
import { pickLabel } from "@/components/MyCard";
import { Note, PageTitle, ResultTag, StatTile } from "@/components/ui";
import { cards } from "@/lib/cards";
import * as data from "@/lib/data";
import { fmtPct, fmtPrice, fmtSigned, fmtUnits, record, winPct } from "@/lib/format";
import { formatDayLong } from "@/lib/time";

export const metadata: Metadata = { title: "My Card record" };

const MARKETS = ["spread", "total", "moneyline", "prop"] as const;

export default function CardRecordPage() {
  const g = data.cardGrades();
  const s = g?.summary.all;
  const all = cards().slice().reverse();
  const gradeFor = (date: string, id: string) => g?.grades.find((x) => x.etDate === date && x.pickId === id);

  return (
    <div>
      <PageTitle eyebrow="Human picks" title="My Card record">
        My own picks, written before tip in a dated file and graded automatically from final scores at the line and
        price I logged. Tracked separately from the model.
      </PageTitle>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatTile label="Record" value={s && s.w + s.l + s.p ? record(s.w, s.l, s.p) : "—"} sub={s ? fmtPct(winPct(s.w, s.l)) : undefined} />
        <StatTile label="Units" value={s ? fmtUnits(s.units) : "—"} sub={s ? `${s.risked.toFixed(1)}u risked` : undefined} />
        <StatTile label="ROI" value={s?.roi != null ? fmtPct(s.roi) : "—"} sub="profit ÷ risked" />
        <StatTile
          label="CLV"
          value={s?.clvPtsAvg != null ? fmtSigned(s.clvPtsAvg) : "—"}
          sub={s?.clvN ? `pts vs close · beat close ${fmtPct(s.beatClosePct, 0)}` : "spreads and totals, once closing lines exist"}
        />
      </div>

      {g && (
        <div className="overflow-x-auto mb-8">
          <table className="text-sm num min-w-[420px]">
            <caption className="sr-only">Record by market</caption>
            <thead>
              <tr className="text-left text-muted border-b border-rule">
                <th scope="col" className="font-normal py-2 pr-6">Market</th>
                <th scope="col" className="font-normal py-2 pr-6">W-L-P</th>
                <th scope="col" className="font-normal py-2 pr-6">Units</th>
                <th scope="col" className="font-normal py-2">ROI</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {MARKETS.map((m) => {
                const x = g.summary[m];
                if (!x || x.w + x.l + x.p + x.pending === 0) return null;
                return (
                  <tr key={m}>
                    <th scope="row" className="text-left font-normal py-2 pr-6 capitalize">{m}</th>
                    <td className="py-2 pr-6">{record(x.w, x.l, x.p)}</td>
                    <td className="py-2 pr-6">{fmtUnits(x.units)}</td>
                    <td className="py-2">{fmtPct(x.roi)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {all.length === 0 ? (
        <p className="text-muted">No cards posted yet.</p>
      ) : (
        <div className="space-y-6">
          {all.map((c) => (
            <section key={c.date} aria-labelledby={`d-${c.date}`}>
              <h2 id={`d-${c.date}`} className="eyebrow mb-2">
                <Link href={`/nba/${c.date}`} className="hover:text-ink">{formatDayLong(c.date)}</Link>
              </h2>
              {c.picks.length === 0 ? (
                <p className="text-sm text-muted">No plays.</p>
              ) : (
                <ul className="divide-y divide-rule border-y border-rule">
                  {c.picks.map((p) => {
                    const gr = gradeFor(c.date, p.id);
                    const amend = c.amendments.filter((a) => a.pickId === p.id);
                    return (
                      <li key={p.id} className="py-2 flex items-center gap-3 text-sm">
                        <ResultTag result={gr?.result ?? "pending"} />
                        <span className="font-medium flex-1 min-w-0">
                          {pickLabel(p)} <span className="text-muted">{fmtPrice(p.odds)} · {p.units}u</span>
                          {amend.map((a) => (
                            <span key={a.at} className="block text-xs text-muted">Amended: {a.note}</span>
                          ))}
                        </span>
                        <span className="num">{gr && gr.result !== "pending" ? fmtUnits(gr.profitU) : "—"}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}

      <div className="mt-8 space-y-2">
        <Note>Units are amount risked. A 1u play at -110 wins +0.909u or loses 1u. Pushes and voids are 0.</Note>
        <Note>
          Picks are locked at tip. A correction after tip needs a visible amendment note, and CI rejects any edit or new
          pick for a game that has already started.
        </Note>
      </div>
    </div>
  );
}
