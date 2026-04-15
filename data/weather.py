import httpx

# Precise location coordinates for the lime tree's position
LATITUDE = 52.353099007332396
LONGITUDE = 4.899946192795255

BASE_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather() -> dict:
    """
    Fetch current conditions and a 7-day forecast.

    We request:
    - current: temperature, humidity, precipitation, cloud cover, wind speed
    - daily: precipitation sum and max/min temperature for the next 7 days

    This gives the agent enough to reason about watering schedules,
    sun stress, and whether to act today vs. wait for rain.
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

    response = httpx.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    raw = response.json()

    current = raw["current"]
    daily = raw["daily"]

    # Zip the daily arrays into a list of day objects — much easier to read
    # in a prompt than separate arrays
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


if __name__ == "__main__":
    import json
    data = get_weather()
    print(json.dumps(data, indent=2))
