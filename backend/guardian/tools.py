def get_service_alerts():
    return {
        "alerts": [
            {
                "line": "Broad Street Line",
                "status": "delayed",
                "delay_minutes": 20,
                "description": "Northbound service is experiencing delays."
            }
        ]
    }


def get_elevator_outages():
    return {
        "outages": [
            {
                "station": "City Hall",
                "status": "out_of_service"
            }
        ]
    }

