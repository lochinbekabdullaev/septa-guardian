import os
import zipfile
import pandas as pd


GTFS_DIR = "gtfs"


def load_gtfs():
    stops_path = os.path.join(GTFS_DIR, "stops.txt")
    routes_path = os.path.join(GTFS_DIR, "routes.txt")
    trips_path = os.path.join(GTFS_DIR, "trips.txt")
    stop_times_path = os.path.join(GTFS_DIR, "stop_times.txt")

    return {
        "stops": pd.read_csv(stops_path),
        "routes": pd.read_csv(routes_path),
        "trips": pd.read_csv(trips_path),
        "stop_times": pd.read_csv(stop_times_path),
    }


def find_station(stops, name):
    matches = stops[
        stops["stop_name"]
        .str.contains(name, case=False, na=False)
    ]

    return matches


def find_routes_between(data, origin, destination):

    stops = data["stops"]
    stop_times = data["stop_times"]
    trips = data["trips"]
    routes = data["routes"]

    origin_stops = find_station(stops, origin)
    destination_stops = find_station(stops, destination)

    if origin_stops.empty or destination_stops.empty:
        return []

    origin_ids = set(origin_stops["stop_id"])
    destination_ids = set(destination_stops["stop_id"])

    origin_times = stop_times[
        stop_times["stop_id"].isin(origin_ids)
    ][
        ["trip_id", "stop_sequence", "stop_id"]
    ]

    destination_times = stop_times[
        stop_times["stop_id"].isin(destination_ids)
    ][
        ["trip_id", "stop_sequence", "stop_id"]
    ]

    merged = origin_times.merge(
        destination_times,
        on="trip_id",
        suffixes=("_origin", "_destination")
    )

    # Destination must occur after origin
    merged = merged[
        merged["stop_sequence_destination"]
        > merged["stop_sequence_origin"]
    ]

    if merged.empty:
        return []

    merged = merged.merge(
        trips,
        on="trip_id",
        how="left"
    )

    merged = merged.merge(
        routes,
        on="route_id",
        how="left"
    )

    results = []

    for _, row in merged.head(20).iterrows():

        results.append({
            "trip_id": row["trip_id"],
            "route_id": row["route_id"],
            "route_name": row.get("route_long_name", ""),
            "origin_stop": origin,
            "destination_stop": destination,
            "origin_sequence": int(
                row["stop_sequence_origin"]
            ),
            "destination_sequence": int(
                row["stop_sequence_destination"]
            ),
        })

    return results