"""Typed access to config/*.json."""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel

from .io import read_json
from .paths import CONFIG


class Brand(BaseModel):
    name: str
    tagline: str
    url: str


class Site(BaseModel):
    showBookNames: bool
    season: str
    espnSeasonYear: int
    seasonStartEt: str
    timezone: str


class FitConfig(BaseModel):
    fitSeason: str
    priorSeasonForFit: str
    kGrid: list[float]
    regressionGrid: list[float]


class ModelConfig(BaseModel):
    version: str
    edgeTiers: list[float]
    sampleBadgeGames: int
    projectionHorizonDays: int
    modelPickPrice: int
    altitudeThresholdM: float
    fit: FitConfig


class Budget(BaseModel):
    monthlyCap: int
    reserve: int
    dailyCap: int


class Snapshots(BaseModel):
    morningEtHour: int
    afternoonEtHour: int
    preTipMinutesBeforeFirstTip: int
    closingWindowMinutes: int


class OddsConfig(BaseModel):
    provider: str  # "auto" | "the_odds_api" | "espn"
    sport: str
    regions: list[str]
    featuredMarkets: list[str]
    budget: Budget
    snapshots: Snapshots


@lru_cache
def brand() -> Brand:
    return Brand(**read_json(CONFIG / "brand.json"))


@lru_cache
def site() -> Site:
    return Site(**read_json(CONFIG / "site.json"))


@lru_cache
def model() -> ModelConfig:
    return ModelConfig(**read_json(CONFIG / "model.json"))


@lru_cache
def odds() -> OddsConfig:
    return OddsConfig(**read_json(CONFIG / "odds.json"))


def season_label(espn_year: int) -> str:
    """ESPN season year 2027 -> '2026-27'."""
    return f"{espn_year - 1}-{str(espn_year)[-2:]}"
