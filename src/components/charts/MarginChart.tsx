import { fmtSigned } from "@/lib/format";

const LABELS: Record<string, string> = {
  offense: "Offense",
  defense: "Defense",
  pace: "Pace",
  home: "Home court",
  rest_travel: "Rest & travel",
  injuries: "Injuries",
};

/**
 * Diverging horizontal bars: each input's contribution to the projected margin, in points.
 * Bars to the right favour the home team, to the left the away team.
 * Hand-rolled SVG with a caption and a hidden data table for screen readers.
 */
export function MarginChart({
  contributions,
  away,
  home,
  pendingKeys = [],
}: {
  contributions: { key: string; pts: number }[];
  away: string;
  home: string;
  pendingKeys?: string[];
}) {
  // Drawn at phone width so text stays ~1:1 on mobile; capped on desktop.
  const rowH = 30;
  const labelW = 96;
  const width = 360;
  const plotW = width - labelW - 44;
  const max = Math.max(1, ...contributions.map((c) => Math.abs(c.pts)));
  const scale = plotW / 2 / max;
  const mid = labelW + plotW / 2;
  const height = rowH * contributions.length + 30;
  const sum = contributions.reduce((s, c) => s + c.pts, 0);
  const favored = sum >= 0 ? home : away;

  return (
    <figure className="max-w-xl">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-auto"
        role="img"
        aria-labelledby="margin-cap"
      >
        <text x={mid - 6} y={14} textAnchor="end" className="fill-[var(--muted)] text-[10px] tracking-widest">
          ← {away}
        </text>
        <text x={mid + 6} y={14} className="fill-[var(--muted)] text-[10px] tracking-widest">
          {home} →
        </text>
        <line x1={mid} x2={mid} y1={22} y2={height} stroke="var(--rule)" />
        {contributions.map((c, i) => {
          const y = 24 + i * rowH;
          const w = Math.abs(c.pts) * scale;
          const x = c.pts >= 0 ? mid : mid - w;
          const pending = pendingKeys.includes(c.key);
          return (
            <g key={c.key}>
              <text x={0} y={y + rowH / 2 + 4} className="fill-[var(--ink)] text-[12px]">
                {LABELS[c.key] ?? c.key}
              </text>
              <rect x={x} y={y + 7} width={Math.max(w, 1)} height={rowH - 14} fill="var(--bar)" opacity={c.pts >= 0 ? 1 : 0.55} />
              <text
                x={c.pts >= 0 ? mid + w + 6 : mid - w - 6}
                y={y + rowH / 2 + 4}
                textAnchor={c.pts >= 0 ? "start" : "end"}
                className="fill-[var(--muted)] text-[11px]"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {pending ? "n/a" : fmtSigned(c.pts)}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption id="margin-cap" className="text-sm text-muted mt-2">
        Contributions sum to {Math.abs(sum).toFixed(1)} points toward {favored}. Positive numbers favour {home}, negative
        favour {away}.
        {pendingKeys.length > 0 && " Injuries are not modelled yet (phase 2) and contribute 0."}
      </figcaption>
      <table className="sr-only">
        <caption>Contribution to projected margin, points (positive favours {home})</caption>
        <thead>
          <tr>
            <th scope="col">Input</th>
            <th scope="col">Points</th>
          </tr>
        </thead>
        <tbody>
          {contributions.map((c) => (
            <tr key={c.key}>
              <th scope="row">{LABELS[c.key] ?? c.key}</th>
              <td>{fmtSigned(c.pts)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
