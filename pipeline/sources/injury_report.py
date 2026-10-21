"""Injury sources.

1. Official NBA injury report PDFs, listed at official.nba.com/nba-injury-report-2026-27-season/.
   Verified 2026-10-20: reachable from the maintainer's laptop, but 403 from GitHub Actions runners.
   Statuses: Out / Doubtful / Questionable / Probable / Available.
2. ESPN injuries JSON (fallback; works from Actions). Coarser: Out / Out-for-season / Day-To-Day.

Both return the same normalized rows: {player, team, status, reason, source}.
"""

from __future__ import annotations

import io
import re
from typing import Any

from ..teams import ESPN_TO_NBA
from .http import get, get_json

INDEX_URL = "https://official.nba.com/nba-injury-report-2026-27-season/"
ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"

OFFICIAL_STATUS = {"out": "out", "doubtful": "doubtful", "questionable": "questionable",
                   "probable": "probable", "available": "available"}
COLUMNS = ["GameDate", "GameTime", "Matchup", "Team", "PlayerName", "CurrentStatus", "Reason"]


def norm_name(s: str) -> str:
    """Name key that survives the PDF's dropped spaces and 'Last,First' order."""
    s = s.strip()
    if "," in s:
        last, first = s.split(",", 1)
        s = f"{first} {last}"
    return re.sub(r"[^a-z]", "", s.lower())


def pretty_name(s: str) -> str:
    if "," in s:
        last, first = s.split(",", 1)
        return f"{first.strip()} {last.strip()}"
    return s.strip()


def latest_report_url() -> str | None:
    html = get(INDEX_URL, source="nba-injury-index").text
    links = re.findall(r'https://ak-static\.cms\.nba\.com/referee/injury/Injury-Report_[0-9_A-Z-]+\.pdf', html)
    return links[-1] if links else None


def report_stamp(url: str) -> str | None:
    m = re.search(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf", url)
    return f"{m.group(1)} {m.group(2)}:{m.group(3)} {m.group(4)} ET" if m else None


def parse_official_pdf(pdf_bytes: bytes, team_by_squashed_name: dict[str, str]) -> list[dict]:
    """Column-position parser.

    Only page 1 has a header row; its column x-positions are reused for later pages. Date, time,
    matchup and team cells carry forward. A reason that wraps onto extra lines is split above and
    below its row (the cell is vertically centred), so each fragment joins the nearest player row.
    """
    import pdfplumber

    hdr: dict[str, float] = {}
    lines_all: list[dict[str, Any]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=1.5, keep_blank_chars=False)
            body_top = 60.0  # below the "Injury Report: ..." title
            for i, w in enumerate(words):
                if w["text"] == "Reason" and any(x["text"] == "Matchup" and abs(x["top"] - w["top"]) < 3 for x in words):
                    body_top = w["top"] + 2
                    for j, x in enumerate(words):
                        if abs(x["top"] - w["top"]) >= 3:
                            continue
                        nxt = words[j + 1]["text"] if j + 1 < len(words) else ""
                        key = {"Game": "GameDate" if nxt == "Date" else "GameTime", "Matchup": "Matchup",
                               "Team": "Team", "Player": "PlayerName", "Current": "CurrentStatus",
                               "Reason": "Reason"}.get(x["text"])
                        if key:
                            hdr.setdefault(key, x["x0"])
            if len(hdr) < 7:
                continue
            starts = sorted((x, k) for k, x in hdr.items())

            def col(x0: float) -> str:
                c = starts[0][1]
                for x, k in starts:
                    if x0 >= x - 2:
                        c = k
                return c

            lines: dict[float, dict[str, list[str]]] = {}
            for w in words:
                if w["top"] <= body_top or re.match(r"^Page\d", w["text"]) or w["text"] == "Page":
                    continue
                key = next((k for k in lines if abs(k - w["top"]) <= 2), w["top"])
                lines.setdefault(key, {}).setdefault(col(w["x0"]), []).append(w["text"])
            for top in sorted(lines):
                lines_all.append({"top": top, "page": page.page_number,
                                  **{k: " ".join(v) for k, v in lines[top].items()}})

    players: list[dict] = []
    fragments: list[tuple[int, float, str]] = []
    team = matchup = None
    for r in lines_all:
        if r.get("Matchup"):
            matchup = r["Matchup"].replace(" ", "")
        if r.get("Team"):
            squashed = re.sub(r"[^a-z0-9]", "", r["Team"].lower())
            team = team_by_squashed_name.get(squashed, team)
        name = r.get("PlayerName", "")
        status = (r.get("CurrentStatus") or "").strip().lower()
        if name and status in OFFICIAL_STATUS:
            players.append({"player": pretty_name(name), "key": norm_name(name), "team": team,
                            "status": OFFICIAL_STATUS[status], "matchup": matchup, "source": "nba_official",
                            "_page": r["page"], "_top": r["top"], "_reason": [(r["top"], r.get("Reason", ""))]})
        elif r.get("Reason") and not name and "SUBMITTED" not in " ".join(str(v) for v in r.values()):
            fragments.append((r["page"], r["top"], r["Reason"]))
    for page, top, text in fragments:
        same = [p for p in players if p["_page"] == page]
        if same:
            nearest = min(same, key=lambda p: (abs(p["_top"] - top), p["_top"] > top))
            nearest["_reason"].append((top, text))
    out = []
    for p in players:
        reason = " ".join(t for _, t in sorted(p.pop("_reason")) if t and t != "-").strip()
        p.pop("_page"), p.pop("_top")
        if p["team"]:
            out.append({**p, "reason": reason or None})
    return out


def fetch_official(team_by_squashed_name: dict[str, str]) -> tuple[list[dict], str | None]:
    url = latest_report_url()
    if not url:
        raise RuntimeError("no injury report PDF linked on the index page")
    pdf = get(url, source="nba-injury-pdf").content
    return parse_official_pdf(pdf, team_by_squashed_name), report_stamp(url)


def fetch_espn() -> list[dict]:
    d = get_json(ESPN_URL, source="espn-injuries")
    out = []
    for t in d.get("injuries", []):
        for i in t.get("injuries", []):
            a = i.get("athlete") or {}
            ab = (a.get("team") or {}).get("abbreviation", "")
            st = (i.get("status") or "").lower()
            status = "out" if st.startswith("out") else "questionable" if "day" in st else None
            if status is None:
                continue
            det = i.get("details") or {}
            reason = " ".join(x for x in (det.get("type"), det.get("detail")) if x)
            espn_id = None
            for link in a.get("links", []):
                m = re.search(r"/id/(\d+)", link.get("href", ""))
                if m:
                    espn_id = m.group(1)
                    break
            out.append({"player": a.get("displayName", ""), "key": norm_name(a.get("displayName", "")),
                        "team": ESPN_TO_NBA.get(ab, ab), "status": status, "reason": reason or None,
                        "espnId": espn_id, "source": "espn",
                        "espnStatus": (det.get("fantasyStatus") or {}).get("abbreviation")})
    return out
