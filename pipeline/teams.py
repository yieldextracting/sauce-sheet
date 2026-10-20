"""Team identity mapping between providers. Names only, no numbers."""

from __future__ import annotations

# ESPN uses a few non-standard abbreviations. Everything we store uses the NBA standard.
ESPN_TO_NBA = {
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
    "UTAH": "UTA",
    "WSH": "WAS",
}

# Full-name aliases seen across providers (The Odds API uses "Los Angeles Clippers").
NAME_ALIASES = {
    "LA Clippers": "LAC",
    "Los Angeles Clippers": "LAC",
}


def norm_abbr(espn_abbr: str) -> str:
    return ESPN_TO_NBA.get(espn_abbr, espn_abbr)


def name_index(teams: list[dict]) -> dict[str, str]:
    """Map every known display name -> abbr."""
    idx = dict(NAME_ALIASES)
    for t in teams:
        idx[t["name"]] = t["abbr"]
    return idx
