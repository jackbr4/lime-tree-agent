import httpx
import time

# Precise location coordinates for the lime tree's position
LATITUDE = 52.353099007332396
LONGITUDE = 4.899946192795255

# MET Norway endpoint — primary source
# Excellent for Northern Europe, free, no API key required.
# Requires a User-Agent header identifying the app per their terms of use.
MET_NORWAY_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
MET_NORWAY_HEADERS = {
    "User-Agent": "LimeTreeAgent/1.0 github.com/jackbr4/lime-tree-agent"
}

# Open-Meteo endpoint — fallback source
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather_met_norway() -> dict:
    """
    Fetch weather from MET Norway (api.met.no).
    Returns a normalised weather dict matching the agent's expected format.

    MET Norway returns hourly timeseries data. We take the first entry
    as current conditions and build a 7-day daily summary from the data.
    """
    from datetime import datetime, timezone, timedelta
    from collections import defaultdict

    params = {
        "lat": LATITUDE,
        "lon": LONGITUDE,
    }

    response = httpx.get(
        MET_NORWAY_URL,
        params=params,
        headers=MET_NORWAY_HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    raw = response.json()

    timeseries = raw["properties"]["timeseries"]

    # Current conditions — first entry in the timeseries
    current_entry = timeseries[0]
    current_instant = current_entry["data"]["instant"]["details"]
    current_1h = current_entry["data"].get("next_1_hours", {}).get("details", {})

    current = {
        "temperature_c": current_instant.get("air_temperature"),
        "humidity_pct": current_instant.get("relative_humidity"),
        "precipitation_mm": current_1h.get("precipitation_amount", 0.0),
        "cloud_cover_pct": current_instant.get("cloud_area_fraction"),
        "wind_speed_kmh": round(
            current_instant.get("wind_speed", 0) * 3.6, 1
        ),  # convert m/s to km/h
    }

    # Build 7-day daily forecast by grouping hourly entries by date
    daily_data = defaultdict(lambda: {"precip": 0.0, "temps": []})
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=7)

    for entry in timeseries:
        ts = datetime.fromisoformat(entry["time"].replace("Z", "+00:00"))
        if ts > cutoff:
            break
        date_str = ts.strftime("%Y-%m-%d")
        instant = entry["data"]["instant"]["details"]
        next_1h = entry["data"].get("next_1_hours", {}).get("details", {})

        temp = instant.get("air_temperature")
        if temp is not None:
            daily_data[date_str]["temps"].append(temp)

        precip = next_1h.get("precipitation_amount", 0.0)
        if precip:
            daily_data[date_str]["precip"] += precip

    forecast = []
    for date_str in sorted(daily_data.keys()):
        temps = daily_data[date_str]["temps"]
        forecast.append({
            "date": date_str,
            "precipitation_mm": round(daily_data[date_str]["precip"], 1),
            "temp_max_c": max(temps) if temps else None,
            "temp_min_c": min(temps) if temps else None,
        })

    return {"current": current, "forecast": forecast}


def get_weather_open_meteo() -> dict:
    """
    Fetch weather from Open-Meteo — used as fallback if MET Norway fails.
    Returns a normalised weather dict matching the agent's expected format.
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "cloud_cover",
            "wind_speed_10m",
        ],
        "daily": [
            "precipitation_sum",
            "temperature_2m_max",
            "temperature_2m_min",
        ],
        "timezone": "Europe/Amsterdam",
        "forecast_days": 7,
    }

    response = httpx.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    raw = response.json()

    current = raw["current"]
    daily = raw["daily"]

    forecast = []
    for i in range(len(daily["time"])):
        forecast.append({
            "date": daily["time"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
        })

    return {
        "current": {
            "temperature_c": current["temperature_2m"],
            "humidity_pct": current["relative_humidity_2m"],
            "precipitation_mm": current["precipitation"],
            "cloud_cover_pct": current["cloud_cover"],
            "wind_speed_kmh": current["wind_speed_10m"],
        },
        "forecast": forecast,
    }


def get_weather(retries: int = 3, retry_delay: float = 5.0) -> dict:
    """
    Fetch weather data with automatic failover.

    Order:
    1. MET Norway (primary — best for Amsterdam)
    2. Open-Meteo (fallback — global coverage)
    3. Empty dict (last resort — agent runs on sensor data only)

    Each source is retried up to `retries` times before moving
    to the next source.
    """
    sources = [
        ("MET Norway", get_weather_met_norway),
        ("Open-Meteo", get_weather_open_meteo),
    ]

    for source_name, fetch_fn in sources:
        for attempt in range(1, retries + 1):
            try:
                print(f"Fetching weather from {source_name} (attempt {attempt}/{retries})...")
                data = fetch_fn()
                print(f"Weather fetched successfully from {source_name}.")
                return data
            except Exception as e:
                if attempt < retries:
                    print(f"{source_name} error: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"{source_name} failed after {retries} attempts: {e}")
                    break  # try next source

    # Both sources exhausted — return empty so agent can still run
    print("All weather sources failed. Proceeding with sensor data only.")
    return {
        "current": {
            "temperature_c": "unavailable",
            "humidity_pct": "unavailable",
            "precipitation_mm": "unavailable",
            "cloud_cover_pct": "unavailable",
            "wind_speed_kmh": "unavailable",
        },
        "forecast": [],
    }


if __name__ == "__main__":
    import json
    data = get_weather()
    print(json.dumps(data, indent=2))
