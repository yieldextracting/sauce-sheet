"use client";

import Link from "next/link";
import { useState } from "react";
import { fmtPct, fmtPts, fmtSigned, fmtSpread, fmtUnits, record, winPct } from "@/lib/format";
import { ResultTag } from "./ui";

export type RecordRow = {
  gameId: string;
  dateLabel: string;
  matchup: string;
  pick: string;
  edge: number | null;
  line: number | null;
  closingLine: number | null;
  clvPts: number | null;
  finalScore: string | null;
  result: string;
  profitU: number;
};

type Tier = { key: string; label: string; min: number };

function summarize(rows: RecordRow[]) {
  const done = rows.filter((r) => ["win", "loss", "push"].includes(r.result));
  const w = done.filter((r) => r.result === "win").length;
  const l = done.filter((r) => r.result === "loss").length;
  const p = done.filter((r) => r.result === "push").length;
  return { w, l, p, units: done.reduce((s, r) => s + r.profitU, 0), n: done.length };
}

export function RecordTable({ rows, tiers }: { rows: RecordRow[]; tiers: Tier[] }) {
  const [active, setActive] = useState("all");
  const tier = tiers.find((t) => t.key === active) ?? tiers[0];
  const shown = rows.filter((r) => (r.edge ?? 0) >= tier.min);
  const showClv = rows.some((r) => r.clvPts !== null);

  return (
    <div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6" role="group" aria-label="Filter by edge size">
        {tiers.map((t) => {
          const s = summarize(rows.filter((r) => (r.edge ?? 0) >= t.min));
          const on = t.key === active;
          return (
            <button
              key={t.key}
              type="button"
              aria-pressed={on}
              onClick={() => setActive(t.key)}
              className={`text-left bg-surface border rounded-sm p-4 ${on ? "border-accent" : "border-rule hover:border-muted"}`}
            >
              <span className="eyebrow block">{t.label}</span>
              <span className="num text-2xl font-semibold block mt-1">{s.n ? record(s.w, s.l, s.p) : "—"}</span>
              <span className="text-sm text-muted block mt-1 num">
                {s.n ? `${fmtPct(winPct(s.w, s.l))} · ${fmtUnits(s.units)}` : "no graded games yet"}
              </span>
            </button>
          );
        })}
      </div>

      {shown.length === 0 ? (
        <p className="text-muted">No picks in this tier yet.</p>
      ) : (
        <div className="overflow-x-auto -mx-4 px-4">
          <table className="w-full text-sm num min-w-[560px]">
            <caption className="sr-only">Model picks, {tier.label}</caption>
            <thead>
              <tr className="text-left text-muted border-b border-rule">
                <th scope="col" className="font-normal py-2 pr-3">Date</th>
                <th scope="col" className="font-normal py-2 pr-3">Game</th>
                <th scope="col" className="font-normal py-2 pr-3">Pick</th>
                <th scope="col" className="font-normal py-2 pr-3 text-right">Edge</th>
                {showClv && <th scope="col" className="font-normal py-2 pr-3 text-right">Close</th>}
                {showClv && <th scope="col" className="font-normal py-2 pr-3 text-right">CLV</th>}
                <th scope="col" className="font-normal py-2 pr-3">Final</th>
                <th scope="col" className="font-normal py-2 pr-3">Result</th>
                <th scope="col" className="font-normal py-2 text-right">Units</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {shown.map((r) => (
                <tr key={r.gameId}>
                  <td className="py-2 pr-3 whitespace-nowrap text-muted">{r.dateLabel}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">
                    <Link href={`/nba/game/${r.gameId}`} className="hover:underline">{r.matchup}</Link>
                  </td>
                  <td className="py-2 pr-3 whitespace-nowrap font-medium">{r.pick}</td>
                  <td className="py-2 pr-3 text-right">{fmtPts(r.edge)}</td>
                  {showClv && <td className="py-2 pr-3 text-right">{fmtSpread(r.closingLine)}</td>}
                  {showClv && <td className="py-2 pr-3 text-right">{fmtSigned(r.clvPts)}</td>}
                  <td className="py-2 pr-3 whitespace-nowrap">{r.finalScore ?? "—"}</td>
                  <td className="py-2 pr-3"><ResultTag result={r.result} /></td>
                  <td className="py-2 text-right">{r.result === "pending" ? "—" : fmtUnits(r.profitU)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
