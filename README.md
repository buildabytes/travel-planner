# Travel Planner (Google ADK multi-agent)

A multi-agent travel planner built with Google's Agent Development Kit (ADK).
A root agent delegates to specialist sub-agents for flights, hotels,
attractions, and weather.

## Setup (local / VS Code)

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Add your API keys:
   ```bash
   cp .env.example .env
   # then edit .env and paste in your real keys
   ```

4. Run the CLI:
   ```bash
   python travel_planner/cli.py
   ```

## Project layout
```
travel_planner/
├── agent.py                     # flight tools + flight/hotel/attractions agents + root_agent
├── cli.py                       # interactive command-line entry point
├── test.py                      # task-by-task test harness
├── flights_dataset.json         # mock flight data
├── mock_hotels.json             # mock hotel data
└── agents/
    └── weather_agent/
        └── agent.py             # weather tool + weather_agent
```