from septa import get_alerts, get_elevators, get_arrivals


def get_service_alerts():
    """Get current SEPTA service alerts."""
    return get_alerts()


def get_elevator_outages():
    """Get current SEPTA elevator outages."""
    return get_elevators()


def get_station_arrivals(station: str):
    """Get live SEPTA arrivals for a station."""
    return get_arrivals(station)
