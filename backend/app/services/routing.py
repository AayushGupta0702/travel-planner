import httpx

async def get_route_geometry(waypoints: list[tuple[float, float]]) -> dict:
    """
    Fetch driving route geometry and metadata from public OSRM.
    Args:
        waypoints: List of (latitude, longitude) tuples in sequence.
    """
    if len(waypoints) < 2:
        return {"geometry": None, "distance": 0, "duration": 0}
        
    # OSRM expects longitude,latitude format separated by semicolons
    coords_str = ";".join([f"{lng},{lat}" for lat, lng in waypoints])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=8.0)
            if response.status_code == 200:
                data = response.json()
                if "routes" in data and len(data["routes"]) > 0:
                    route = data["routes"][0]
                    return {
                        "geometry": route.get("geometry"), # GeoJSON LineString
                        "distance_meters": route.get("distance"),
                        "duration_seconds": route.get("duration")
                    }
    except Exception as e:
        print(f"Error fetching OSRM route: {e}")

    # Fallback to direct straight line if API fails or rate-limits
    # GeoJSON coordinates format is [longitude, latitude]
    coordinates = [[lng, lat] for lat, lng in waypoints]
    return {
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        },
        "distance_meters": 0,
        "duration_seconds": 0
    }
