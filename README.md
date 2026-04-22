# 🌳 Lime Tree Agent

An automated care assistant for a potted Key lime tree (*Citrus aurantifolia*) on a 4th-floor south-facing deck in Amsterdam. It reads live sensor data and weather forecasts, reasons about the tree's condition, and delivers a plain-English daily briefing to a Home Assistant dashboard and an iPhone push notification.

---

## What it does

Twice daily (and on demand via a dashboard button), the agent:

1. Reads four Bluetooth soil sensors from Home Assistant — moisture, conductivity, illuminance, and temperature
2. Fetches 30 days of sensor history to reason about trends
3. Pulls the current weather and 7-day forecast from MET Norway
4. Reads the current indoor/outdoor placement from an HA toggle
5. Calls GPT-4o with a detailed lime tree care prompt
6. Writes the briefing across six Home Assistant `input_text` entities (6 × 255 chars)
7. Sends a push notification to Brendan's iPhone with the weather summary line

---

## Example output

```
🌳 LIME TREE BRIEFING — 21 April 2026 15:49
📍 INDOOR · Spring · Clear, 12°C, windy

OVERALL STATUS: Tree is in healthy condition with no immediate concerns.

TODAY'S ACTIONS:
• Nothing required today

TRENDS:
• Moisture at 45% — healthy drying phase, watering needed in ~3–5 days
• Conductivity at 325 µS/cm and declining — fertilize within 3 days

THIS WEEK:
• Conditions not yet suitable for outdoor placement — monitor overnight lows

SENSOR NOTES:
• Illuminance optimal for current indoor position
```

---

## Architecture

```
agent.py          — orchestrator: gather → think → deliver
data/
  home_assistant.py  — sensor reads, history, briefing write, push notification
  weather.py         — MET Norway (primary) + Open-Meteo (fallback)
prompts/
  system.py          — GPT-4o system prompt + user prompt assembly
webhook.py        — Flask server (port 8900) for on-demand HA button trigger
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/jackbr4/lime-tree-agent.git
cd lime-tree-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
HA_URL=https://your-nabu-casa-url.ui.nabu.casa
HA_TOKEN=your_long_lived_token_here
OPENAI_API_KEY=your_openai_key_here
WEBHOOK_TOKEN=your_secret_token_here
```

Generate a secure webhook token:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Run manually

```bash
./venv/bin/python agent.py
```

### 4. Webhook server (on-demand runs)

```bash
./venv/bin/python webhook.py
```

Trigger a run from the command line:
```bash
curl -X POST https://your-host/lime-tree-webhook \
  -H "X-Webhook-Token: your_token"
```

Health check:
```bash
curl https://your-host/lime-tree-webhook/health
```

---

## Home Assistant requirements

| Entity | Type | Purpose |
|---|---|---|
| `sensor.lime_tree_sensor_conductivity` | Sensor | Conductivity reading |
| `sensor.lime_tree_sensor_illuminance` | Sensor | Illuminance reading |
| `sensor.plant_sensor_1548_moisture` | Sensor | Moisture reading |
| `sensor.lime_tree_sensor_temperature` | Sensor | Temperature reading |
| `input_boolean.lime_tree_outdoor` | Toggle | Indoor/outdoor placement |
| `input_text.lime_tree_briefing` through `_6` | Input text (255 chars each) | Briefing storage |
| `notify.mobile_app_brendans_iphone` | Notify service | iPhone push notification |

---

## Deployment

Pushes to `main` deploy automatically to a Whatbox seedbox via GitHub Actions. The workflow pulls the latest code, installs dependencies, and restarts the webhook server.

---

## Dependencies

- [OpenAI Python SDK](https://github.com/openai/openai-python) — GPT-4o calls
- [httpx](https://www.python-httpx.org/) — async-capable HTTP client for HA + weather APIs
- [Flask](https://flask.palletsprojects.com/) — lightweight webhook server
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable management
- Weather data: [MET Norway Locationforecast](https://api.met.no/) (primary), [Open-Meteo](https://open-meteo.com/) (fallback)
