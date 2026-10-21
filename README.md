# Sauce Sheet

> Every line. Every number. Graded in public.

An NBA projection model shown next to the market, a human "My Card" layer on top, and every pick graded
in public. Next.js static site + Python pipeline. Git is the database.

Information and entertainment only. Not betting advice. No affiliate links, promo codes, or sportsbook links.

---

## Daily routine

```bash
git pull                 # get the pipeline's latest data
npm run newcard          # scaffolds content/cards/<today ET>.mdx with the slate, lines, spots, injuries
# write your picks in the frontmatter and your takes in the body
npm run validate         # optional: checks the card before you push
git add content/cards && git commit -m "card: $(date +%F)" && git push
```

That's it. Vercel redeploys on the push, and grading happens automatically after the games.

**Card rules** (CI enforces them):
- Picks are locked at tip. You can edit freely before your game starts.
- After tip, a change needs a new entry in `amendments:` (`at`, `pickId`, `note`). It shows on the site.
- You can't add or remove a pick after its game has tipped.
- Your written takes (the body) are locked after the slate's first tip. Fix with an amendment whose `pickId` is `takes`.
- `units` = amount risked. A 1u play at -110 wins +0.909u or loses 1u.

Card format:

```yaml
---
date: 2026-10-21
picks:
  - id: 1
    game: 20261021-BOS-DET        # from the slate block newcard writes
    market: spread                # spread | total | moneyline | prop
    side: BOS                     # team abbr, or over/under for total/prop
    line: -1.5                    # omit for moneyline
    odds: -110
    units: 1
    confidence: 3                 # 1-5
    why: One line on why.
  - id: 2
    game: 20261021-BOS-DET
    market: prop
    player: "Jayson Tatum"
    stat: pts                     # pts | reb | ast | fg3m | pra
    side: over
    line: 27.5
    odds: -115
    units: 0.5
    confidence: 2
amendments: []
---
```

---

## How it runs

| What | Where | When |
|---|---|---|
| Schedule, results, box scores | GitHub Actions → ESPN | every 30 min (only fetches what's due) |
| Odds snapshots | GitHub Actions → The Odds API (or ESPN fallback) | 10:00 ET, 14:00 ET, ~2h before first tip, and ~30 min before each tip (closing line) |
| Injury report | GitHub Actions → ESPN (official NBA PDF when run from your laptop and it answers) | every run from 09:00 ET until the last tip; re-projects when it changes |
| Lock first-seen lines + model picks | GitHub Actions | right after every odds pull |
| Ratings, projections, grading | GitHub Actions | after new finals, and daily |
| Backfill past seasons, fit hyperparameters | **your laptop** | once a season |

`pipeline.yml` is scheduled every 30 minutes in UTC, but GitHub runs schedules far less reliably than that
(on day one: twice in 8 hours). So once a run starts, it **loops every 10 minutes** while there is work in the
next few hours (`python -m pipeline busy`), for up to ~5.5 hours. The next scheduled run picks up from there.
`python -m pipeline auto` works out what's due **in ET**, using "due and not done yet today" rules, so the
November and March clock changes need no edits. Each change is committed to `main`, which triggers a Vercel
deploy.

Run any stage by hand:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
.venv/bin/python -m pipeline run --stage all
.venv/bin/python -m pipeline run --stage pull_odds,lock
.venv/bin/python -m pipeline gate          # prints what's due right now, runs nothing
.venv/bin/python -m pipeline auto          # what Actions runs
```

Stages: `pull_schedule`, `pull_results`, `build_ratings`, `project_games`, `pull_odds`, `lock`, `grade`.
Local-only: `backfill --seasons 2023 2024 2025 2026`, `fit`.

---

## When something fails

GitHub emails you when a scheduled workflow fails. Open **Actions → pipeline → the red run** and read the log.

| Symptom | Likely cause | Fix |
|---|---|---|
| `FetchError: espn ... HTTP 403` | ESPN blocking GitHub's IPs | Run **Actions → probe**. If ESPN is 403 from Actions, run `pipeline auto` from your laptop (see *Laptop fallback*) and tell the maintainer. |
| `BudgetExceeded` | Odds API credit guard tripped (reserve, daily or monthly cap) | Intended. Check `data/logs/odds-credits.jsonl`. Raise caps in `config/odds.json` only if you've checked the plan. |
| `ODDS_API_KEY not set` | Secret missing and provider forced to `the_odds_api` | Add the repo secret, or set `"provider": "auto"` to fall back to ESPN. |
| `refusing to overwrite write-once file` | Code tried to rewrite a locked line | A bug. Do **not** delete the file. Open an issue. |
| `data/... failed validation` | A source changed its format | The bad data was not committed. Fix the parser, add a fixture test, re-run. |
| Vercel build failed | Same as above, or a bad card | `npm run validate` locally shows the exact file and field. |
| Push rejected / conflict | You and the bot pushed at once | `git pull --rebase` and push again. Cards and data never touch the same files. |
| Missed snapshot | GitHub delayed or dropped a cron run | Nothing to do. The next run catches up because jobs are "due and not done". If a game had no snapshot shortly before tip, its closing line is older, and the record marks that CLV with `*`. |
| No pipeline run for hours on a game day | GitHub didn't start a scheduled run | Actions → pipeline → **Run workflow**. It loops through the evening on its own. |
| `injuries: ... fallback after: nba_official ... 403` | The official report blocks that IP | Expected in Actions (it only tries ESPN there). Locally it falls back to ESPN automatically. |
| `injury pull failed on every source` | ESPN injuries down too | Projections keep the last report for up to 30 hours, then drop the injury adjustment rather than use stale data. |

Every pull is logged in `data/logs/pulls.jsonl`, and every Odds API call in `data/logs/odds-credits.jsonl`
(remaining quota after each call).

**Laptop fallback:** `ODDS_API_KEY=... .venv/bin/python -m pipeline auto && git add data reference && git commit -m "data: manual" && git push`.

---

## Data sources (verified 2026-10-20)

- **ESPN site API** for schedule, scores, box scores and history. `cdn.nba.com`, `stats.nba.com` and
  `www.nba.com` return 403 from the maintainer's Singapore connection, so nothing depends on them.
- **The Odds API** for lines from every US book. Without a key, the pipeline uses the single book shown on
  ESPN's scoreboard. Snapshots record which provider they came from.
- **OpenStreetMap Nominatim + Open-Meteo** for venue coordinates and elevation (travel distance, altitude).
  These are cached in `reference/venues.json`.
- **Injuries:** ESPN's injury feed (works everywhere; statuses are only Out and Day-To-Day). The official NBA
  injury report PDFs (`official.nba.com/nba-injury-report-2026-27-season/`) are parsed when reachable. They were
  reachable from the laptop on Oct 20, 403 from GitHub Actions, and 403 from the laptop too by that evening, so
  they are a bonus, not a dependency. Every pull is logged in `data/logs/pulls.jsonl`. A snapshot is saved to
  `data/injuries/` only when the report changes.

## Odds API budget

Featured markets (spreads, totals, moneylines; US region) cost 3 credits per snapshot for every game. Props
(Phase 3) cost about 4 credits per game per snapshot. Expect about 3.4k credits/month with props, so the
**20K plan ($30/mo)** is plenty. Guard rails are in `config/odds.json`: monthly cap 15,000, reserve 1,500,
daily cap 250.

## The model (v1)

- Opponent-adjusted offensive/defensive efficiency per 100 possessions, plus pace. Solved by ridge
  regression across the season, with home court, altitude, rest days, back-to-back, 3-in-4 and travel terms.
- Shrinks toward last season's ratings regressed toward the mean. The prior counts as K pseudo-games per
  team, so its weight is K/(K+GP). A "small sample" badge shows until both teams reach 15 games.
- Projection gives both scores, spread, total, win probability (normal, σ from historical residuals) and a fair
  moneyline. The margin breakdown sums exactly to the projected spread.
- K, the regression amount and σ are chosen by walk-forward on **2023-24 only**. Schedule-spot
  coefficients are averaged over 2022-23 and 2023-24 full-season fits (one season alone is too noisy for
  altitude). All of it is in `data/model/params.json` (`python -m pipeline fit`). 2024-25 and 2025-26 are never
  used to choose anything, so they stay clean for the backtest.
- **Availability (v2):** a player's value is Hollinger Game Score per 36 minutes above replacement level (the
  minutes-weighted rate of players under 12 mpg), times expected minutes (a decaying average over the team's
  games, so a long absence fades out instead of being double-counted against team ratings). Points lost =
  beta × value × (1 − P(play)). Beta is fit on 2023-24 by regressing the model's margin errors on who actually
  sat: **0.43 ± 0.14**. It's real but modest: it cuts the 2023-24 margin RMSE only from 14.04 to 13.99. P(play):
  out 0, doubtful 15%, questionable 50%, probable 90% (assumptions in `config/model.json`). ESPN's Day-To-Day
  counts as questionable. A listing applies to the team's next game. "Out" also carries to later games.
- Market consensus is the median line across books, rounded to the half point. Edge = model line minus
  market line. Edge tiers live in `config/model.json`.

## Grading

- Model picks are graded against the **first line ever seen** (`data/lines/first-seen/`, write-once,
  enforced in code and in CI) at -110. Win +0.909u, loss -1u, push 0.
- Card picks are graded at the line and price you logged.
- Void: postponed, cancelled or rescheduled-to-another-day games, and props for players who didn't play.
- CLV is measured against the closing consensus (the last snapshot before tip). Spreads and totals are measured in
  points, moneylines in no-vig win probability. Each closing line records how many minutes before tip it was
  taken.

## Setup (once)

1. Create the GitHub repo and push. Add repo secret `ODDS_API_KEY` (Settings → Secrets → Actions).
2. Vercel → New Project → import the repo. Framework: Next.js, no env vars needed (the site only reads JSON).
3. Actions → enable workflows. Run **probe** once, then **pipeline** once by hand.
4. Vercel **Hobby is personal, non-commercial use only.** If you add ads, sponsorships, paid tiers or
   affiliate income, you need Pro (and, given Singapore's Gambling Control Act, proper legal advice first).

## Renaming

Change `config/brand.json`. Both the site and the pipeline read it.

## Development

```bash
nvm use                  # Node 22
npm install
npm run dev              # http://localhost:3000
npm test                 # vitest
.venv/bin/python -m pytest pipeline/tests
npm run build            # validates all data first
```
