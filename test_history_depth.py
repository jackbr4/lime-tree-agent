"""
Diagnostic script to check how far back HA history actually goes
for the moisture and conductivity sensors.
"""
import os
import httpx
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

HA_URL = os.getenv("HA_URL")
HA_TOKEN = os.getenv("HA_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

def check_history_depth(entity_id: str, days: int = 30):
    """Ask for 30 days and see how far back HA actually returns data."""
    start_time = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = f"{HA_URL}/api/history/period/{start_time}"

    params = {
        "filter_entity_id": entity_id,
        "minimal_response": "true",
        "no_attributes": "true",
    }

    response = httpx.get(url, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    raw = response.json()

    if not raw or not raw[0]:
        print(f"{entity_id}: No history returned")
        return

    states = raw[0]
    total = len(states)

    # Find earliest and latest timestamps
    timestamps = []
    for s in states:
        try:
            ts = datetime.fromisoformat(s["last_changed"].replace("Z", "+00:00"))
            timestamps.append(ts)
        except:
            continue

    if timestamps:
        earliest = min(timestamps).strftime("%Y-%m-%d %H:%M")
        latest = max(timestamps).strftime("%Y-%m-%d %H:%M")
        print(f"{entity_id}:")
        print(f"  Total state changes returned: {total}")
        print(f"  Earliest: {earliest}")
        print(f"  Latest:   {latest}")
    else:
        print(f"{entity_id}: Could not parse timestamps")

if __name__ == "__main__":
    print("Checking history depth (requesting 30 days)...\n")
    check_history_depth("sensor.plant_sensor_1548_moisture")
    check_history_depth("sensor.lime_tree_sensor_conductivity")
