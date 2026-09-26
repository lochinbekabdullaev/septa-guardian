import re
import html
import requests
from datetime import datetime, timezone


SEPTA_ALERTS_URL = "https://www3.septa.org/api/Alerts/index.php"
SEPTA_ARRIVALS_URL = "https://www3.septa.org/api/Arrivals/index.php"


def strip_html(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(text))
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_septa_date(date_string):
    if not date_string:
        return None

    formats = [
        "%b %d %Y %I:%M%p",
        "%b %d %Y  %I:%M%p",
        "%b %d %Y %I:%M %p",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                date_string.strip(),
                fmt
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


# =========================================================
# ALERTS
# =========================================================

def get_alerts():
    response = requests.get(
        SEPTA_ALERTS_URL,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    alerts = []

    now = datetime.now(timezone.utc)

    for item in data:

        updated_at = item.get("last_updated", "")
        updated_time = parse_septa_date(updated_at)

        if updated_time is None:
            continue

        age_days = (
            now - updated_time
        ).total_seconds() / 86400

        if age_days > 7:
            continue

        is_active_alert = any(
            item.get(flag) == "Y"
            for flag in [
                "isalert",
                "isdelays",
                "isdiversion",
                "isdetour",
                "isdetouralert",
                "iselevator",
                "issuspended",
                "issuppend",
                "isstrike",
                "ismodifiedservice",
            ]
        )

        if not is_active_alert:
            continue

        description = (
            item.get("alert")
            or item.get("advisory")
            or item.get("description")
            or ""
        )

        if (
            item.get("issuspended") == "Y"
            or item.get("issuppend") == "Y"
            or item.get("isstrike") == "Y"
        ):
            severity = "high"

        elif (
            item.get("isdelays") == "Y"
            or item.get("isdiversion") == "Y"
            or item.get("isdetour") == "Y"
            or item.get("isdetouralert") == "Y"
            or item.get("iselevator") == "Y"
        ):
            severity = "medium"

        else:
            severity = "low"

        alerts.append({
            "id": item.get("route_id", ""),
            "title": (
                item.get("route_name")
                or item.get("route", "")
            ),
            "description": strip_html(description),
            "severity": severity,
            "route": item.get("route", ""),
            "active": True,
            "updated_at": updated_at,
        })

    return {
        "alerts": alerts
    }


# =========================================================
# ELEVATORS
# =========================================================

def get_elevators():
    response = requests.get(
        SEPTA_ALERTS_URL,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    elevators = []

    now = datetime.now(timezone.utc)

    for item in data:

        if item.get("iselevator") != "Y":
            continue

        updated_at = item.get("last_updated", "")
        updated_time = parse_septa_date(updated_at)

        if updated_time is None:
            continue

        age_days = (
            now - updated_time
        ).total_seconds() / 86400

        if age_days > 7:
            continue

        description = (
            item.get("alert")
            or item.get("advisory")
            or item.get("description")
            or ""
        )

        elevators.append({
            "id": item.get("route_id", ""),
            "station": (
                item.get("route_name")
                or item.get("route", "")
            ),
            "description": strip_html(description),
            "active": True,
            "updated_at": updated_at,
        })

    return {
        "elevators": elevators
    }


# =========================================================
# REGIONAL RAIL ARRIVALS
# =========================================================

def get_arrivals(station):

    params = {
        "station": station,
        "results": 10
    }

    response = requests.get(
        SEPTA_ARRIVALS_URL,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    arrivals = []

    # SEPTA returns something like:
    #
    # {
    #   "North Philadelphia Departures: ...": [
    #       {
    #           "Northbound": [...]
    #       },
    #       {
    #           "Southbound": [...]
    #       }
    #   ]
    # }
    #
    # The timestamped key changes every request,
    # so we grab the first value.

    if not isinstance(data, dict):
        return {
            "station": station,
            "arrivals": []
        }

    if not data:
        return {
            "station": station,
            "arrivals": []
        }

    # Get the first top-level value
    station_data = next(iter(data.values()))

    if not isinstance(station_data, list):
        return {
            "station": station,
            "arrivals": []
        }

    for direction_group in station_data:

        if not isinstance(direction_group, dict):
            continue

        # Handle Northbound and Southbound
        for direction_name in ["Northbound", "Southbound"]:

            trains = direction_group.get(
                direction_name,
                []
            )

            if not isinstance(trains, list):
                continue

            for train in trains:

                if not isinstance(train, dict):
                    continue

                arrivals.append({
                    "train": train.get(
                        "train_id",
                        ""
                    ),

                    "line": train.get(
                        "line",
                        ""
                    ),

                    "service_type": train.get(
                        "service_type",
                        ""
                    ),

                    "origin": train.get(
                        "origin",
                        ""
                    ),

                    "destination": train.get(
                        "destination",
                        ""
                    ),

                    "current_location": train.get(
                        "next_station",
                        ""
                    ),

                    "scheduled_time": train.get(
                        "sched_time",
                        ""
                    ),

                    "arrival_time": train.get(
                        "depart_time",
                        ""
                    ),

                    "status": train.get(
                        "status",
                        ""
                    ),

                    "delay": train.get(
                        "status",
                        ""
                    ),

                    "track": train.get(
                        "track",
                        ""
                    ),

                    "direction": direction_name,

                    "path": train.get(
                        "path",
                        ""
                    ),
                })

    return {
        "station": station,
        "arrivals": arrivals
    }
