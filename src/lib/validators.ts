/** Path pattern -> schema for every validated file under data/. Used by scripts/validate-data.ts. */
import type { z } from "zod";
import {
  CurrentLine,
  CurrentLines,
  FirstSeen,
  LineSnapshot,
  Grades,
  InjuryPull,
  ModelParams,
  ModelPick,
  PipelineState,
  ProjectionDay,
  Ratings,
  Result,
  Schedule,
  Teams,
} from "./schemas";

export const VALIDATORS: { pattern: RegExp; schema: z.ZodType }[] = [
  { pattern: /^teams\.json$/, schema: Teams },
  { pattern: /^schedule\/[^/]+\.json$/, schema: Schedule },
  { pattern: /^projections\/\d{4}-\d{2}-\d{2}\.json$/, schema: ProjectionDay },
  { pattern: /^lines\/current\.json$/, schema: CurrentLines },
  { pattern: /^lines\/closing\/[^/]+\.json$/, schema: CurrentLine },
  { pattern: /^lines\/snapshots\/\d{4}-\d{2}-\d{2}\/\d{8}T\d{4}Z\.json$/, schema: LineSnapshot },
  { pattern: /^lines\/first-seen\/[^/]+\.json$/, schema: FirstSeen },
  { pattern: /^picks\/model\/[^/]+\.json$/, schema: ModelPick },
  { pattern: /^results\/[^/]+\/[^/]+\.json$/, schema: Result },
  { pattern: /^ratings\/[^/]+\.json$/, schema: Ratings },
  { pattern: /^model\/params\.json$/, schema: ModelParams },
  { pattern: /^grades\/[^/]+\.json$/, schema: Grades },
  { pattern: /^logs\/state\.json$/, schema: PipelineState },
  { pattern: /^injuries\/(latest|\d{4}-\d{2}-\d{2}\/\d{8}T\d{4}Z)\.json$/, schema: InjuryPull },
];
