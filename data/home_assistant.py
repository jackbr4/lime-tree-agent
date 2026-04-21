import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# Your HA base URL and auth token come from environment variables.
# Never hardcode secrets — if this repo ever becomes public, you're safe.
HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")

# HA's REST API requires a Bearer token in the Authorization header.
# This is standard OAuth-style auth — you'll see this pattern everywhere.
HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

# These are the four sensors — entity IDs pulled from Home Assistant.
SENSORS = {
    "conductivity": "sensor.lime_tree_sensor_conductivity",
    "illuminance": "sensor.lime_tree_sensor_illuminance",
    "moisture": "sensor.plant_sensor_1548_moisture",
    "temperature": "sensor.lime_tree_sensor_temperature",
}


def get_sensor_state(entity_id: str) -> dict:
    """
    Fetch a single sensor's current state from Home Assistant.
    HA's REST API returns a JSON object for each entity with
    a 'state' (the value) and 'attributes' (friendly name, etc.)
    """
    url = f"{HA_URL}/api/states/{entity_id}"
    response = httpx.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()  # throws if HA returns an error
    return response.json()


def get_plant_data() -> dict:
    """
    Fetch all four sensor readings and return them as a clean dict.
    This is what the agent will actually use — a single call that
    gives you everything about the lime tree's current state.
    """
    readings = {}

    for name, entity_id in SENSORS.items():
        data = get_sensor_state(entity_id)
        readings[name] = {
            "value": data["state"],
            "unit": data["attributes"].get("unit_of_measurement", ""),
            "friendly_name": data["attributes"].get("friendly_name", name),
        }

    return readings


def get_entity_history(entity_id: str, days: int = 7) -> list:
    """
    Fetch historical state changes for a single entity from HA's history API.

    HA logs every state change, which for sensors means many readings per day.
    We sample this down to one reading per 12-hour window so we get a clean,
    consistent trend that matches the agent's twice-daily run frequency.

    Returns a list of dicts with 'timestamp' and 'value' keys, oldest first.
    """
    from datetime import datetime, timedelta, timezone

    # Calculate start time — HA expects ISO 8601 format with timezone
    start_time = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = f"{HA_URL}/api/history/period/{start_time}"

    params = {
        "filter_entity_id": entity_id,
        "minimal_response": "true",  # reduces payload — we only need state + timestamp
        "no_attributes": "true",
    }

    response = httpx.get(url, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    raw = response.json()

    if not raw or not raw[0]:
        return []

    # HA returns a list of lists — one inner list per entity requested
    states = raw[0]

    # Sample to one reading per 12-hour window
    # This keeps the history clean and avoids overwhelming the prompt
    sampled = []
    last_window = None

    for state in states:
        try:
            value = float(state["state"])
        except (ValueError, KeyError):
            continue  # skip unavailable or non-numeric states

        # Parse timestamp and determine which 12-hour window it falls in
        ts = datetime.fromisoformat(
            state["last_changed"].replace("Z", "+00:00")
        )
        # Window key: date + AM/PM (0 = midnight–noon, 1 = noon–midnight)
        window = (ts.date(), ts.hour >= 12)

        if window != last_window:
            sampled.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M"),
                "value": value,
            })
            last_window = window

    return sampled


def get_sensor_histories() -> dict:
    """
    Fetch 7-day history for moisture and conductivity.

    We only pull history for these two sensors because:
    - Moisture: needed to reason about wet/dry cycle phase
    - Conductivity: needed to reason about fertilizer trends and salt buildup
    - Illuminance and temperature are better reasoned about via current reading
      + weather forecast rather than historical sensor logs
    """
    return {
        "moisture": get_entity_history("sensor.plant_sensor_1548_moisture"),
        "conductivity": get_entity_history("sensor.lime_tree_sensor_conductivity"),
    }


def get_tree_location() -> str:
    """
    Read the indoor/outdoor toggle from HA.
    input_boolean.lime_tree_outdoor:
      - 'on'  = outdoor
      - 'off' = indoor

    This is the single source of truth for tree placement.
    The TREE_LOCATION env var is no longer used.
    """
    data = get_sensor_state("input_boolean.lime_tree_outdoor")
    return "outdoor" if data["state"] == "on" else "indoor"


def set_briefing(briefing_text: str) -> bool:
    """
    Write the briefing to HA across six input_text entities.

    HA caps input_text at 255 characters each, so we split the
    briefing into six chunks and write them to six separate
    entities. The dashboard card stitches them back together.

    Returns True if all writes succeeded, False if any failed.
    """
    entities = [
        "input_text.lime_tree_briefing",
        "input_text.lime_tree_briefing_2",
        "input_text.lime_tree_briefing_3",
        "input_text.lime_tree_briefing_4",
        "input_text.lime_tree_briefing_5",
        "input_text.lime_tree_briefing_6",
    ]

    # Split briefing into 255-char chunks
    chunks = [briefing_text[i:i+255] for i in range(0, len(briefing_text), 255)]

    # Pad to 6 chunks so unused entities get cleared
    while len(chunks) < 6:
        chunks.append("")

    success = True
    for entity_id, chunk in zip(entities, chunks):
        url = f"{HA_URL}/api/states/{entity_id}"
        payload = {"state": chunk}
        try:
            response = httpx.post(url, headers=HEADERS, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Warning: could not write to {entity_id}: {e}")
            success = False

    return success


# This block only runs when you execute this file directly (not when imported).
# It's a quick way to test the data fetcher in isolation.
if __name__ == "__main__":
    import json
    data = get_plant_data()
    print(json.dumps(data, indent=2))
