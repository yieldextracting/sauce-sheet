import Link from "next/link";
import type { ReactNode } from "react";
import type { TTeam } from "@/lib/schemas";

/** "01 / THE NUMBER" */
export function SectionHeader({ n, title, id }: { n: number; title: string; id?: string }) {
  return (
    <h2 id={id} className="flex items-baseline gap-3 border-t border-rule pt-6 mt-10 mb-4">
      <span className="eyebrow text-accent num whitespace-nowrap">{String(n).padStart(2, "0")} /</span>
      <span className="eyebrow text-ink">{title}</span>
    </h2>
  );
}

export function PageTitle({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <div className="pt-8 pb-4">
      {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
      <h1 className="font-serif text-3xl sm:text-4xl font-semibold tracking-tight">{title}</h1>
      {children && <div className="mt-3 text-muted max-w-2xl leading-relaxed">{children}</div>}
    </div>
  );
}

export function StatTile({ label, value, sub, href }: { label: string; value: ReactNode; sub?: ReactNode; href?: string }) {
  const body = (
    <>
      <p className="eyebrow">{label}</p>
      <p className="num text-2xl sm:text-3xl font-semibold mt-1">{value}</p>
      {sub && <p className="text-sm text-muted mt-1">{sub}</p>}
    </>
  );
  const cls = "block bg-surface border border-rule rounded-sm p-4";
  return href ? (
    <Link href={href} className={`${cls} hover:border-accent`}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

/** Team identity without logos: color chip + abbreviation + name. `team.logoUrl` is the hook for later. */
export function TeamMark({ team, record, size = "md" }: { team: TTeam; record?: string; size?: "md" | "lg" }) {
  return (
    <span className="inline-flex items-center gap-2 min-w-0">
      <span
        aria-hidden
        className={size === "lg" ? "w-3 h-6 shrink-0 rounded-[1px]" : "w-2 h-4 shrink-0 rounded-[1px]"}
        style={{ background: `linear-gradient(#${team.color} 65%, #${team.altColor} 65%)` }}
      />
      <span className="font-semibold num">{team.abbr}</span>
      <span className="text-muted truncate hidden sm:inline">{team.shortName}</span>
      {record && <span className="text-muted text-sm num">{record}</span>}
    </span>
  );
}

export function ResultTag({ result }: { result: string }) {
  const map: Record<string, { t: string; cls: string; label: string }> = {
    win: { t: "W", cls: "bg-accent text-accent-ink", label: "Win" },
    loss: { t: "L", cls: "border border-rule text-muted", label: "Loss" },
    push: { t: "P", cls: "border border-rule text-muted", label: "Push" },
    void: { t: "V", cls: "border border-dashed border-rule text-faint", label: "Void" },
    pending: { t: "·", cls: "text-faint", label: "Pending" },
  };
  const m = map[result] ?? map.pending;
  return (
    <span className={`inline-flex w-6 h-6 items-center justify-center text-xs font-bold rounded-sm ${m.cls}`} title={m.label}>
      <span aria-hidden>{m.t}</span>
      <span className="sr-only">{m.label}</span>
    </span>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted leading-relaxed max-w-2xl">{children}</p>;
}
