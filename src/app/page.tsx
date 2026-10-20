import Link from "next/link";
import { StatTile } from "@/components/ui";
import { BRAND } from "@/lib/brand";
import * as data from "@/lib/data";
import { fmtPct, fmtSigned, fmtUnits, record, winPct } from "@/lib/format";
import type { TSummary } from "@/lib/schemas";

function tiles(s: TSummary | undefined) {
  const n = s ? s.w + s.l + s.p : 0;
  return {
    ats: s && n ? record(s.w, s.l, s.p) : "—",
    atsSub: s && n ? `${fmtPct(winPct(s.w, s.l))} · ${fmtUnits(s.units)}` : "no graded picks yet",
    clv: s?.clvPtsAvg != null ? fmtSigned(s.clvPtsAvg) : "—",
    clvSub: s?.clvN ? `pts vs close · beat it ${fmtPct(s.beatClosePct, 0)} of ${s.clvN}` : "needs closing lines",
  };
}

const HOW = [
  {
    t: "Possessions, not just box scores",
    d: "Every game is converted to points per 100 possessions on offense and defense, plus pace. That strips out tempo and says how well a team actually scores and stops.",
  },
  {
    t: "Adjusted for who they played",
    d: "Ratings are solved jointly across the whole schedule with home court, rest, back-to-backs and travel. Early in the season they lean on last year's ratings and let go as games come in.",
  },
  {
    t: "Locked, then graded in public",
    d: "The first market line the pipeline sees is written once, with the model's pick against it, and committed to git. Every pick is graded against that line. The record is the whole record.",
  },
];

export default function Home() {
  const m = tiles(data.modelGrades()?.summary.all);
  const c = tiles(data.cardGrades()?.summary.all);
  const cs = data.cardGrades()?.summary.all;
  return (
    <div>
      <section className="pt-12 pb-8">
        <h1 className="font-serif text-4xl sm:text-6xl font-semibold tracking-tight">{BRAND.name}</h1>
        <p className="font-serif italic text-xl sm:text-2xl text-muted mt-3">{BRAND.tagline}</p>
        <p className="mt-6 max-w-2xl leading-relaxed">
          An NBA model that projects every game, shown next to the market, with my own picks on top. Every number is
          produced by the pipeline and every pick is graded after the game, win or lose.
        </p>
        <div className="flex flex-wrap gap-3 mt-6">
          <Link href="/nba" className="bg-accent text-accent-ink px-4 py-2 rounded-sm font-semibold text-sm">
            Today&apos;s board
          </Link>
          <Link href="/nba/record" className="border border-rule px-4 py-2 rounded-sm text-sm hover:border-accent">
            Model record
          </Link>
          <Link href="/nba/card" className="border border-rule px-4 py-2 rounded-sm text-sm hover:border-accent">
            My Card
          </Link>
        </div>
      </section>

      <section aria-labelledby="records">
        <h2 id="records" className="eyebrow mb-3">Season to date · NBA 2026-27</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatTile label="Model ATS" value={m.ats} sub={m.atsSub} href="/nba/record" />
          <StatTile label="Model CLV" value={m.clv} sub={m.clvSub} href="/nba/record" />
          <StatTile label="My Card" value={c.ats} sub={cs?.roi != null ? `${c.atsSub} · ROI ${fmtPct(cs.roi)}` : c.atsSub} href="/nba/card" />
          <StatTile label="My Card CLV" value={c.clv} sub={c.clvSub} href="/nba/card" />
        </div>
      </section>

      <section aria-labelledby="how" className="mt-12">
        <h2 id="how" className="eyebrow mb-4">How it works</h2>
        <ol className="grid md:grid-cols-3 gap-6">
          {HOW.map((h, i) => (
            <li key={h.t} className="border-t border-rule pt-4">
              <p className="eyebrow text-accent num">{String(i + 1).padStart(2, "0")}</p>
              <h3 className="font-serif text-xl font-semibold mt-1">{h.t}</h3>
              <p className="text-muted mt-2 leading-relaxed text-[0.95rem]">{h.d}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
