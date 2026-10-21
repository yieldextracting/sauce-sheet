/** Number formatting. Pure functions, no dates (dates live in time.ts). */

/** Spread from one side's perspective: -3.5, +2, PK */
export function fmtSpread(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (n === 0) return "PK";
  return n > 0 ? `+${trim(n)}` : `${trim(n)}`;
}

export function fmtPrice(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n > 0 ? `+${n}` : `${n}`;
}

export function fmtUnits(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  const v = Math.round(n * 10) / 10;
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1)}u`;
}

export function fmtPct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function fmtPts(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined) return "—";
  return n.toFixed(digits);
}

export function fmtSigned(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined) return "—";
  const v = Number(n.toFixed(digits));
  if (v === 0) return (0).toFixed(digits);
  return `${v > 0 ? "+" : "−"}${Math.abs(v).toFixed(digits)}`;
}

export function record(w: number, l: number, p = 0): string {
  return p ? `${w}-${l}-${p}` : `${w}-${l}`;
}

export function winPct(w: number, l: number): number | null {
  return w + l > 0 ? w / (w + l) : null;
}

function trim(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/** 1234 -> "1,234" (no locale APIs; see the ESLint date rule). */
export function fmtInt(n: number): string {
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
