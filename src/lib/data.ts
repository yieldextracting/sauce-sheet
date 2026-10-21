/**
 * Build-time data access. Reads JSON from data/ and validates it with Zod.
 * Server-only: never import from a client component.
 */
import "server-only";
import fs from "node:fs";
import path from "node:path";
import type { z } from "zod";
import {
  CurrentLine,
  CurrentLines,
  FirstSeen,
  Grades,
  InjuryPull,
  LineSnapshot,
  ModelParams,
  ModelPick,
  PipelineState,
  ProjectionDay,
  Ratings,
  Result,
  Schedule,
  Teams,
  type TGame,
  type TTeam,
} from "./schemas";
import { SEASON } from "./brand";
import { todayEt } from "./time";

const ROOT = process.cwd();
const DATA = path.join(ROOT, "data");

const cache = new Map<string, unknown>();

function load<T extends z.ZodType>(rel: string, schema: T): z.infer<T> | null {
  const key = rel;
  if (cache.has(key)) return cache.get(key) as z.infer<T> | null;
  const file = path.join(DATA, rel);
  if (!fs.existsSync(file)) {
    cache.set(key, null);
    return null;
  }
  const raw = JSON.parse(fs.readFileSync(file, "utf8"));
  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    throw new Error(`data/${rel} failed validation:\n${parsed.error.message}`);
  }
  cache.set(key, parsed.data);
  return parsed.data;
}

function listJson(rel: string): string[] {
  const dir = path.join(DATA, rel);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .sort();
}

export function teams(): TTeam[] {
  return load("teams.json", Teams) ?? [];
}

export function teamMap(): Record<string, TTeam> {
  return Object.fromEntries(teams().map((t) => [t.abbr, t]));
}

export function schedule(): TGame[] {
  return load(`schedule/${SEASON}.json`, Schedule)?.games ?? [];
}

export function game(id: string): TGame | undefined {
  return schedule().find((g) => g.id === id);
}

export function gameDays(): string[] {
  return [...new Set(schedule().map((g) => g.etDate))].sort();
}

export function gamesOn(day: string): TGame[] {
  return schedule()
    .filter((g) => g.etDate === day)
    .sort((a, b) => a.tipUtc.localeCompare(b.tipUtc) || a.id.localeCompare(b.id));
}

/** Days that have something worth a board page: a projection or a line. */
export function boardDays(): string[] {
  const proj = new Set(listJson("projections").map((f) => f.replace(".json", "")));
  return gameDays().filter((d) => proj.has(d));
}

/** The board's default slate: today ET if it has games, else the next game day, else the last one. */
export function defaultBoardDay(now: Date = new Date()): string | null {
  const days = boardDays();
  if (!days.length) return null;
  const today = todayEt(now);
  return days.find((d) => d >= today) ?? days[days.length - 1];
}

export function projections(day: string) {
  return load(`projections/${day}.json`, ProjectionDay)?.games ?? [];
}

export function projection(id: string, day: string) {
  return projections(day).find((p) => p.gameId === id) ?? null;
}

export function currentLines() {
  return load("lines/current.json", CurrentLines) ?? {};
}

export function firstSeen(id: string) {
  return load(`lines/first-seen/${id}.json`, FirstSeen);
}

export function closingLine(id: string) {
  return load(`lines/closing/${id}.json`, CurrentLine);
}

export function modelPick(id: string) {
  return load(`picks/model/${id}.json`, ModelPick);
}

export function result(id: string) {
  return load(`results/${SEASON}/${id}.json`, Result);
}

export function ratings() {
  return load("ratings/latest.json", Ratings);
}

export function modelParams() {
  return load("model/params.json", ModelParams);
}

export function modelGrades() {
  return load("grades/model.json", Grades);
}

export function cardGrades() {
  return load("grades/card.json", Grades);
}

export function pipelineState() {
  return load("logs/state.json", PipelineState);
}

export function injuries() {
  return load("injuries/latest.json", InjuryPull);
}

export type LinePoint = { takenAt: string; provider: string; spreadHome: number | null; total: number | null; nBooks: number };

let lineIndex: Map<string, LinePoint[]> | null = null;

/** Every snapshot that contained this game, oldest first. Built once per build from data/lines/snapshots. */
export function lineHistory(id: string): LinePoint[] {
  if (!lineIndex) {
    lineIndex = new Map();
    const root = path.join(DATA, "lines", "snapshots");
    const days = fs.existsSync(root) ? fs.readdirSync(root).sort() : [];
    for (const day of days) {
      for (const f of listJson(`lines/snapshots/${day}`)) {
        const snap = load(`lines/snapshots/${day}/${f}`, LineSnapshot);
        if (!snap) continue;
        for (const g of snap.games) {
          const arr = lineIndex.get(g.gameId) ?? [];
          arr.push({ takenAt: snap.takenAt, provider: snap.provider, spreadHome: g.consensus.spreadHome, total: g.consensus.total, nBooks: g.consensus.nBooks });
          lineIndex.set(g.gameId, arr);
        }
      }
    }
    for (const arr of lineIndex.values()) arr.sort((a, b) => a.takenAt.localeCompare(b.takenAt));
  }
  return lineIndex.get(id) ?? [];
}
