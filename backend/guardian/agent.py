import os
import json

from dotenv import load_dotenv
from google import genai

from guardian.tools import (
    get_service_alerts,
    get_elevator_outages,
    get_station_arrivals,
)

from guardian.prompts import SYSTEM_PROMPT


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=api_key)


# -----------------------------
# Tool definitions
# -----------------------------

service_alerts_tool = {
    "type": "function",
    "name": "get_service_alerts",
    "description": "Gets current SEPTA service alerts, delays, and disruptions.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

elevator_outages_tool = {
    "type": "function",
    "name": "get_elevator_outages",
    "description": "Gets current SEPTA elevator outages.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

station_arrivals_tool = {
    "type": "function",
    "name": "get_station_arrivals",
    "description": "Gets live SEPTA Regional Rail arrivals and departures for a station.",
    "parameters": {
        "type": "object",
        "properties": {
            "station": {
                "type": "string",
                "description": "The SEPTA station name."
            }
        },
        "required": ["station"],
    },
}

TOOLS = [
    service_alerts_tool,
    elevator_outages_tool,
    station_arrivals_tool,
]

# -----------------------------
# Tool execution
# -----------------------------

def execute_tool(name, arguments):

    if name == "get_service_alerts":
        return get_service_alerts()

    if name == "get_elevator_outages":
        return get_elevator_outages()

    if name == "get_station_arrivals":
        return get_station_arrivals(
            arguments["station"]
        )

    raise ValueError(f"Unknown tool: {name}")

# -----------------------------
# Guardian
# -----------------------------

def run_guardian(user_request):

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=user_request,
        tools=TOOLS,
        generation_config={
            "thinking_level": "low"
        },
    )

    while True:

        function_calls = [
            step
            for step in interaction.steps
            if step.type == "function_call"
        ]

        if not function_calls:
            return interaction.output_text

        results = []

        for call in function_calls:

            print(f"🔧 Guardian calling: {call.name}")

            result = execute_tool(
                call.name,
                call.arguments
            )

            print(f"📡 Tool result: {result}")

            results.append({
                "type": "function_result",
                "name": call.name,
                "call_id": call.id,
                "result": [
                    {
                        "type": "text",
                        "text": json.dumps(result)
                    }
                ],
            })

        interaction = client.interactions.create(
            model="gemini-3.8-flash",
            previous_interaction_id=interaction.id,
            input=results,
            tools=TOOLS,
        )


# -----------------------------
# Test
# -----------------------------

if __name__ == "__main__":

    request = """
    I need to get to Temple University by 2:00 PM.

    Check SEPTA conditions and determine whether
    any current disruptions could affect my journey.

    Tell me what I should do.
    """

    answer = run_guardian(request)

    print("\n")
    print("=" * 60)
    print("🛡️ SEPTA GUARDIAN")
    print("=" * 60)
    print(answer)
