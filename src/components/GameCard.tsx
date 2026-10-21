import Link from "next/link";
import { lineLabel, SAMPLE_BADGE_GAMES, type BoardGame } from "@/lib/board";
import { fmtPts, fmtSpread } from "@/lib/format";
import { formatTip } from "@/lib/time";
import { ResultTag, TeamMark } from "./ui";

export function SampleBadge({ awayGP, homeGP }: { awayGP: number; homeGP: number }) {
  const min = Math.min(awayGP, homeGP);
  if (min >= SAMPLE_BADGE_GAMES) return null;
  return (
    <span
      className="eyebrow border border-rule rounded-sm px-1.5 py-0.5 text-[0.6rem]"
      title={`Fewer than ${SAMPLE_BADGE_GAMES} games for at least one team. Ratings lean on last season.`}
    >
      Small sample · {min} GP
    </span>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3 py-1.5 border-t border-rule first:border-t-0">
      <dt className="text-muted text-sm">{label}</dt>
      <dd className="num text-sm font-medium text-right">{children}</dd>
    </div>
  );
}

const FLAG_LABEL: Record<string, string> = {
  b2b: "B2B",
  "3in4": "3-in-4",
  long_travel: "long trip",
};

function SpotLine({ g }: { g: BoardGame }) {
  const p = g.projection;
  if (!p) return null;
  const bits: string[] = [];
  for (const f of p.flags) {
    if (f === "altitude") bits.push(`${g.game.away} at altitude`);
    else {
      const side = f.endsWith("_away") ? "away" : "home";
      const key = f.replace(/_(away|home)$/, "");
      bits.push(`${g.game[side]} ${FLAG_LABEL[key] ?? key}`);
    }
  }
  const inj = p.contributions.find((c) => c.key === "injuries")?.pts ?? 0;
  if (Math.abs(inj) >= 0.5) bits.push(`injuries ${Math.abs(inj).toFixed(1)} → ${inj > 0 ? g.game.home : g.game.away}`);
  if (!bits.length) return null;
  return <p className="text-xs text-muted -mt-1">{bits.join(" · ")}</p>;
}

export function GameCard({ g }: { g: BoardGame }) {
  const { game, away, home, projection: p, pick } = g;
  const final = g.result;
  return (
    <article className="bg-surface border border-rule rounded-sm p-4 flex flex-col gap-3" aria-labelledby={`g-${game.id}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="eyebrow num" id={`g-${game.id}`}>
          {final ? "Final" : formatTip(game.tipUtc)}
          {game.status === "postponed" && " · Postponed"}
          <span className="sr-only">
            {" "}
            {away.name} at {home.name}
          </span>
        </p>
        {p && <SampleBadge awayGP={p.sample.awayGP} homeGP={p.sample.homeGP} />}
      </div>

      <div className="grid grid-cols-[1fr_auto] gap-y-2 items-center">
        <TeamMark team={away} record={g.awayRecord} />
        <span className="num text-xl font-semibold text-right">
          {final ? final.awayPts : fmtPts(p?.awayPts)}
        </span>
        <TeamMark team={home} record={g.homeRecord} />
        <span className="num text-xl font-semibold text-right">
          {final ? final.homePts : fmtPts(p?.homePts)}
        </span>
      </div>
      {final && p && (
        <p className="text-xs text-muted num">
          Projected {fmtPts(p.awayPts)}–{fmtPts(p.homePts)}
        </p>
      )}

      <SpotLine g={g} />

      <dl>
        <Row label="Market line">{lineLabel(g.marketSpreadHome, game.away, game.home)}</Row>
        <Row label="Model line">{p ? lineLabel(p.spreadHome, game.away, game.home) : "—"}</Row>
        <Row label="Model pick">
          {pick && pick.side !== "none" && g.pickTeam ? (
            <span className="inline-flex items-center gap-2">
              <span>
                {g.pickTeam} {fmtSpread(pick.line)}{" "}
                <span className="text-accent">({fmtPts(Math.abs(pick.edge ?? 0))})</span>
              </span>
              {g.grade && g.grade.result !== "pending" && <ResultTag result={g.grade.result} />}
            </span>
          ) : pick ? (
            <span className="text-muted">No pick ({pick.reason ?? "no edge"})</span>
          ) : (
            <span className="text-muted">Not locked yet</span>
          )}
        </Row>
      </dl>

      <div className="flex flex-wrap gap-x-4 gap-y-1 pt-1">
        <Link href={`/nba/game/${game.id}`} className="eyebrow text-accent hover:underline">
          Game breakdown →
        </Link>
      </div>
    </article>
  );
}
