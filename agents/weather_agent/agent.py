import os
from google.adk import Agent
from google.genai import types
import httpx


# Task 5: Build Weather Agent
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/forecast"

# --- Tool Function ---
async def get_weather(location: str) -> str:
    """
    Fetches the 5-day weather forecast (40 items, typically) from OpenWeatherMap
    for a given city/location using the currentAPI key.

    Args:
        location: The name of the city or location (e.g., "Paris, France").
    
    Return:
        A human-readable string summarizing the key weather details.
    """
    if not OPENWEATHERMAP_API_KEY:
        return "Error: OPenWeatherMap API Key is not configured."

    # use an async HTTP Client
    async with httpx.AsyncClient() as client:
        params = {
            "q": location,
            "appid": OPENWEATHERMAP_API_KEY,
            "units": "metric", # use Celsius
        }

        try:
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            return f"Error retrieving weather data: API returned status code {e.response.status_code}."
        except httpx.RequestError as e:
            return f"Error connecting to OpenWeatherMap API: {e}."
        except json.JSONDecodeError:
            return "Error: Received unreadble response from the weather service."

        daily_forecasts = {}

        for item in data.get("list", []):
            date_str = item["dt_txt"].split(" ")[0]
            temp = item["main"]["temp"]
            weather_description = item["weather"][0]["description"]
        
        if date_str not in daily_forecasts:
            daily_forecasts[date_str] = {
                "min_temp": temp,
                "max_temp": temp,
                "weather": weather_description,
                "count": 1,
            }
        else:
            daily_forecasts[date_str]["min_temp"] = min(daily_forecasts[date_str]["min_temp"], temp)
            daily_forecasts[date_str]["max_temp"] = max(daily_forecasts[date_str]["max_temp"], temp)

            daily_forecasts[date_str]["weather"] = weather_description
            daily_forecasts[date_str]["count"] += 1

        summary = []
        for date, daily_data in daily_forecasts.items():
            summary.append(
                f"{date}: {daily_data['weather'].capitalize()}"
                f"(High: {daily_data['max_temp']:.1f}\u00b0C, Low: {daily_data['min_temp']:.1f}\u00b0C)"
            )
        
        if not summary:
            return f"Couly not find a forecast for {location}". Please chekc the location spelling."
    
        return f"Multiday Weather Forecast for {location}:\n- " + "\n- ". join(summary)

# --- Agent Definition ---
weather_agent = Agent(
    model="gemini-2.5-flash",
    name="weather_agent",
    description="Provides multi-day weather forecasts for a given city.",
    instrcution="""
        You are a weather assitant for a travel planner. When the user asks
        about the weather for a destination, call the get_weather tools with the
        city name and relay its forecast clearly. If the tool returns an error
        message, pass it along politely and suggest checking the city spelling.
    """,
    tools=[get_weather],
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ]
    ),
)