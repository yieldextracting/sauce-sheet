# Sauce Sheet: build plan

> "Every line. Every number. Graded in public."

Status: **plan only, no code yet.** The open questions are at the bottom. Nothing gets built until they're answered.

---

## 0. What I verified before writing this (2026-10-20, from your MyRepublic IP in Singapore)

| Source | Result | Consequence |
|---|---|---|
| `cdn.nba.com` scoreboard / `scheduleLeagueV2` / odds JSON | **403 Access Denied (Akamai)**, from curl *and* from a real browser | The prompt assumed this works everywhere. From your machine it doesn't. It's IP/geo based, not fingerprinting. |
| `www.nba.com`, `stats.nba.com` | 403 / connection hangs | `nba_api` can't run on your laptop either. **"Run stats.nba.com locally" is dead from Singapore.** |
| `basketball-reference.com` | 403 | Not an option. |
| ESPN `site.api.espn.com/.../nba/scoreboard?dates=YYYYMMDD` | 200. Tonight's 3 games: BOS@DET 19:00Z, PHI@NYK 23:00Z, OKC@SAS 01:30Z | Works. Schedule, status, scores. |
| ESPN `.../nba/summary?event={id}` | 200. Full player + team box score, injuries, play-by-play | Works. Box scores for ratings, player logs, props, grading. |
| ESPN `.../nba/teams/{id}/schedule?season=2026` | 200. 82 games for BOS 2025-26 | Works. Full past seasons for priors and backtest. |
| ESPN core `.../events/{id}/competitions/{id}/odds` | 200. **Open and close spreads** for 2023-24 (Caesars), 2024-25 (ESPN BET), 2025-26 (DraftKings). None for 2022-23 | Free historical closing lines for the backtest. Single book, not consensus. |
| ESPN `.../nba/injuries` | 200, ~1 MB | Injury fallback works. |
| Official injury report index `official.nba.com/nba-injury-report-2026-27-season/` | 200. 43 PDF links today, every 15 min | Works. Pattern: `ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HH_MMAM.pdf` (times are ET). |
| Those PDFs | 200, `application/pdf`, ~86 KB | Primary injury source. Parse with `pdfplumber`. |
| The Odds API `/v4/sports` | 401 without key (expected) | Endpoint is live. Needs your key. |

Not verified yet: whether ESPN and `ak-static.cms.nba.com` answer **GitHub Actions** IPs. That's the first task of Phase 1: a throwaway "probe" workflow hits every endpoint from a runner before I build on it. If one fails from Actions, that stage moves to your laptop (see §6, "fallback runner").

**Decision: ESPN replaces both `cdn.nba.com` and `nba_api`.** One source for schedule, scores, box scores and history. It works from your laptop today and very likely from Actions. The official PDF stays primary for injuries because it's the source of truth, with ESPN as fallback. If you later want lineup data from `stats.nba.com`, the only route is a US residential IP. That's out of scope for v1.

Reference site (samthemodelman): I read the home page, the NBA and NFL boards, an NFL game breakdown, the props page, the record page and the gaps page. I'm copying the structure, not the copy. Two things worth stealing: (a) the honest "tracks the market rather than beating it" line in section 01, sourced from the backtest; (b) "counted at X% toward a play" on props.

---

## 1. Key decisions (brief)

- **Repo:** standalone repo at `~/Documents/Claude/sauce-sheet` with its own `git init`, pushed to GitHub. Not inside the existing `Documents/Claude` repo.
- **Stack:** Next.js 16 (App Router, `output` = static where possible) · React 19 · TypeScript · Tailwind 4 · Zod 4 · `next-mdx-remote` + `gray-matter` for cards · Vitest. Python 3.13 with a plain `venv` and pinned `requirements.txt` (`httpx`, `pydantic`, `numpy`, `scipy`, `pdfplumber`, `python-frontmatter`, `pytest`). uv isn't installed, and venv is one less thing.
- **Brand:** `src/lib/brand.ts` exports `BRAND = { name: "Sauce Sheet", tagline: "...", url }`. Python reads the same values from `config/brand.json`. That's one place to rename.
- **Config:** `config/model.json` holds edge tiers `[1.5, 3, 5]`, shrinkage K, sim count, and prop weights. `config/site.json` holds `SHOW_BOOK_NAMES`. `config/odds.json` holds markets, regions, books and the credit budget. Both runtimes read these and Zod validates them.
- **Game ID:** `YYYYMMDD-AWY-HOM` using the **ET** date of the originally scheduled tip, e.g. `20261020-BOS-DET`. It's readable in URLs and provider-agnostic. `espnId` and `oddsEventId` are stored as mappings. A postponed game keeps its ID, and its `tipUtc` and `status` change.
- **Grading logic lives only in Python.** The site renders `data/grades/*.json`. That gives one implementation and one set of tests.
- **Model record locks at first sight.** When the pipeline first sees a market line for a game, it writes **both** `lines/first-seen/{id}.json` and `picks/model/{id}.json` (the model's line *at that moment*) with exclusive create. The board also shows the live model line, labelled "current". The graded pick is the locked one. This is the only version without look-ahead bias (see Q6).
- **Scheduler:** **one** GitHub Actions workflow running every 30 min. A Python "gate" decides what's due in ET terms. Details in §6.
- **Charts:** hand-rolled SVG components. Each has a `<figcaption>` summary and a visually hidden `<table>` with the same numbers.
- **No logos:** `TeamMark` renders a color chip plus the abbreviation and name. Team colors come from ESPN's `/teams` feed (`color`, `alternateColor`), not typed by me. A `logoUrl?: string` prop is the hook for later.
- **`frontend-design` skill:** not installed in this environment. I'll follow your design brief directly (§8).

---

## 2. File tree

```
sauce-sheet/
├─ PLAN.md  README.md (runbook)  .env.example  .gitignore
├─ config/
│  ├─ brand.json  site.json  model.json  odds.json
├─ reference/
│  └─ arenas.json            # 30 arenas: lat/lon, elevation_ft, tz. Facts with a source URL per row.
├─ content/cards/YYYY-MM-DD.mdx
├─ data/
│  ├─ teams.json             # from ESPN /teams: id, abbr, name, colors
│  ├─ schedule/2026-27.json
│  ├─ results/2026-27/{gameId}.json         # final score, status, team box, player box
│  ├─ history/{season}/team_games.json      # backfill, compact (local job)
│  ├─ history/{season}/player_games.json
│  ├─ history/{season}/lines.json           # ESPN open/close for backtest
│  ├─ injuries/YYYY-MM-DD/{HHMM}Z.json      # every pull, normalized
│  ├─ injuries/latest.json
│  ├─ lines/snapshots/YYYY-MM-DD/{HHMM}Z.json   # featured markets, normalized, all books
│  ├─ lines/props/YYYY-MM-DD/{HHMM}Z/{gameId}.json
│  ├─ lines/first-seen/{gameId}.json        # WRITE-ONCE
│  ├─ lines/closing/{gameId}.json           # last pre-tip snapshot (derived)
│  ├─ picks/model/{gameId}.json             # WRITE-ONCE, model pick at lock
│  ├─ ratings/YYYY-MM-DD.json  ratings/latest.json
│  ├─ projections/YYYY-MM-DD.json
│  ├─ props/YYYY-MM-DD/{gameId}.json        # sims summary (Phase 3)
│  ├─ grades/model.json  grades/card.json   # derived, fully regenerated each run
│  ├─ backtest/summary.json                 # Phase 3
│  └─ logs/pulls.jsonl  logs/odds-credits.jsonl
├─ pipeline/                 # python -m pipeline run --stage <name|all>
│  ├─ __main__.py  cli.py  gate.py  config.py  et.py  io.py (write_once, atomic writes)
│  ├─ sources/espn.py  sources/injury_report.py  sources/odds/{base.py,the_odds_api.py,budget.py}
│  ├─ stages/pull_schedule.py  pull_results.py  pull_odds.py  pull_injuries.py
│  │        lock.py  build_ratings.py  project_games.py  simulate_props.py  grade.py  backfill.py  backtest.py
│  ├─ model/ratings.py  projection.py  availability.py  props.py  rest.py
│  └─ tests/ (pytest, with recorded fixtures: ESPN JSON, an injury PDF, an Odds API response)
├─ scripts/
│  ├─ newcard.ts             # npm run newcard
│  ├─ validate-data.ts       # prebuild: Zod over every JSON + card frontmatter
│  └─ check-immutable.ts     # CI: first-seen + model picks + locked card picks
├─ src/
│  ├─ app/
│  │  ├─ layout.tsx  page.tsx (home)  responsible-gambling/page.tsx  opengraph-image.tsx
│  │  └─ nba/
│  │     ├─ page.tsx                 # board, current slate
│  │     ├─ [date]/page.tsx          # board archive by ET date
│  │     ├─ game/[id]/page.tsx + opengraph-image.tsx
│  │     ├─ props/[id]/page.tsx
│  │     ├─ record/page.tsx  card/page.tsx  card/[date]/opengraph-image.tsx
│  │     ├─ gaps/page.tsx  rest/page.tsx  methodology/page.tsx
│  ├─ components/ TeamMark, GameCard, StatTile, SectionHeader ("01 / THE NUMBER"), Footer,
│  │             SampleBadge, charts/{HBar,Distribution,LineMovement,Percentile}.tsx, MyCard
│  ├─ lib/ brand.ts  time.ts (THE ONLY ET helper)  data.ts (loaders)  schemas.ts (Zod)  format.ts
│  └─ tests/ (vitest: time.ts, schemas, card parsing)
└─ .github/workflows/ pipeline.yml  ci.yml  probe.yml (Phase 1 day 1, then deleted)
```

---

## 3. Data contracts (Zod, `src/lib/schemas.ts`)

Every file under `data/` and every card's frontmatter is parsed by these at build time (`prebuild`). One bad file fails the build. Python writes through Pydantic models with the same shape, and a test round-trips sample files through both.

```ts
const UtcIso = z.string().datetime({ offset: false });        // always ...Z
const EtDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const GameId = z.string().regex(/^\d{8}-[A-Z]{2,3}-[A-Z]{2,3}$/);
const Abbr   = z.string().regex(/^[A-Z]{2,3}$/);
const American = z.number().int().refine(n => n <= -100 || n >= 100);

export const Team = z.object({ abbr: Abbr, espnId: z.string(), name: z.string(),
  shortName: z.string(), color: z.string().regex(/^[0-9a-f]{6}$/i),
  altColor: z.string().regex(/^[0-9a-f]{6}$/i), logoUrl: z.string().url().optional() });

export const Game = z.object({ id: GameId, season: z.string(), etDate: EtDate, tipUtc: UtcIso,
  away: Abbr, home: Abbr, espnId: z.string(), oddsEventId: z.string().nullable(),
  status: z.enum(["scheduled","live","final","postponed","cancelled"]),
  neutralSite: z.boolean(), venue: z.string().nullable() });
export const Schedule = z.object({ season: z.string(), pulledAt: UtcIso, games: z.array(Game) });

export const BookLine = z.object({ book: z.string(),           // plain-text name; hidden if !SHOW_BOOK_NAMES
  spreadHome: z.number().nullable(), spreadHomePrice: American.nullable(), spreadAwayPrice: American.nullable(),
  total: z.number().nullable(), overPrice: American.nullable(), underPrice: American.nullable(),
  mlHome: American.nullable(), mlAway: American.nullable(), lastUpdate: UtcIso });
export const GameLines = z.object({ gameId: GameId, books: z.array(BookLine),
  consensus: z.object({ spreadHome: z.number().nullable(), total: z.number().nullable() }) }); // median across books
export const LineSnapshot = z.object({ takenAt: UtcIso, provider: z.string(), games: z.array(GameLines) });

export const FirstSeen = GameLines.extend({ seenAt: UtcIso, snapshot: z.string() /* path */ });

export const ModelPick = z.object({ gameId: GameId, lockedAt: UtcIso, modelVersion: z.string(),
  modelSpreadHome: z.number(), marketSpreadHome: z.number(), edge: z.number(),  // model - market, pts
  side: z.enum(["home","away","none"]), line: z.number(), price: American,
  modelTotal: z.number(), marketTotal: z.number().nullable() });

export const Projection = z.object({ gameId: GameId, generatedAt: UtcIso, modelVersion: z.string(),
  awayPts: z.number(), homePts: z.number(), spreadHome: z.number(), total: z.number(),
  pace: z.number(), homeWinProb: z.number().min(0).max(1), fairMlHome: American, fairMlAway: American,
  contributions: z.array(z.object({ key: z.enum(["offense","defense","pace","home","rest_travel","injuries"]),
    pts: z.number() })),                               // signed toward home; sums to spreadHome (tested)
  sample: z.object({ awayGP: z.number().int(), homeGP: z.number().int(), priorWeight: z.number() }),
  flags: z.array(z.enum(["b2b_away","b2b_home","3in4_away","3in4_home","altitude","long_travel_away","long_travel_home"])) });

export const Injury = z.object({ player: z.string(), team: Abbr, gameId: GameId.nullable(),
  status: z.enum(["out","doubtful","questionable","probable","available"]), reason: z.string(),
  pPlay: z.number().min(0).max(1), source: z.enum(["nba_official","espn"]) });
export const InjuryPull = z.object({ pulledAt: UtcIso, source: z.string(), reportStamp: z.string().nullable(),
  ok: z.boolean(), error: z.string().nullable(), items: z.array(Injury) });

export const Result = z.object({ gameId: GameId, status: z.enum(["final","postponed","cancelled"]),
  awayPts: z.number().int().nullable(), homePts: z.number().int().nullable(), finalizedAt: UtcIso,
  players: z.array(z.object({ name: z.string(), team: Abbr, espnId: z.string(), dnp: z.boolean(),
    min: z.number(), pts: z.number().int(), reb: z.number().int(), ast: z.number().int(), fg3m: z.number().int() /* + rest of box */ })) });

// My Card frontmatter
export const CardPick = z.object({
  id: z.string(),                                   // "1", "2" ... stable within the day
  game: GameId,
  market: z.enum(["spread","total","moneyline","prop"]),
  side: z.string(),                                 // "BOS" | "over" | "under"
  player: z.string().optional(), stat: z.enum(["pts","reb","ast","fg3m","pra"]).optional(),
  line: z.number().nullable(),                      // null for moneyline
  odds: American, units: z.number().positive(),
  confidence: z.number().int().min(1).max(5),
  why: z.string().optional() });
export const Card = z.object({ date: EtDate, picks: z.array(CardPick),
  amendments: z.array(z.object({ at: UtcIso, pickId: z.string(), note: z.string() })).default([]) });

export const Grade = z.object({ source: z.enum(["model","card"]), gameId: GameId, pickId: z.string(),
  market: z.string(), side: z.string(), line: z.number().nullable(), price: American, units: z.number(),
  result: z.enum(["win","loss","push","void","pending"]), profitU: z.number(),
  closingLine: z.number().nullable(), closingPrice: American.nullable(),
  clvPts: z.number().nullable(), clvProb: z.number().nullable(), edge: z.number().nullable() });
export const Grades = z.object({ generatedAt: UtcIso, grades: z.array(Grade),
  summary: z.record(z.string(), z.object({ w: z.number(), l: z.number(), p: z.number(),
    units: z.number(), roi: z.number(), clvPtsAvg: z.number().nullable(), beatClosePct: z.number().nullable() })) });

export const CreditLog = z.object({ at: UtcIso, endpoint: z.string(), cost: z.number(), remaining: z.number(), used: z.number() });
```

Phase 2 and 3 add `Ratings`, `PropSim`, `BacktestSummary` and `RestSpot` in the same style.

---

## 4. Time handling (US Eastern only)

- Data stores **UTC only** (`...Z`). The one exception is `etDate`, which is a derived key, not a time.
- TS: `src/lib/time.ts` is the **only** place that formats times. It uses `Intl.DateTimeFormat` with `timeZone: "America/New_York"` and exports `etDate(utc)`, `formatTip(utc)` → `7:30 PM ET`, `formatUpdated(utc)` → `UPDATED TUE 8:39 PM ET`, and `todayEt(now)`. A lint rule bans `toLocale*`/`getHours` elsewhere.
- Python: `pipeline/et.py` uses `zoneinfo.ZoneInfo("America/New_York")`. Nothing calls naive `datetime.now()`. A test greps for it.
- **Game day = ET date of the scheduled tip.** A 10:30 PM ET tip that ends at 1 AM ET belongs to the earlier date. Grading, card filenames, `newcard`, slate records and rest flags all key off `Game.etDate`.
- Tests (both runtimes): 23:30 ET vs 00:30 ET; 2026-11-01 01:30 ET occurs twice (EDT then EST) and both instances map to 2026-11-01; 2027-03-14 spring forward (02:30 ET doesn't exist); a 10:30 PM tip on Oct 31 ending after the change; the gate's due-time logic on both sides of the switch.

---

## 5. Pipeline stages

`python -m pipeline run --stage all` runs them in this order. Each one runs alone with `--stage X` and is idempotent.

| Stage | Source | Writes | Where it runs |
|---|---|---|---|
| `pull_schedule` | ESPN scoreboard by date (season range) | `schedule/2026-27.json`, `teams.json` | Actions (daily) |
| `pull_results` | ESPN summary for games past tip | `results/...` | Actions |
| `pull_odds` | Odds API (`OddsProvider` interface) | `lines/snapshots/...`, `lines/props/...`, credit log | Actions (gated) |
| `lock` | latest snapshot + latest projection | `first-seen/` + `picks/model/` (**exclusive create, refuse overwrite**) | Actions, right after `pull_odds` |
| `pull_injuries` | official PDF → ESPN fallback | `injuries/...`, `logs/pulls.jsonl` | Actions (hourly on game days) |
| `build_ratings` | results + priors | `ratings/` | Actions |
| `project_games` | ratings + injuries + rest | `projections/` | Actions |
| `simulate_props` (P3) | player logs + prop lines | `props/` | Actions |
| `grade` | results + picks + cards + closing lines | `grades/`, `lines/closing/` | Actions (nightly) |
| `backfill` | ESPN, 2022-23 → 2025-26 | `history/` | **Laptop, once** (~4k requests at ~2/s, network-bound, light on CPU) |
| `backtest` (P3) | history | `backtest/summary.json` | Laptop |

**Odds client.** `OddsProvider` is a Protocol with `events()`, `featured(markets)` and `event_props(event_id, markets)`, and it returns normalized `GameLines`. `TheOddsApi` implements it. `BudgetGuard` wraps every call. It reads `x-requests-remaining`/`x-requests-used`/`x-requests-last`, appends to `logs/odds-credits.jsonl`, and **refuses the next call** if the estimated cost would push remaining below `reserve` or today's spend past `dailyCap`. It fails loudly, so the workflow goes red. `/sports` and `/events` are free, and I use `/events` to map IDs before spending credits.

**Credit math** (verified from the v4 docs: featured = markets × regions; per-event props = markets *returned* × regions; historical = 10×):
- Featured (spreads, totals, h2h; `us`) = **3 credits/snapshot**, covering every game in one call.
- Props (pts, reb, ast, threes; `us`) = **~4 credits/game/snapshot**.
- Avg ~7.5 games/night: 3 snapshots × (3 + 30) ≈ **100/day**, plus ~4 featured-only "closing" snapshots for CLV (12) ≈ **~112/day ≈ 3.4k/month ≈ 19k/season**. That matches your estimate.
- **Plan:** the **20K plan ($30/mo)** covers it with ~6× monthly headroom. The free 500-credit Starter is enough to build and test against today. The backtest uses ESPN's free open/close lines, so it doesn't need historical credits (optional cross-check in Q1).

**Model v1** (`pipeline/model/`):
1. **Ratings:** each team-game gives an observation `100·pts/poss = μ + O_team + D_opp + h·home + β·rest_terms`. Possessions come from the box score (`FGA − OREB + TOV + 0.44·FTA`, averaged across both teams). Pace gets the same treatment. Solved as ridge regression where the penalty pulls toward **priors** (last season's ratings regressed 1/3 to league mean) as `K` pseudo-games. The prior's weight decays naturally as games accumulate (`K/(K+GP)`). Rest terms: rest days (0/1/2/3+), B2B, 3-in-4, travel km (from `reference/arenas.json`), altitude (DEN, UTA).
2. **Projection:** `poss = pace_h·pace_a/pace_lg`; `pts_home = poss·(μ + O_h + D_a + h/2 + rest_h)/100`, and the same for away. Spread and total follow. Win prob = Φ(margin/σ), where σ is estimated from historical residuals. Fair ML comes from the win prob. Contributions (section 03) are a linear decomposition that is **tested to sum to the spread**.
3. **Availability (Phase 2):** box-score player value (transparent BPM-style formula, documented on `/nba/methodology`), minutes-weighted. Impact = −value × projected minutes share × (1 − pPlay). pPlay: out 0, doubtful 0.15, questionable 0.5, probable 0.9 (in `config/model.json`, labelled as assumptions). Each player's points impact shows in section 04.
4. **Market:** consensus = median across books. Edge = model spread − market spread (pts). Tiers `[1.5, 3, 5]` come from config.
5. **Props (Phase 3):** minutes projection × per-minute rates (EWMA, opponent-adjusted). 10,000 Monte Carlo sims with a seeded RNG, vectorized numpy (a fraction of a second per game). Edge = P(win at price) − breakeven(price). Weight = `min(1, GP/N0) × minutes_certainty`. Shown as "counted at X% toward a play".
6. **Honesty guard:** K, σ and the rest coefficients are fit on **2023-24 only**. 2024-25 and 2025-26 are held out and published untouched. No re-tuning after seeing the test number. The model version string is frozen per season.

---

## 6. Scheduling (GitHub Actions, DST-safe)

One workflow, `pipeline.yml`: `cron: "7,37 * * * *"` (every 30 min, off the top of the hour, which GitHub delays most). Step 1 runs `python -m pipeline gate`. It computes **now in ET** and asks, for each job, **"is it due, and not yet done for this ET game day?"** It doesn't ask "is it exactly hour X?". That survives the Nov 1 clock change, GitHub's 10-30 min cron delays and occasional dropped runs. It prints the due stages, and the workflow runs only those.

| Job | Due when (ET) |
|---|---|
| odds: morning | ≥ 10:00 on a game day, not yet taken |
| odds: afternoon | ≥ 14:00 |
| odds: pre-tip | ≥ first tip − 120 min (lands ~60–120 min before first tip) |
| odds: closing (featured only, 3 credits) | any game tipping within the next 40 min that has no snapshot in that window |
| injuries | every run from 09:00 until last tip on game days (every 30 min, about 2× your spec; it's free) |
| results + grade | from 00:30 ET onward, once all of the previous game day's games are final, then once more at 09:00 for stat corrections |
| schedule | once per ET day |

Mechanics: `concurrency: pipeline` (no overlapping runs). The workflow commits only if `data/` changed, then does `git pull --rebase` and pushes to `main` with `GITHUB_TOKEN`. Each push triggers a Vercel deploy, which is ≤ ~30/day against Hobby's 100/day. Secrets: `ODDS_API_KEY` in GitHub Actions secrets only. Vercel needs **no** secrets because it only builds static JSON.

**Fallback runner:** if the probe shows ESPN or the NBA PDF host blocking Actions IPs, the same CLI runs on your laptop via `launchd`. It would be one plist, with the same gate and the same commits. Downside: it only works when your Mac is awake. I'd tell you, not hide it.

**Vercel Hobby:** personal and non-commercial only. Ads, a paid tier or sponsorships mean moving to Pro ($20/mo). I'll flag it in the README.

---

## 7. Pages

| Route | Phase | Contents |
|---|---|---|
| `/` | 1 | Hero + tagline. Record tiles: Model ATS (W-L-P, %, units) and **CLV** next to it (P2); My Card (W-L-P, units, ROI, CLV). Links to boards. "How it works" ×3: possession-level box data / opponent-adjusted / locked then graded. |
| `/nba`, `/nba/[date]` | 1 | My Card for the date on top (if it exists). Strip: slate record · games · model disagrees 3+ · biggest gap. Games grouped by ET date. Card: tip ET, teams + records, projected scores, market line, model line (locked + current), pick + edge, sample badge (<15 GP), rest flags (P2), links. "UPDATED TUE 8:39 PM ET". |
| `/nba/game/[id]` | 1: 01–03 · 2: 04–07 | 01 The Number (+ backtest-sourced honesty line once P3 exists; until then: "No backtest published yet. Treat every gap as unproven.") · 02 Projected Score · 03 Where the Margin Comes From · 04 Availability · 05 How They Rate · 06 Team Ratings · 07 Line Movement |
| `/nba/record` | 1 | Every graded model pick vs first-seen. Tiles: All / 1.5+ / 3+ / 5+, each a filter. Break-even 52.4% at -110. "Small samples are noise." CLV column (P2). |
| `/nba/card` | 1 | My picks graded: W-L-P, units, ROI, CLV (P2), by market, amendment notes shown inline. |
| `/nba/gaps` | 2 | Games ranked by |edge|. |
| `/nba/rest` | 2 | B2B, 3-in-4, travel km, altitude per game (ET dates). |
| `/nba/props/[id]` | 3 | Favorites, per-player blocks, book table (names behind the flag), best price, edge, weight, distribution SVG. |
| `/nba/methodology` | 3 | Model spec, N, ATS%, CLV from the backtest, published as-is. |
| `/responsible-gambling` | 1 | Helpline pointer (number left for you to verify at ncpg.org.sg), information-only stance. |
| OG images | 3 | `game/[id]/opengraph-image`, `card/[date]/opengraph-image`. |

Footer on every page: your exact disclaimer text. No affiliate links, promo codes, CTAs, sportsbook links or sportsbook logos anywhere. A CI grep fails the build on known sportsbook domains in `src/`.

---

## 8. Design

Editorial analyst's notebook. Dark by default (`prefers-color-scheme` honored, manual toggle stored in localStorage). Headings use a serif (Newsreader); body and data use Inter with `font-variant-numeric: tabular-nums`; mono for line values. One accent (Q2). Win and loss are shown as text glyphs (W / L / P) plus a muted tone, never color alone. Section headers read `01 / THE NUMBER`. Mobile-first single column, two columns on board cards from `md`. WCAG AA contrast checked on both themes. Visible focus rings. Every chart has a caption and a hidden data table.

---

## 9. Tests (CI runs all of them; `ci.yml` on every push)

- **Grading (pytest):** -110 win +0.909u / loss −1u / push 0; −3.5 and −3 lines; push on whole numbers; totals same; ML at arbitrary prices; postponed/cancelled → void; props from box, DNP → void; card uses its logged line/price; model uses first-seen; CLV in pts and no-vig prob.
- **Immutability:** `write_once` raises if the file exists (unit test). `check-immutable.ts` in CI fails if any commit modifies or deletes `lines/first-seen/*` or `picks/model/*`, or changes a card pick whose game had tipped at commit time without a new `amendments[]` entry, or *adds* a pick after its game's tip.
- **Time:** the DST and midnight cases in §4, in both TS and Python.
- **Contracts:** Zod validation of all `data/` (prebuild); Pydantic↔Zod round-trip on fixtures; contributions sum to spread.
- **Budget guard:** stops before the reserve/daily cap, using a fake provider.
- **Parsers:** a recorded injury-report PDF and ESPN JSON fixtures.
- `next build` must pass before any phase is called done.

---

## 10. Phases

**Phase 1: shippable board.** Probe workflow from Actions → ESPN schedule/results → Odds API featured snapshots + budget guard → `lock` (first-seen + model picks) → backfill 2025-26 (priors) and ratings v1 → projections → grade → site: Home, Board, Game 01–03, Record, My Card + `/nba/card`, `npm run newcard`, footer, `/responsible-gambling` → CI + pipeline workflows → Vercel deploy → README runbook.
*Honest caveat:* the season opens **tonight**. Any game that tips before the pipeline is live has no first-seen line and won't be in the model record. I won't backfill locks, because the git timestamp is the proof.

**Phase 2:** injuries (PDF + fallback, logged), availability model + section 04, sections 05–07, line movement, rest/travel page, gaps page, closing lines + CLV everywhere.

**Phase 3:** backfill 2022-26, backtest + `/nba/methodology` (published whatever it says), prop pulls, sims, prop analyzer, OG share cards.

**Phase 4:** polish, Lighthouse/performance, SEO (metadata, sitemap, JSON-LD `SportsEvent`), accessibility pass.

---

## 11. Open questions → see chat (answers get folded in here)
