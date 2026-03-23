"""Configuration management via Pydantic Settings + config.yaml + .env."""

from pathlib import Path
from functools import lru_cache

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml_config() -> dict:
    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml = _load_yaml_config()
_scoring = _yaml.get("scoring", {})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_prefix="LIBRO_",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///data/libro.db"

    # Keepa
    keepa_api_key: str = ""
    keepa_tokens_per_minute: int = 10

    # Scraping
    scraper_headless: bool = True
    scraper_delay_min: float = _yaml.get("scraper_delay_min", 2.0)
    scraper_delay_max: float = _yaml.get("scraper_delay_max", 5.0)
    amazon_marketplace: str = _yaml.get("amazon_marketplace", "com")

    # Generation
    default_trim_size: str = _yaml.get("default_trim_size", "6x9")
    default_page_count: int = _yaml.get("default_page_count", 120)
    output_dir: Path = PROJECT_ROOT / "data" / "output"
    covers_template_dir: Path = PROJECT_ROOT / "data" / "covers"

    # Scoring weights
    weight_demand: float = _scoring.get("weight_demand", 0.4)
    weight_competition: float = _scoring.get("weight_competition", 0.2)
    weight_trend: float = _scoring.get("weight_trend", 0.2)
    weight_stability: float = _scoring.get("weight_stability", 0.1)
    weight_price: float = _scoring.get("weight_price", 0.1)

    # Scoring thresholds
    min_bsr_for_demand: int = _yaml.get("min_bsr_for_demand", 500_000)
    max_reviews_for_low_competition: int = _yaml.get("max_reviews_for_low_competition", 50)
    min_opportunity_score: float = _yaml.get("min_opportunity_score", 0.6)
    min_price_for_margin: float = _yaml.get("min_price_for_margin", 6.99)

    # Tracking
    evaluation_period_days: int = _yaml.get("evaluation_period_days", 14)
    snapshot_interval_hours: int = _yaml.get("snapshot_interval_hours", 12)

    # Similarity guard
    similarity_title_threshold: float = _yaml.get("similarity_title_threshold", 0.7)
    similarity_max_similar_active: int = _yaml.get("similarity_max_similar_active", 3)


@lru_cache
def get_settings() -> Settings:
    return Settings()
