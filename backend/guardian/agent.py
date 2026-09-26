import os
import json
from typing import List, Literal

from dotenv import load_dotenv

from google import genai
from pydantic import BaseModel, Field

from guardian.tools import (
    get_service_alerts,
    get_station_arrivals,
    get_elevator_outages,
)


# ============================================================
# GEMINI CLIENT
# ============================================================

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set."
    )

client = genai.Client(api_key=API_KEY)

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)


# ============================================================
# STRUCTURED OUTPUT MODELS
# ============================================================

class Disruption(BaseModel):
    line: str = Field(
        description=(
            "The exact line or service name from the SEPTA alert. "
            "Do not invent or normalize the name."
        )
    )

    status: str = Field(
        description=(
            "The status explicitly stated by SEPTA. "
            "Do not infer a status that is not present in the alert."
        )
    )

    severity: Literal["high", "medium", "low"] = Field(
        description=(
            "The severity exactly as provided by the SEPTA alert data."
        )
    )

    description: str = Field(
        description=(
            "A concise summary using only information contained "
            "in the SEPTA alert."
        )
    )


class Arrival(BaseModel):
    line: str = Field(
        description=(
            "The train line exactly as returned by SEPTA."
        )
    )

    destination: str = Field(
        description=(
            "The train destination exactly as returned by SEPTA."
        )
    )

    arrival_time: str = Field(
        description=(
            "The arrival time exactly as returned by SEPTA."
        )
    )

    status: str = Field(
        description=(
            "The status or delay exactly as returned by SEPTA."
        )
    )

    track: str = Field(
        description=(
            "The track exactly as returned by SEPTA, "
            "or an empty string if unavailable."
        )
    )


class GuardianAnalysis(BaseModel):
    summary: str = Field(
        description=(
            "A concise summary based ONLY on the provided SEPTA data. "
            "Do not add outside SEPTA knowledge."
        )
    )

    disruptions: List[Disruption] = Field(
        description=(
            "Only disruptions explicitly supported by the SEPTA "
            "service alert data."
        )
    )

    relevant_arrivals: List[Arrival] = Field(
        description=(
            "Only arrivals explicitly supported by the SEPTA "
            "arrival data."
        )
    )

    elevator_summary: str = Field(
        description=(
            "Describe elevator information ONLY from the provided "
            "elevator tool result. If the result contains an empty "
            "elevators list, state that no elevator outages were "
            "returned by the tool. Do not infer that elevators are "
            "operational."
        )
    )


# ============================================================
# TOOL DATA COLLECTION
# ============================================================

def collect_septa_data():
    """
    Collect all available SEPTA data.

    The Gemini model receives the returned data as its only
    factual source.
    """

    alerts = get_service_alerts()

    arrivals = get_station_arrivals(
        "Temple University"
    )

    elevators = get_elevator_outages()

    return {
        "service_alerts": alerts,
        "station_arrivals": arrivals,
        "elevator_outages": elevators,
    }


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are SEPTA Guardian, a transit information assistant.

Your job is to summarize SEPTA data returned by tools.

ABSOLUTE SOURCE RULE
====================

The tool results provided to you are the ONLY authoritative factual
source for this response.

Do not use your general knowledge of SEPTA.

Do not use memory.

Do not browse mentally.

Do not invent missing information.

Do not assume that a SEPTA route, station, subway line, bus route,
transfer, travel time, accessibility feature, or service condition
exists unless it is explicitly present in the supplied tool data.

If information is not present in the tool data, say that it is not
available from the current SEPTA data.

ALERT RULES
===========

For service alerts:

- Use only alerts returned by get_service_alerts.
- Preserve the exact route/line names from the data.
- Preserve the severity supplied by the tool.
- Do not create additional disruptions.
- Do not claim a service is suspended unless the alert explicitly
  supports that statement.
- Do not turn a delay into a suspension.
- Do not turn a platform instruction into a suspension.
- Do not infer the geographic extent of a disruption beyond what the
  alert description says.

ARRIVAL RULES
=============

For train arrivals:

- Use only trains returned by get_station_arrivals.
- Preserve the line exactly as returned.
- Preserve the destination exactly as returned.
- Preserve the arrival time exactly as returned.
- Preserve the status/delay exactly as returned.
- Preserve the track exactly as returned.
- Do not invent additional trains.
- Do not invent departure times.
- Do not calculate a new arrival time.
- Do not claim that a train is cancelled unless the tool data says so.
- Do not claim that a train is operating normally merely because its
  status says "On Time."

ELEVATOR RULES
==============

Elevator information requires special care.

The elevator tool result is authoritative.

If:

    {"elevators": []}

is returned, you MUST say:

"No elevator outages were returned by the SEPTA elevator data."

Do NOT say:

"There are no elevator outages."

Do NOT say:

"All elevators are operational."

Do NOT say:

"Temple University elevators are working."

An empty result means only that the tool returned no elevator outage
records. It does not prove that every elevator is operational.

If elevator records are returned, report only those records.

RECOMMENDATIONS
===============

Do not invent alternate routes.

Do not invent bus routes.

Do not invent subway transfers.

Do not claim that a particular route is faster, safer, more reliable,
or unaffected unless the supplied data explicitly supports that claim.

If the available tool data is insufficient to recommend a route, say so.

TIME RULES
==========

Never invent a deadline.

Never invent a current time.

Never say a passenger should arrive before a particular time unless
that time was explicitly supplied by the user or by tool data.

Do not use a previously mentioned time as though it were current.

UNCERTAINTY RULE
================

When the data is insufficient, explicitly say:

"The available SEPTA data does not provide enough information to
determine that."

Do not fill gaps with guesses.

IMPORTANT
=========

Your job is to accurately summarize the data, not to create a complete
trip plan from outside knowledge.

It is better to omit information than to invent it.
"""


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_septa_data(data):
    """
    Send the collected SEPTA data to Gemini.

    Gemini is explicitly constrained to use only the supplied data.
    """

    user_prompt = (
        "Analyze the following SEPTA tool data.\n\n"
        "IMPORTANT: Treat this JSON as the complete factual record. "
        "Do not add information that is not present.\n\n"
        + json.dumps(data, indent=2, ensure_ascii=False)
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "response_schema": GuardianAnalysis,
            "temperature": 0,
        },
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return GuardianAnalysis.model_validate_json(
        response.text
    )


# ============================================================
# OUTPUT
# ============================================================

def print_guardian_report(analysis: GuardianAnalysis):
    print()
    print("=" * 60)
    print("🛡️ SEPTA GUARDIAN")
    print("=" * 60)
    print()

    print(analysis.summary)
    print()

    if analysis.disruptions:
        print("### Disruptions")
        print()

        for disruption in analysis.disruptions:
            print(
                f"- {disruption.line} "
                f"[{disruption.severity}]"
            )
            print(
                f"  Status: {disruption.status}"
            )
            print(
                f"  {disruption.description}"
            )
            print()

    if analysis.relevant_arrivals:
        print("### Relevant Arrivals")
        print()

        for arrival in analysis.relevant_arrivals:
            print(
                f"- {arrival.line} → "
                f"{arrival.destination}"
            )
            print(
                f"  Arrival: {arrival.arrival_time}"
            )
            print(
                f"  Status: {arrival.status}"
            )
            print(
                f"  Track: {arrival.track}"
            )
            print()

    print("### Elevator Information")
    print()
    print(analysis.elevator_summary)
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    print("🔧 Collecting SEPTA data...")

    data = collect_septa_data()

    print("📡 SEPTA data collected.")

    print()
    print("🤖 Sending data to Gemini...")

    analysis = analyze_septa_data(data)

    print("🤖 Gemini analysis complete.")

    print_guardian_report(analysis)


if __name__ == "__main__":
    main()
