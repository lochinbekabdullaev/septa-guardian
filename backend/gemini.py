import os

from dotenv import load_dotenv
from google import genai


# =========================================================
# GEMINI SETUP
# =========================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing from .env"
    )

client = genai.Client(
    api_key=API_KEY
)


MODEL_NAME = "gemini-3.8-flash"


# =========================================================
# TRIP PLANNER
# =========================================================

def plan_trip(
    origin,
    destination,
    alerts,
    arrivals=None,
    departure_time="now",
):

    prompt = f"""
You are SEPTA Guardian, a real-time transit safety
and trip-planning assistant.

A rider wants to travel from:

Origin: {origin}

Destination: {destination}

Departure time: {departure_time}

CURRENT SEPTA SERVICE ALERTS:
{alerts}

CURRENT TRAIN ARRIVALS / DEPARTURES:
{arrivals}

Your job is to analyze the live SEPTA information
and give the rider a practical recommendation.

IMPORTANT RULES:

1. Use ONLY the SEPTA information provided above.
2. Never invent trains, stations, routes, times, delays,
   or service information.
3. If a service disruption affects the trip, explain it.
4. Prefer currently available services when possible.
5. If the provided data is insufficient to determine
   a specific route, clearly say that.
6. Do not pretend that you know information that was
   not provided.
7. Keep the response concise and mobile-friendly.

Return EXACTLY this format:

Recommendation: <recommended action>

Reason: <short explanation based on the SEPTA data>

Alert: <important active disruption, or "None">

Alternative: <backup option based only on provided data,
or "None">
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
    )

    return interaction.output_text


# =========================================================
# DISRUPTION REPLANNER
# =========================================================

def replan_trip(
    origin,
    destination,
    current_route,
    reason,
    alerts,
    arrivals=None,
):

    prompt = f"""
You are SEPTA Guardian, a real-time transit
replanning assistant.

A rider is currently trying to travel from:

Origin: {origin}

Destination: {destination}

Their current route is:

{current_route}

The route has been disrupted because:

{reason}

CURRENT SEPTA SERVICE ALERTS:
{alerts}

CURRENT TRAIN ARRIVALS / DEPARTURES:
{arrivals}

The rider needs an alternative plan.

IMPORTANT RULES:

1. Use ONLY the SEPTA information provided above.
2. Never invent a train, route, station, departure time,
   delay, or service.
3. Avoid the disrupted service when possible.
4. Use the live train information to identify alternatives.
5. If there is not enough information to safely recommend
   an alternative, say so.
6. Be concise and useful for a mobile app.

Return EXACTLY this format:

Recommendation: <new recommended action>

Reason: <why the original route is affected and why
the new action makes sense>

Alert: <important active disruption>

Alternative: <another option based only on the provided
SEPTA data, or "None">
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt,
    )

    return interaction.output_text

