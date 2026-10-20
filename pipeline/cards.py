"""Read My Card files (content/cards/YYYY-MM-DD.mdx). Frontmatter only; the body is for the site."""

from __future__ import annotations

from typing import Literal

import frontmatter
from pydantic import BaseModel, field_validator

from .paths import CARDS_DIR


class CardPick(BaseModel):
    id: str
    game: str
    market: Literal["spread", "total", "moneyline", "prop"]
    side: str
    player: str | None = None
    stat: Literal["pts", "reb", "ast", "fg3m", "pra"] | None = None
    line: float | None = None
    odds: int
    units: float
    confidence: int
    why: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _id_str(cls, v):
        return str(v)


class Amendment(BaseModel):
    at: str
    pickId: str
    note: str

    @field_validator("pickId", mode="before")
    @classmethod
    def _id_str(cls, v):
        return str(v)


class Card(BaseModel):
    date: str
    picks: list[CardPick] = []
    amendments: list[Amendment] = []

    @field_validator("date", mode="before")
    @classmethod
    def _date_str(cls, v):
        return str(v)


def load_all() -> list[Card]:
    cards = []
    for p in sorted(CARDS_DIR.glob("*.mdx")):
        meta = frontmatter.load(p).metadata
        card = Card(**meta)
        if card.date != p.stem:
            raise ValueError(f"{p.name}: frontmatter date {card.date} does not match filename")
        cards.append(card)
    return cards
