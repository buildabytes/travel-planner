# Travel Planner — A Multi-Agent System with Google ADK

An AI travel planner built with Google's **Agent Development Kit (ADK)**. You
chat with it in the terminal ("plan a two-day trip to Paris") and a team of
specialized agents work together to pull flights, hotels, attractions, and
weather, then assemble a plan.

This project is a hands-on tour of **agentic patterns**: tools, specialized
sub-agents, and a root agent that orchestrates them.

---

## How it works

### The big picture

You don't talk to one giant AI. You talk to a **root agent** (an orchestrator)
that delegates each part of your request to a **specialist sub-agent**. Each
sub-agent owns one job and the tool(s) for it.

```
                          You (terminal)
                                │
                                ▼
                        ┌───────────────┐
                        │  root_agent   │   orchestrator: routes work,
                        │ (coordinator) │   then assembles the final plan
                        └───────┬───────┘
              ┌─────────────┬───┴─────────┬──────────────┐
              ▼             ▼             ▼              ▼
        ┌───────────┐ ┌───────────┐ ┌─────────────┐ ┌───────────┐
        │  flight_  │ │  hotel_   │ │ attractions_│ │ weather_  │
        │  agent    │ │  agent    │ │ agent       │ │ agent     │
        └─────┬─────┘ └─────┬─────┘ └──────┬──────┘ └─────┬─────┘
              ▼             ▼              ▼              ▼
        query_flights  query_hotels   (LLM knowledge)  get_weather
        (mock data)    (mock data)                     (OpenWeather API)
```

### The three building blocks

1. **Tools** — ordinary Python functions the model can call (e.g.
   `query_flights`, `get_weather`). The framework reads each function's
   signature and docstring to decide when and how to call it. The docstring is
   effectively the tool's API documentation *for the model*.

2. **Sub-agents** — small, single-purpose agents. Each has a name, a
   description, an instruction, and its tools. They don't know about each
   other.

3. **Root agent** — the coordinator. It holds the sub-agents in its
   `sub_agents` list and delegates ("transfers") to whichever one fits each
   part of the request, then summarizes the combined result.

### What happens on one request

1. You type a request into the CLI (`cli.py`).
2. The CLI wraps it in a message and hands it to a `Runner`, which drives the
   `root_agent`.
3. The root agent decides which specialist(s) the request needs and **transfers**
   control to them — e.g. flights → `flight_agent`.
4. The specialist calls its **tool** (e.g. `query_flights`) to get real data.
5. Results bubble back up to the root agent, which assembles a plan and replies.
6. The CLI streams each step's text to your terminal, tagged with the agent
   that produced it (`[flight_agent]: ...`).

### The agents at a glance

| Agent | Job | Tool | Data source |
|-------|-----|------|-------------|
| `flight_agent` | Find flights between cities on a date | `query_flights` | `flights_dataset.json` (mock) |
| `hotel_agent` | Find hotels by city, rating, price | `query_hotels` | `mock_hotels.json` (mock) |
| `attractions_agent` | Suggest things to see/do | none | the model's own knowledge |
| `weather_agent` | Multi-day forecast for a city | `get_weather` | OpenWeatherMap API (live) |
| `root_agent` | Coordinate the above; assemble the plan | `example_tool` | — |

> **Note:** flights and hotels use small **mock datasets**, so searches only
> succeed for cities/dates that exist in those files (the sample flight data is
> January-only, among London/Paris/New York). Weather is a **live** API call,
> so it needs a real key.

---

## Project layout

```
travel-planner/                  ← repo root (run commands from here)
├── README.md
├── requirements.txt
├── .env.example                 ← copy to .env and add your keys
├── .gitignore
└── travel_planner/
    ├── agent.py                 ← flight tools + flight/hotel/attractions + root_agent + example_tool
    ├── cli.py                   ← interactive command-line entry point
    ├── test.py                  ← task-by-task test harness
    ├── flights_dataset.json     ← mock flight data
    ├── mock_hotels.json         ← mock hotel data
    └── agents/
        └── weather_agent/
            └── agent.py         ← weather tool + weather_agent
```

You do **not** need a copy of the ADK library source (`google/adk/...`) — that
is installed for you by `pip install google-adk`.

---

## Prerequisites

- **Python 3.10+** (check with `python3 --version`)
- A **Gemini API key** (free): https://aistudio.google.com/apikey
- An **OpenWeatherMap API key** (free) for the weather agent:
  https://home.openweathermap.org/api_keys
- VS Code with the Python extension (recommended)

---

## Setup

From the **repo root** (`travel-planner/`):

**1. Create and activate a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows PowerShell
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your API keys**
```bash
cp .env.example .env
```
Then open `.env` and paste in your real keys:
```
GOOGLE_API_KEY=your_gemini_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
OPENWEATHERMAP_API_KEY=your_openweathermap_key_here
```

**4. (VS Code) Select the interpreter**
`Cmd/Ctrl + Shift + P` → **Python: Select Interpreter** → choose the `.venv`
one, so the Run button and terminal use the environment you just installed into.

---

## Running it

From the repo root:
```bash
python travel_planner/cli.py
```

You'll see a welcome prompt. Try a request that exists in the mock data:
```
You: Find flights from New York to London on 01-01
[flight_agent]: AirDemo 101 — New York → London, departs 01-01, on time.

You: What's the weather like in Paris?
[weather_agent]: Multiday Weather Forecast for Paris:
- 2026-06-18: Light clouds (High: 22.0°C, Low: 14.0°C)
- ...

You: quit
Goodbye! Safe travels.
```

Type `quit` or `exit` to leave.

---

## Troubleshooting

**"Missing key" / model errors on the first message.**
Educative set `GOOGLE_API_KEY` for you invisibly; locally you must supply your
own in `.env`. Make sure `GOOGLE_GENAI_USE_VERTEXAI=FALSE` is set too, so the
SDK uses your AI Studio key instead of expecting Vertex/gcloud auth.

**`ModuleNotFoundError` on `agent` or `agents.weather_agent`.**
Run from the **repo root** (`python travel_planner/cli.py`), not from inside the
`travel_planner/` folder. The imports resolve relative to where you launch
Python.

**"Default value is not supported in function declaration schema."**
A function registered as a tool has default parameter values. Tool functions
must have **all required parameters** (no `= ""`); tell the agent, in its
instruction, to pass `""`/`0` for anything the user didn't specify.

**Searches return nothing.**
Flights and hotels use small mock datasets. Use cities/dates that exist in
`flights_dataset.json` / `mock_hotels.json` (sample flights are January-only,
in `MM-DD` format, among London/Paris/New York).

**"Non-text parts in the response" warning.**
Harmless. That's the model's reasoning/tool-call parts; the CLI only prints
text.

---

## License

MIT (or your choice). The ADK library is Google's and is installed via pip,
not bundled here.