"""Backward-compatible config exports for legacy agent/tools modules."""

from app.core.config import get_settings

_settings = get_settings()

GOOGLE_API_KEY = _settings.google_api_key
GOOGLE_MAPS_API_KEY = _settings.google_maps_api_key
NEWS_API_KEY = _settings.news_api_key
