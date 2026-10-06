from typing import Any
from urllib.parse import quote_plus

import requests

WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_live_weather(location: str) -> dict[str, Any]:
    """
    Fetch live weather conditions and 3-day forecast for any city or location using Open-Meteo API.
    """
    trimmed = location.strip()
    if not trimmed:
        return {"ok": False, "error": "Location cannot be empty."}

    # 1. Geocode location to lat/lon
    try:
        geo_res = requests.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={quote_plus(trimmed)}&count=1&language=en&format=json",
            timeout=6,
        )
        if geo_res.status_code != 200 or not geo_res.json().get("results"):
            return {"ok": False, "location": trimmed, "error": f"Could not find coordinates for location '{trimmed}'."}

        geo_data = geo_res.json()["results"][0]
        lat = geo_data["latitude"]
        lon = geo_data["longitude"]
        place_name = f"{geo_data.get('name')}, {geo_data.get('admin1', '')} {geo_data.get('country', '')}".strip()

        # 2. Fetch current weather and daily forecast
        weather_res = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto",
            timeout=6,
        )
        if weather_res.status_code != 200:
            return {"ok": False, "location": place_name, "error": "Weather forecast service is temporarily unreachable."}

        data = weather_res.json()
        current = data.get("current", {})
        daily = data.get("daily", {})

        weather_code = current.get("weather_code", 0)
        condition = WEATHER_CODE_MAP.get(weather_code, "Partly Cloudy")

        forecast_list = []
        dates = daily.get("time", [])[:3]
        max_temps = daily.get("temperature_2m_max", [])[:3]
        min_temps = daily.get("temperature_2m_min", [])[:3]
        codes = daily.get("weather_code", [])[:3]

        for i in range(len(dates)):
            forecast_list.append({
                "date": dates[i],
                "condition": WEATHER_CODE_MAP.get(codes[i], "Fair"),
                "high_c": max_temps[i],
                "low_c": min_temps[i],
            })

        return {
            "ok": True,
            "location": place_name,
            "latitude": lat,
            "longitude": lon,
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "condition": condition,
            "forecast_3day": forecast_list,
        }
    except Exception as exc:
        return {"ok": False, "location": trimmed, "error": f"Failed to retrieve weather data: {exc}"}
