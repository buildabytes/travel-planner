import random
from google.genai import Client, types
from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.examples import Example
from google.adk.tools.example_tool import ExampleTool
import os
import json
from typing import Optional

# --- Load mock flight dataset ----
FLIGHTS_JSON_PATH = os.path.join(os.path.dirname(__file__), "flights_dataset.json")

_HOTELS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mock_hotels.json"
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

def _load_flights():
    """Load and return the raw list of flight records from the dataset file."""
    with open(FLIGHTS_JSON_PATH, "r") as f:
        flights_data = json.load(f)
        return flights_data

def _load_hotels():
    """Load hotels and attach a lowercased city for case-insensitive search.
 
    The original fields are preserved; a private ``_city_lower`` key is added
    purely for matching and is not part of what we return to the caller.
    """
    with open(_HOTELS_PATH, "r", encoding="utf-8") as fh:
        hotels = json.load(fh)
    for hotel in hotels:
        hotel["_city_lower"] = hotel["city"].lower()
    return hotels

def _parse_month_day(token):
    """Parse an ``"MM-DD"`` token into ``(month, day)``."""
    month, day = token.strip().split("-")
    return int(month), int(day)

def _flight_month_day(flight):
    """Return the ``(month, day)`` of a flight's departure as integers.
 
    Departure times look like ``"01-02 06:00"``: take the part before the
    space, split on ``-``, done.
    """
    date_part = flight["departure_time"].split()[0]   # "01-02"
    month, day = date_part.split("-")
    return int(month), int(day)

def _to_month_number(month: str):
    """Return an int month from '3', '03', 'March', or 'mar'. None if blank/unknown."""
    m = month.strip().lower()
    if not m:
        return None
    if m.isdigit():
        return int(m)
    # Match full name or 3-letter abbreviation.
    if m in _MONTHS:
        return _MONTHS[m]
    for name, num in _MONTHS.items():
        if name.startswith(m[:3]):
            return num
    return None

def query_flights(
    departure_city: str = "",
    arrival_city: str ="",
    date: str = "",
    start_date: str ="",
    end_date: str = "",
    month:str =""
) -> list :
    flights = _load_flights()

    dep = departure_city.strip().lower()
    arr = arrival_city.strip().lower()

    range_bounds = None   # (start_md, end_md)
    month_filter = None   # int month
    exact_md = None       # (month, day)

    if start_date.strip() and end_date.strip():
        startDate = _parse_month_day(start_date)
        endDate = _parse_month_day(end_date)
        range_bounds = (min(startDate, endDate), max(startDate, endDate))
    elif month.strip():
        month_filter = _to_month_number(month)
    elif date.strip():
        exact_md = _parse_month_day(date)

    results = []
    for flight in flights:
        if dep and flight["departure_city"].lower() != dep:
            continue
        if arr and flight["arrival_city"].lower() != arr:
            continue
 
        if range_bounds or month_filter is not None or exact_md is not None:
            md = _flight_month_day(flight)
            if range_bounds and not (range_bounds[0] <= md <= range_bounds[1]):
                continue
            if month_filter is not None and md[0] != month_filter:
                continue
            if exact_md is not None and md != exact_md:
                continue
 
        results.append(flight)
 
    return results

def query_flights_simple(
    departure_city: str,
    arrival_city: str,
    date: str,
) -> list:
    """Look up flights by departure city, arrival city, and date.
 
    This is the simplified, agent-facing tool. It has no default values (the
    agent passes "" to skip a filter). The ``date`` argument is an exact date
    in ``"MM-DD"`` format (e.g. ``"01-02"``).
 
    Args:
        departure_city: City to depart from, e.g. ``"London"``. Pass "" to
            skip this filter.
        arrival_city: City to arrive at, e.g. ``"Paris"``. Pass "" to skip
            this filter.
        date: Exact ``"MM-DD"`` date to search for. Pass "" to skip this
            filter.
 
    Returns:
        A list of matching flight dictionaries, each containing the airline,
        flight number, departure/arrival cities and airports, departure and
        arrival times, and status. Empty list if there are no matches.
    """
    return query_flights(
        departure_city=departure_city,
        arrival_city=arrival_city,
        date=date,
    )

def query_hotels(city: str, min_rating: float, max_price: float) -> list:
    query = city.strip().lower()

    results = []
    for hotel in _load_hotels():
        if query and query not in hotel["_city_lower"]:
            continue
        if hotel["rating"] < min_rating:
            continue
        if max_price > 0 and hotel["price"] > max_price:
            continue
        # Return a clean record without the internal matching helper.
        results.append({
            "city": hotel["city"],
            "name": hotel["name"],
            "rating": hotel["rating"],
            "price": hotel["price"],
        })
 
    return results


# Task 2: Create your First Agent
attractions_agent = Agent(
    model="gemini-2.5-flash",
    name="attractions_agent",
    description="Provides tourist attractions info for a given city",
    instruction="""
        You are responsible for suggesting popular tourist attractions,
        sightseeing spots, and local activities for the given city.
        Provide concise and relevent recommendations to help the user plan their trip.
    """,
    tools=[],
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ]
    ),
)


# Task 3: Integrate Flight Agent
flight_agent = Agent(
    model="gemini-2.5-flash",
    name="flight_agent",
    description="Provides flight information from the mock flight dataset using city names.",
    instruction="""
        You are a Flight Information agent. When asked for flights between cities on a certain date,
        query the mock flight dataset and provide a clear summary of matching flights,
        including airline, flight number, departure/arrival cities and times, and status.
        If no flights match, politely tell the user that no flights were found.
        Assume the user provides city names, not airport codes.
        Always pass all three arguments to the tool; use an empty string "" for any
        the user didn't specify. Dates are in "MM-DD" format.
        Dates use MM-DD. If the user gives a month by name (e.g. 'March'), 
        convert it to its two-digit number ('03') before calling the tool.
    """,
    tools=[query_flights_simple],
    generate_content_config=types.GenerateContentConfig(
    safety_settings=[
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.OFF,
        ),
    ]
    ),
    )


# Task 4: Integrate Hotel Agent
hotel_agent =  Agent(
    name="hotel_agent",
    model="gemini-2.5-flash",
    description=(
        "Finds hotels for a traveler's destination, filtering by city, a "
        "minimum star rating, and a maximum nightly price."
    ),
    instruction=(
        "You are a helpful hotel-finding assistant for a travel planner. "
        "When a user asks about places to stay, call the `query_hotels` tool "
        "to look up matching hotels.\n"
        "Always provide all three arguments. If the user does not specify "
        "one, pass a neutral value: an empty string \"\" for `city`, 0 for "
        "`min_rating`, and 0 for `max_price` (0 means no price cap).\n"
        "For each hotel found, present its name, city, rating, and nightly "
        "price clearly. If no hotels match, politely tell the user that none "
        "were found and suggest relaxing the rating or price constraints."
    ),
    tools=[query_hotels],
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ]
    ),
)


# Task 8: Add Example Tool for Demonstrations
example_tool = ExampleTool(
    examples=[
        Example(
            input=types.Content(
                role="user",
                parts=[types.Part(text="Plan a trip to Paris next week.")],
            ),
            output=[
                types.Content(
                    role="model",
                    parts=[types.Part(text=(
                        "Do not describe what you will do — actually delegate. For each part of the request," 
                        "transfer to the relevant sub-agent, wait for its result, then continue. Only after"
                        "collecting flights, hotels, attractions, and weather should you present the combined plan and ask the user to confirm."
                    ))],
                )
            ],
        ),
        Example(
            input=types.Content(
                role="user",
                parts=[types.Part(text="Recommend hotels near the main attractions in Paris.")],
            ),
            output=[
                types.Content(
                    role="model",
                    parts=[types.Part(text=(
                        "I'll first ask the attractions agent for Paris's top sights, then "
                        "have the hotel agent find well-rated hotels nearby and share the best options."
                    ))],
                )
            ],
        ),
        Example(
            input=types.Content(
                role="user",
                parts=[types.Part(text="Build me a daily itinerary for two days in Paris")],
            ),
            output=[
                types.Content(
                    role="model",
                    parts=[types.Part(text=(
                        "I'll gather attractions from the attractions agent and the forecast "
                        "from the weather agent, then organize a day-by-day itinerary and "
                        "confirm it with you before finalizing."
                    ))],
                )
            ],
        ),
    ]
)


# Task 6: Register the Weather Agent as a Remote Agent
weather_agent = RemoteA2aAgent(
    name="weather_agent",
    description="Provides weather info for a given city.",
    agent_card=os.path.join(
        os.path.dirname(__file__), "agents", "weather_agent", "agent.json"
    ),
)


# Task 7: Create the Root Agent
root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    global_instruction="""
        You are the Travel Planner, a friendly and organized assistant that 
        helps users plan complete trips. Be concise, confirm details, and keep
        the user informed about which part of their request you are handling.
    """,
    instruction="""
        You are the coordinator for a travel-planning team. Delegate each part of the user's request 
        to the right sub-agent:
         - weather_agent: weather forecasts for a destination.
         - hotel_agent: finding hotels by city, rating, and price.
         - flight_agent: finding flights between cities on a date.
         - attractions_agent: suggesting things to see and do in a city.
        Gather the results. then summarize the full plan and confirm it with
        the user before finishing. If a request is ambiguous, ask a brief 
        clarifying question first.
    """,
    sub_agents=[
        weather_agent,
        hotel_agent,
        flight_agent,
        attractions_agent,
    ],
    tools=[example_tool],
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ]
    ),
)
