"""
Centralized External API Endpoints and Service URLs for JARVIS.

All external service endpoints are centralized here in the backend to ensure:
1. No external URLs or secret tokens are leaked to the frontend.
2. Single source of truth for all external API endpoints across providers.
3. Clean configuration and testability.
"""

# Google Gemini API
GEMINI_API_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

# Groq API
GROQ_API_BASE_URL: str = "https://api.groq.com/openai/v1"
GROQ_CHAT_URL: str = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TRANSCRIBE_URL: str = "https://api.groq.com/openai/v1/audio/transcriptions"

# OpenAI API
OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
OPENAI_CHAT_URL: str = "https://api.openai.com/v1/chat/completions"

# Anthropic API
ANTHROPIC_API_BASE_URL: str = "https://api.anthropic.com/v1"
ANTHROPIC_MESSAGES_URL: str = "https://api.anthropic.com/v1/messages"

# DuckDuckGo Search
DUCKDUCKGO_HTML_URL: str = "https://html.duckduckgo.com/html/"
DUCKDUCKGO_API_URL: str = "https://api.duckduckgo.com/"

# Live Search & Knowledge Endpoints
GOOGLE_NEWS_RSS_URL: str = "https://news.google.com/rss/search"
WIKIPEDIA_API_URL: str = "https://en.wikipedia.org/w/api.php"

# Open-Meteo Weather
OPEN_METEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
