"""
Loads and validates config.yaml using Pydantic.

PEDAGOGICAL NOTE FOR READERS:
We validate configuration at load time and fail loudly if there's any invalid schema.
This is a production-minded practice: catching typos or wrong configurations immediately
on startup prevents silent errors or pipelines failing halfway through an expensive run.
"""
import os
import yaml
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class DomainConfig(BaseModel):
    primary: str
    focus_subdomain: Optional[str] = None

class CompetitorConfig(BaseModel):
    name: str
    sources: List[str] = Field(default_factory=list)

class WatchlistConfig(BaseModel):
    name: str
    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"analyst", "award", "conference"}
        if v not in allowed:
            raise ValueError(f"Watchlist type must be one of {allowed}, got '{v}'")
        return v

class ScheduleConfig(BaseModel):
    time: str
    timezone: str

class RunLimitsConfig(BaseModel):
    max_search_calls: int
    max_report_items: int
    cold_start_lookback_hours: int

    @field_validator("max_search_calls", "max_report_items", "cold_start_lookback_hours")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Run limit parameters must be positive integers")
        return v

class DeliveryConfig(BaseModel):
    to_email: Optional[str] = None

class AppConfig(BaseModel):
    llm_model: str
    domain: DomainConfig
    competitors: List[CompetitorConfig]
    watchlist: List[WatchlistConfig]
    schedule: ScheduleConfig
    run_limits: RunLimitsConfig
    delivery: DeliveryConfig

def load_config(config_path: str) -> AppConfig:
    """
    Loads config from the given path and parses/validates it using Pydantic.
    Fails loudly with clear validation error messages if validation fails.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            raw_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in configuration file: {e}")

    # Validate using Pydantic; this will throw ValidationError if structure is invalid
    return AppConfig.model_validate(raw_data)
