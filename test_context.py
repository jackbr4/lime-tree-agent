"""
Test script that assembles and prints the full context that will be
passed to Claude on each agent run.

This is not the agent itself — it just shows you exactly what Claude
will see, so you can verify the data looks right before wiring it up.
"""
import json
import os
from dotenv import load_dotenv

load_dotenv()

from data.home_assistant import get_plant_data, get_sensor_histories
from data.weather import get_weather
from prompts.system import build_system_prompt, build_user_prompt

def main():
    print("Fetching plant data...")
    plant_data = get_plant_data()

    print("Fetching sensor histories...")
    histories = get_sensor_histories()

    print("Fetching weather...")
    weather = get_weather()

    tree_location = os.getenv("TREE_LOCATION", "outdoor")

    print("\n" + "="*60)
    print("SYSTEM PROMPT:")
    print("="*60)
    print(build_system_prompt())

    print("\n" + "="*60)
    print("USER PROMPT (live data):")
    print("="*60)
    print(build_user_prompt(plant_data, histories, weather, tree_location))

    print("\n" + "="*60)
    print("RAW HISTORIES (for debugging):")
    print("="*60)
    print(json.dumps(histories, indent=2))

if __name__ == "__main__":
    main()
