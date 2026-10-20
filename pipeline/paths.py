"""Filesystem layout. Every path the pipeline touches is defined here."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
DATA = ROOT / "data"
CONTENT = ROOT / "content"
REFERENCE = ROOT / "reference"

TEAMS = DATA / "teams.json"
SCHEDULE_DIR = DATA / "schedule"
RESULTS_DIR = DATA / "results"
HISTORY_DIR = DATA / "history"
LINES_DIR = DATA / "lines"
SNAPSHOTS_DIR = LINES_DIR / "snapshots"
FIRST_SEEN_DIR = LINES_DIR / "first-seen"
CLOSING_DIR = LINES_DIR / "closing"
CURRENT_LINES = LINES_DIR / "current.json"
MODEL_PICKS_DIR = DATA / "picks" / "model"
RATINGS_DIR = DATA / "ratings"
PROJECTIONS_DIR = DATA / "projections"
GRADES_DIR = DATA / "grades"
MODEL_PARAMS = DATA / "model" / "params.json"
LOGS_DIR = DATA / "logs"
PULL_LOG = LOGS_DIR / "pulls.jsonl"
CREDIT_LOG = LOGS_DIR / "odds-credits.jsonl"
STATE = LOGS_DIR / "state.json"
CARDS_DIR = CONTENT / "cards"
VENUES = REFERENCE / "venues.json"


def schedule_path(season: str) -> Path:
    return SCHEDULE_DIR / f"{season}.json"


def results_dir(season: str) -> Path:
    return RESULTS_DIR / season
