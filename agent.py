"""
agent.py — The Lime Tree Agent Orchestrator

This is the main entry point. It:
1. Gathers all data (sensors, history, weather)
2. Assembles the prompts and calls ChatGPT with that context
3. Prints the briefing

Run manually:    python agent.py
Run on schedule: this file is what the cron job will call (Phase 5)
"""
import os
import openai
from dotenv import load_dotenv

load_dotenv()

from data.home_assistant import get_plant_data, get_sensor_histories, get_tree_location, set_briefing
from data.weather import get_weather
from prompts.system import build_system_prompt, build_user_prompt


def run_agent() -> str:
    """
    Execute one full agent run and return the briefing text.

    This function is the core loop:
      Observe (gather data) → Think (call Claude) → Act (return briefing)

    Keeping it as a single function that returns a string makes it easy
    to later extend — e.g. send the output via email, push a notification
    to HA, or log it to a file — without changing the core logic.
    """

    # --- OBSERVE ---
    # Gather all data sources. If any of these fail, let the exception
    # surface naturally — better to know about failures than silently
    # produce an empty briefing.
    print("Fetching sensor readings...")
    plant_data = get_plant_data()

    print("Fetching sensor history...")
    histories = get_sensor_histories()

    print("Fetching weather...")
    weather = get_weather()

    print("Reading tree location from HA...")
    tree_location = get_tree_location()
    print(f"Tree is currently: {tree_location}")

    # --- THINK ---
    # Assemble prompts and call ChatGPT.
    # The system prompt holds fixed lime tree knowledge.
    # The user prompt holds all the live data for this specific run.
    print("Calling ChatGPT...")

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    message = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": build_system_prompt(),
            },
            {
                "role": "user",
                "content": build_user_prompt(
                    plant_data=plant_data,
                    histories=histories,
                    weather=weather,
                    tree_location=tree_location,
                ),
            },
        ],
    )

    # Extract the text response from the response object
    briefing = message.choices[0].message.content

    return briefing


def main():
    """
    Entry point when running directly.
    Runs the agent and prints the briefing to stdout.

    In Phase 5 we will extend this to also deliver the briefing
    (email, HA notification, etc.) — but printing is enough for now.
    """
    print("\n" + "="*60)
    print("LIME TREE AGENT — STARTING RUN")
    print("="*60 + "\n")

    briefing = run_agent()

    print("\n" + "="*60)
    print("BRIEFING:")
    print("="*60)
    print(briefing)
    print("\n" + "="*60)

    # Also write the latest briefing to a file so we can inspect it
    # and later use it for delivery (Phase 5)
    with open("latest_briefing.txt", "w") as f:
        f.write(briefing)
    print("Briefing saved to latest_briefing.txt")

    print("Writing briefing to Home Assistant...")
    success = set_briefing(briefing)
    if success:
        print("Briefing written to HA successfully.")
    else:
        print("Warning: one or more HA writes failed — check logs.")


if __name__ == "__main__":
    main()
