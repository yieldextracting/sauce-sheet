/**
 * The ONLY place the site formats times. Everything is US Eastern (America/New_York),
 * which handles EST/EDT automatically. Data is stored in UTC; we convert at render time.
 * ESLint bans toLocale* and Date getters elsewhere.
 */

const TZ = "America/New_York";

const dateParts = new Intl.DateTimeFormat("en-US", {
  timeZone: TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const tipFmt = new Intl.DateTimeFormat("en-US", {
  timeZone: TZ,
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

const weekdayShort = new Intl.DateTimeFormat("en-US", { timeZone: TZ, weekday: "short" });

const longDay = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC", // used on ET calendar dates already, anchored at noon UTC
  weekday: "long",
  month: "long",
  day: "numeric",
});

const shortDay = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  weekday: "short",
  month: "short",
  day: "numeric",
});

function parts(fmt: Intl.DateTimeFormat, d: Date): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of fmt.formatToParts(d)) out[p.type] = p.value;
  return out;
}

/** ET calendar date (YYYY-MM-DD) of a UTC instant. A game's "game day". */
export function etDate(utc: string | Date): string {
  const d = typeof utc === "string" ? new Date(utc) : utc;
  const p = parts(dateParts, d);
  return `${p.year}-${p.month}-${p.day}`;
}

/** "7:30 PM ET" */
export function formatTip(utc: string): string {
  return `${tipFmt.format(new Date(utc))} ET`;
}

/** "UPDATED TUE 8:39 PM ET" */
export function formatUpdated(utc: string): string {
  const d = new Date(utc);
  return `UPDATED ${weekdayShort.format(d).toUpperCase()} ${tipFmt.format(d)} ET`;
}

/** "Tuesday, October 20" for an ET date string. */
export function formatDayLong(etDay: string): string {
  return longDay.format(new Date(`${etDay}T12:00:00Z`));
}

/** "Tue, Oct 20" for an ET date string. */
export function formatDayShort(etDay: string): string {
  return shortDay.format(new Date(`${etDay}T12:00:00Z`));
}

export function todayEt(now: Date = new Date()): string {
  return etDate(now);
}

export function addDays(etDay: string, n: number): string {
  const d = new Date(`${etDay}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
