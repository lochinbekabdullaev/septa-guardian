from fastapi import FastAPI
from pydantic import BaseModel

from septa import get_alerts, get_elevators, get_arrivals
from gemini import plan_trip, replan_trip


app = FastAPI(title="SEPTA Guardian API")


# =========================================================
# REQUEST MODELS
# =========================================================

class TripRequest(BaseModel):
    origin: str
    destination: str
    departure_time: str = "now"


class ReplanRequest(BaseModel):
    origin: str
    destination: str
    current_route: str = ""
    reason: str = ""


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "SEPTA Guardian backend is running!"
    }


# =========================================================
# ALERTS
# =========================================================

@app.get("/api/alerts")
def alerts():
    return get_alerts()


# =========================================================
# ELEVATORS
# =========================================================

@app.get("/api/elevators")
def elevators():
    return get_elevators()


# =========================================================
# LIVE TRAIN ARRIVALS
# =========================================================

@app.get("/api/arrivals/{station}")
def arrivals(station: str):
    return get_arrivals(station)


# =========================================================
# GEMINI TRIP PLANNER
# =========================================================

@app.post("/api/trip/plan")
def trip_plan(request: TripRequest):

    # Get current SEPTA alerts
    alert_data = get_alerts()

    # Get live trains at the origin station
    try:
        arrival_data = get_arrivals(request.origin)
    except Exception:
        arrival_data = {
            "station": request.origin,
            "arrivals": []
        }

    # Ask Gemini to analyze the live SEPTA information
    recommendation = plan_trip(
        origin=request.origin,
        destination=request.destination,
        alerts=alert_data,
        arrivals=arrival_data,
        departure_time=request.departure_time,
    )

    return {
        "origin": request.origin,
        "destination": request.destination,
        "recommendation": recommendation,
        "live_data": {
            "alerts": alert_data,
            "arrivals": arrival_data,
        }
    }


# =========================================================
# GEMINI DISRUPTION REPLANNER
# =========================================================

@app.post("/api/trip/replan")
def trip_replan(request: ReplanRequest):

    # Get fresh SEPTA alerts
    alert_data = get_alerts()

    # Get fresh train information
    try:
        arrival_data = get_arrivals(request.origin)
    except Exception:
        arrival_data = {
            "station": request.origin,
            "arrivals": []
        }

    # Ask Gemini to find an alternative
    recommendation = replan_trip(
        origin=request.origin,
        destination=request.destination,
        current_route=request.current_route,
        reason=request.reason,
        alerts=alert_data,
        arrivals=arrival_data,
    )

    return {
        "origin": request.origin,
        "destination": request.destination,
        "recommendation": recommendation,
        "live_data": {
            "alerts": alert_data,
            "arrivals": arrival_data,
        }
    }
