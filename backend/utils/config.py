import logging
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MAPBOX_TOKEN: str = os.getenv("MAPBOX_ACCESS_TOKEN", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

DEFAULT_SEARCH_RADIUS_KM: float = 30.0
DEFAULT_MAX_RESULTS: int = 5

ROUTE_MODES = {"driving", "walking", "bicycling"}


def get_mapbox_token() -> str:
    if not MAPBOX_TOKEN:
        logger.warning("MAPBOX_ACCESS_TOKEN not set - place search and routing disabled")
        return ""
    return MAPBOX_TOKEN


def get_gemini_key() -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment")
    return GEMINI_API_KEY