import { MDXRemote } from "next-mdx-remote/rsc";
import type { CardFile } from "@/lib/cards";
import * as data from "@/lib/data";
import { fmtPrice, fmtSpread } from "@/lib/format";
import type { TCardPick } from "@/lib/schemas";
import { ResultTag } from "./ui";

export function pickLabel(p: TCardPick): string {
  switch (p.market) {
    case "spread":
      return `${p.side} ${fmtSpread(p.line ?? null)}`;
    case "total":
      return `${p.side === "over" ? "Over" : "Under"} ${p.line}`;
    case "moneyline":
      return `${p.side} ML`;
    case "prop":
      return `${p.player} ${p.side === "over" ? "o" : "u"}${p.line} ${p.stat?.toUpperCase()}`;
  }
}

function matchup(gameId: string): string {
  const g = data.game(gameId);
  return g ? `${g.away} at ${g.home}` : gameId;
}

export function MyCard({ card, compact = false }: { card: CardFile; compact?: boolean }) {
  const grades = data.cardGrades()?.grades ?? [];
  const gradeFor = (id: string) => grades.find((g) => g.etDate === card.date && g.pickId === id);
  return (
    <section aria-labelledby={`card-${card.date}`} className="bg-surface border border-accent/60 rounded-sm p-4 sm:p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id={`card-${card.date}`} className="font-serif text-xl font-semibold whitespace-nowrap">
          My Card
        </h2>
        <p className="eyebrow">Human picks · graded separately</p>
      </div>
      {card.picks.length === 0 ? (
        <p className="text-muted mt-3">No plays today.</p>
      ) : (
        <ol className="mt-3 divide-y divide-rule">
          {card.picks.map((p) => {
            const gr = gradeFor(p.id);
            const amend = card.amendments.filter((a) => a.pickId === p.id);
            return (
              <li key={p.id} className="py-3 flex gap-3">
                <span className="num text-accent font-semibold w-5 shrink-0">{p.id}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="font-semibold num">{pickLabel(p)}</span>
                    <span className="num text-sm text-muted">{fmtPrice(p.odds)}</span>
                    <span className="num text-sm text-muted">{p.units}u</span>
                    <span className="text-sm text-muted" aria-label={`Confidence ${p.confidence} of 5`}>
                      {"●".repeat(p.confidence)}
                      <span className="text-faint">{"○".repeat(5 - p.confidence)}</span>
                    </span>
                    {gr && gr.result !== "pending" && <ResultTag result={gr.result} />}
                  </div>
                  <p className="text-xs text-muted mt-0.5">{matchup(p.game)}</p>
                  {p.why && !compact && <p className="text-sm mt-1 leading-relaxed">{p.why}</p>}
                  {amend.map((a) => (
                    <p key={a.at} className="text-xs mt-1 border-l-2 border-accent pl-2">
                      <span className="eyebrow">Amended</span> {a.note}
                    </p>
                  ))}
                </div>
              </li>
            );
          })}
        </ol>
      )}
      {card.body && !compact && (
        <div className="prose-card mt-3 border-t border-rule pt-3 text-[0.95rem]">
          <MDXRemote source={card.body} />
          {card.amendments
            .filter((a) => a.pickId === "takes")
            .map((a) => (
              <p key={a.at} className="text-xs mt-2 border-l-2 border-accent pl-2">
                <span className="eyebrow">Takes amended</span> {a.note}
              </p>
            ))}
        </div>
      )}
    </section>
  );
}
