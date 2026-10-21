import type { LinePoint } from "@/lib/data";
import { fmtPct, fmtPts, fmtSigned } from "@/lib/format";
import type { TAvailabilityRow, TRatings } from "@/lib/schemas";
import { METRICS, percentile, type Metric } from "@/lib/teamstats";
import { formatUpdated } from "@/lib/time";
import { lineLabel } from "@/lib/board";

const STATUS_LABEL: Record<string, string> = {
  out: "Out",
  doubtful: "Doubtful",
  questionable: "Questionable",
  probable: "Probable",
  available: "Available",
};

const STATUS_SHORT: Record<string, string> = { out: "Out", doubtful: "Doubt", questionable: "Q", probable: "Prob", available: "Avail" };

/** 04 / AVAILABILITY */
export function AvailabilityTable({
  away,
  home,
  rows,
  source,
  pulledAt,
}: {
  away: string;
  home: string;
  rows: { away: TAvailabilityRow[]; home: TAvailabilityRow[] };
  source: string | null;
  pulledAt: string | null;
}) {
  if (!pulledAt) return <p className="text-sm text-muted">No recent injury report was available when this game was projected.</p>;
  const sides: [string, TAvailabilityRow[]][] = [
    [away, rows.away],
    [home, rows.home],
  ];
  return (
    <div className="space-y-5">
      {sides.map(([team, list]) => {
        const total = list.reduce((s, r) => s + r.impactPts, 0);
        return (
          <div key={team}>
            <p className="eyebrow mb-1">
              {team} · expected cost {fmtPts(total)} pts
            </p>
            {list.length === 0 ? (
              <p className="text-sm text-muted">Nobody listed.</p>
            ) : (
              <div>
                <table className="w-full text-sm num">
                  <caption className="sr-only">{team} injury report and points impact</caption>
                  <thead>
                    <tr className="text-left text-muted border-b border-rule">
                      <th scope="col" className="font-normal py-1.5 pr-3">Player</th>
                      <th scope="col" className="font-normal py-1.5 pr-3">Status</th>
                      <th scope="col" className="font-normal py-1.5 pr-3 text-right">
                        <span className="sm:hidden">Play</span>
                        <span className="hidden sm:inline">P(play)</span>
                      </th>
                      <th scope="col" className="font-normal py-1.5 pr-3 text-right hidden sm:table-cell">Exp. min</th>
                      <th scope="col" className="font-normal py-1.5 text-right">Impact</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule">
                    {list.map((r) => (
                      <tr key={r.player}>
                        <td className="py-1.5 pr-3">
                          {r.player}
                          {r.reason && <span className="block text-xs text-muted">{r.reason}</span>}
                        </td>
                        <td className="py-1.5 pr-3">
                          <span className="sm:hidden">{STATUS_SHORT[r.status]}</span>
                          <span className="hidden sm:inline">{STATUS_LABEL[r.status]}</span>
                        </td>
                        <td className="py-1.5 pr-3 text-right">{fmtPct(r.pPlay, 0)}</td>
                        <td className="py-1.5 pr-3 text-right hidden sm:table-cell">{r.matched ? fmtPts(r.expMin) : "—"}</td>
                        <td className="py-1.5 text-right">{r.impactPts > 0 ? `−${r.impactPts.toFixed(1)}` : "0.0"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
      <p className="text-sm text-muted leading-relaxed max-w-2xl">
        Report from {source === "espn" ? "ESPN" : "the official NBA injury report"}, pulled{" "}
        {formatUpdated(pulledAt).replace("UPDATED ", "")}.
        {source === "espn" && " ESPN only says Out or Day-To-Day; Day-To-Day is treated as questionable (50%)."} Impact
        is the expected points the team loses: player value above a replacement-level player, times expected minutes,
        times the chance he sits. Players under 8 expected minutes count as 0. A dash means the name could not be
        matched to a box score.
      </p>
    </div>
  );
}

function Bar({ p }: { p: number | null }) {
  return (
    <span className="hidden sm:inline-block w-16 h-1.5 bg-surface-2 rounded-full align-middle overflow-hidden" aria-hidden>
      {p !== null && <span className="block h-full bg-accent" style={{ width: `${Math.max(2, p)}%` }} />}
    </span>
  );
}

/** 05 / HOW THEY RATE */
export function RateGrid({ away, home }: { away: string; home: string }) {
  const groups: [string, Metric[]][] = [
    ["Offense", METRICS.filter((m) => m.side === "off")],
    ["Defense", METRICS.filter((m) => m.side === "def")],
    ["Tempo", METRICS.filter((m) => m.side === "both")],
  ];
  return (
    <div>
      <table className="w-full text-sm num">
        <caption className="sr-only">Percentile vs the league, 100 is best</caption>
        <thead>
          <tr className="text-left text-muted border-b border-rule">
            <th scope="col" className="font-normal py-1.5 pr-3"></th>
            <th scope="col" className="font-normal py-1.5 pr-3 text-right sm:text-left">{away}</th>
            <th scope="col" className="font-normal py-1.5 pr-3 text-right sm:text-left">{home}</th>
          </tr>
        </thead>
        {groups.map(([name, ms]) => (
          <tbody key={name} className="divide-y divide-rule">
            <tr>
              <th scope="rowgroup" colSpan={3} className="text-left eyebrow pt-4 pb-1">{name}</th>
            </tr>
            {ms.map((m) => {
              const cells = [away, home].map((t) => ({ v: m.get(t), p: percentile(m, t) }));
              return (
                <tr key={m.key}>
                  <th scope="row" className="text-left font-normal py-1.5 pr-3 text-muted">{m.label}</th>
                  {cells.map((c, i) => (
                    <td key={i} className="py-1.5 pr-3 whitespace-nowrap text-right sm:text-left">
                      <Bar p={c.p} /> <span className="sm:ml-1 font-medium">{c.p ?? "—"}</span>
                      <span className="text-muted text-xs block sm:inline sm:ml-2">{c.v === null ? "" : m.fmt(c.v)}</span>
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        ))}
      </table>
    </div>
  );
}

/** 06 / TEAM RATINGS */
export function RatingsTable({ away, home, ratings }: { away: string; home: string; ratings: TRatings }) {
  const rows: [string, (a: string) => string][] = [
    ["Record", (a) => `${ratings.teams[a].w}-${ratings.teams[a].l}`],
    ["Adj. offensive rating", (a) => fmtPts(ratings.teams[a].ortg)],
    ["Adj. defensive rating", (a) => fmtPts(ratings.teams[a].drtg)],
    ["Adj. net rating", (a) => fmtSigned(ratings.teams[a].net)],
    ["Pace effect (poss/48)", (a) => fmtSigned(ratings.teams[a].pace)],
    ["Games played", (a) => String(ratings.teams[a].gp)],
    ["Weight on last season", (a) => fmtPct(ratings.teams[a].priorWeight, 0)],
  ];
  return (
    <table className="w-full max-w-lg text-sm num">
      <caption className="sr-only">Opponent-adjusted team ratings</caption>
      <thead>
        <tr className="text-left text-muted border-b border-rule">
          <th scope="col" className="font-normal py-1.5"></th>
          <th scope="col" className="font-normal py-1.5 text-right">{away}</th>
          <th scope="col" className="font-normal py-1.5 text-right">{home}</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-rule">
        {rows.map(([label, f]) => (
          <tr key={label}>
            <th scope="row" className="text-left font-normal py-1.5 text-muted">{label}</th>
            <td className="py-1.5 text-right">{f(away)}</td>
            <td className="py-1.5 text-right">{f(home)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** 07 / LINE MOVEMENT: step chart of the consensus spread (home perspective) over time. */
export function LineMovement({
  points,
  away,
  home,
  modelSpreadHome,
  tipUtc,
  tipped,
}: {
  points: LinePoint[];
  away: string;
  home: string;
  modelSpreadHome: number | null;
  tipUtc: string;
  tipped: boolean;
}) {
  const pts = points.filter((p) => p.spreadHome !== null) as (LinePoint & { spreadHome: number })[];
  if (pts.length === 0) return <p className="text-sm text-muted">No lines stored yet.</p>;
  const W = 360, H = 170, L = 44, R = 12, T = 12, B = 28;
  const t0 = new Date(pts[0].takenAt).getTime();
  const lastT = new Date(pts[pts.length - 1].takenAt).getTime();
  const tEnd = tipped ? Math.max(lastT, new Date(tipUtc).getTime()) : lastT;
  const span = Math.max(tEnd - t0, 60_000);
  const vals = [...pts.map((p) => p.spreadHome), ...(modelSpreadHome !== null ? [modelSpreadHome] : [])];
  const lo = Math.floor(Math.min(...vals) - 1), hi = Math.ceil(Math.max(...vals) + 1);
  const x = (t: string | number) => L + ((new Date(t).getTime() - t0) / span) * (W - L - R);
  const y = (v: number) => T + ((v - lo) / (hi - lo)) * (H - T - B); // more negative (home favoured) at top
  let d = `M ${x(pts[0].takenAt)} ${y(pts[0].spreadHome)}`;
  for (let i = 1; i < pts.length; i++) d += ` H ${x(pts[i].takenAt)} V ${y(pts[i].spreadHome)}`;
  d += ` H ${x(tEnd)}`;
  const ticks = Array.from({ length: hi - lo + 1 }, (_, i) => lo + i).filter((v) => (hi - lo > 8 ? v % 2 === 0 : true));
  const first = pts[0], last = pts[pts.length - 1];
  return (
    <figure className="max-w-xl">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-labelledby="lm-cap">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--rule)" strokeWidth={v === 0 ? 1 : 0.5} />
            <text x={L - 6} y={y(v) + 3} textAnchor="end" className="fill-[var(--muted)] text-[10px]" style={{ fontVariantNumeric: "tabular-nums" }}>
              {v === 0 ? "PK" : v > 0 ? `+${v}` : v}
            </text>
          </g>
        ))}
        {modelSpreadHome !== null && (
          <>
            <line x1={L} x2={W - R} y1={y(modelSpreadHome)} y2={y(modelSpreadHome)} stroke="var(--muted)" strokeDasharray="3 3" />
            <text x={W - R} y={y(modelSpreadHome) - 4} textAnchor="end" className="fill-[var(--muted)] text-[10px]">model</text>
          </>
        )}
        <path d={d} fill="none" stroke="var(--accent)" strokeWidth={2} />
        <circle cx={x(first.takenAt)} cy={y(first.spreadHome)} r={3.5} fill="var(--accent)" />
        <text x={L} y={H - 8} className="fill-[var(--muted)] text-[10px]">first seen</text>
        <text x={W - R} y={H - 8} textAnchor="end" className="fill-[var(--muted)] text-[10px]">
          {tipped ? "tip" : "latest"}
        </text>
      </svg>
      <figcaption id="lm-cap" className="text-sm text-muted mt-2">
        {home} spread, consensus. Opened {lineLabel(first.spreadHome, away, home)}, latest {lineLabel(last.spreadHome, away, home)}
        {" "}across {pts.length} snapshot{pts.length === 1 ? "" : "s"}. Higher on the chart means {home} more favoured.
      </figcaption>
      <table className="sr-only">
        <caption>Line snapshots</caption>
        <thead>
          <tr>
            <th scope="col">Taken</th>
            <th scope="col">Spread</th>
            <th scope="col">Total</th>
          </tr>
        </thead>
        <tbody>
          {pts.map((p) => (
            <tr key={p.takenAt}>
              <td>{formatUpdated(p.takenAt).replace("UPDATED ", "")}</td>
              <td>{lineLabel(p.spreadHome, away, home)}</td>
              <td>{p.total ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
