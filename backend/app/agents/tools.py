import json
import httpx
from datetime import datetime
from sqlmodel import select
from app.database import get_db_session
from app.models import PlacesCache, Itinerary
from app.services.weather import get_weather_forecast

def to_pure_python(obj):
    """
    Recursively converts protobuf composite types (like RepeatedComposite)
    to standard Python lists and dicts to avoid JSON serialization errors.
    """
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    # Dict-like objects
    if hasattr(obj, "keys") and hasattr(obj, "items"):
        return {k: to_pure_python(v) for k, v in obj.items()}
    # List-like/iterable objects (excluding strings/bytes)
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        return [to_pure_python(x) for x in obj]
    # Fallback check for protobuf composite types
    type_name = type(obj).__name__
    if "Composite" in type_name or "Repeated" in type_name:
        if hasattr(obj, "items"):
            return {k: to_pure_python(v) for k, v in obj.items()}
        return [to_pure_python(x) for x in obj]
    return obj

def get_city_center(location: str) -> tuple[float, float]:
    """
    Returns the coordinates of a city center. Checks a dictionary of common cities
    or geocodes the city name via Nominatim.
    """
    loc_lower = location.lower()
    city_coords = {
        "tokyo": (35.6762, 139.6503),
        "seattle": (47.6062, -122.3321),
        "miami": (25.7617, -80.1918),
        "london": (51.5074, -0.1278),
        "new york": (40.7128, -74.0060),
        "paris": (48.8566, 2.3522),
        "rome": (41.9028, 12.4964),
        "sydney": (-33.8688, 151.2093),
        "barcelona": (41.3851, 2.1734),
    }
    for city, coords in city_coords.items():
        if city in loc_lower:
            return coords
            
    # Geocode city name directly if not in common dict
    headers = {"User-Agent": "travel-planner-agent/1.0 (antigravity-ide)"}
    url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json&limit=1"
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data:
                    return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
        
    return 35.6762, 139.6503 # Default to Tokyo if everything fails


def search_places_of_interest(query: str, location: str) -> str:
    """
    Search for places, sights, parks, restaurants or hotels in a given location.
    Args:
        query: What to search for (e.g. 'parks', 'museums', 'hotels').
        location: The city or area name (e.g. 'Seattle', 'London').
    Returns:
        A JSON string containing list of matching places with names, coordinates, and categories.
    """
    cache_query = f"{query} in {location}".strip().lower()
    
    # 1. Get city center first
    city_lat, city_lon = get_city_center(location)
    
    # 2. Check cache first
    try:
        with get_db_session() as session:
            statement = select(PlacesCache).where(PlacesCache.query == cache_query)
            cached = session.exec(statement).first()
            if cached:
                return cached.results_json
    except Exception as e:
        print(f"Tool cache read error: {e}")

    # 3. Fetch from Nominatim (sync)
    headers = {"User-Agent": "travel-planner-agent/1.0 (antigravity-ide)"}
    search_q = f"{query}, {location}"
    url = f"https://nominatim.openstreetmap.org/search?q={search_q}&format=json&limit=12"
    
    results = []
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, timeout=8.0)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    lat = float(item.get("lat"))
                    lon = float(item.get("lon"))
                    
                    # Spatial filter: only accept coordinates within 1.5 degrees (~150km) of city center
                    if abs(lat - city_lat) < 1.5 and abs(lon - city_lon) < 1.5:
                        parts = item.get("display_name", "").split(",")
                        name = parts[0].strip() if parts else "Location"
                        results.append({
                            "name": name,
                            "display_name": item.get("display_name"),
                            "latitude": lat,
                            "longitude": lon,
                            "category": item.get("type", "attraction")
                        })
    except Exception as e:
        print(f"Error in search_places_of_interest tool: {e}")

    # 4. Local fallback: if no coordinates matched inside the city bounds
    if not results:
        import random
        # Generate a small random offset so multiple fallback spots do not overlap on the exact same spot
        lat_offset = random.uniform(-0.015, 0.015)
        lon_offset = random.uniform(-0.015, 0.015)
        results.append({
            "name": query,
            "display_name": f"{query}, {location}",
            "latitude": city_lat + lat_offset,
            "longitude": city_lon + lon_offset,
            "category": "attraction"
        })

    # 5. Cache and return results
    results_json = json.dumps(results)
    try:
        with get_db_session() as session:
            new_cache = PlacesCache(query=cache_query, results_json=results_json)
            session.add(new_cache)
            session.commit()
    except Exception as ce:
        print(f"Tool cache write error: {ce}")
        
    return results_json


def get_weather_for_destination(city: str, date: str) -> str:
    """
    Get the weather forecast for a given city on a specific date to plan outdoor/indoor events.
    Args:
        city: City name (e.g. 'Seattle').
        date: Forecast date in YYYY-MM-DD format (e.g. '2026-06-10').
    """
    forecast = get_weather_forecast(city, date)
    return json.dumps(forecast)


def get_route_geometry_sync(waypoints: list[tuple[float, float]]) -> dict:
    """
    Synchronous helper to fetch driving route geometry from OSRM.
    """
    if len(waypoints) < 2:
        return {"geometry": None, "distance_meters": 0, "duration_seconds": 0}
        
    coords_str = ";".join([f"{lng},{lat}" for lat, lng in waypoints])
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=8.0)
            if response.status_code == 200:
                data = response.json()
                if "routes" in data and len(data["routes"]) > 0:
                    route = data["routes"][0]
                    return {
                        "geometry": route.get("geometry"),
                        "distance_meters": route.get("distance"),
                        "duration_seconds": route.get("duration")
                    }
    except Exception as e:
        print(f"Route sync helper error: {e}")

    coordinates = [[lng, lat] for lat, lng in waypoints]
    return {
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        },
        "distance_meters": 0,
        "duration_seconds": 0
    }


def extract_name_from_description(desc: str) -> str:
    """
    Fallback parser to extract place names from descriptions (e.g. extracting 'India Gate'
    from 'Visit India Gate and take a relaxing walk...').
    """
    if not desc:
        return "Sightseeing"
    desc_lower = desc.lower()
    
    # Try common travel keywords
    for keyword in ["visit ", "explore ", "go to ", "see ", "check into "]:
        if keyword in desc_lower:
            idx = desc_lower.find(keyword) + len(keyword)
            sub = desc[idx:]
            # Cut off at common phrase dividers
            for sep in [".", ",", " and ", " to ", " for ", " or "]:
                if sep in sub:
                    sub = sub.split(sep)[0]
            val = sub.strip()
            if val:
                # Remove articles
                if val.lower().startswith("the "):
                    val = val[4:]
                return val
                
    # Fallback: return first 4 words of description
    words = desc.split()
    if len(words) <= 4:
        return desc
    return " ".join(words[:4])


def save_itinerary_plan(
    title: str,
    destination: str,
    start_date: str,
    end_date: str,
    days: list[dict],
    itinerary_id: Optional[int] = None
) -> str:
    """
    Save or update the finalized itinerary in the database. Call this tool when you have
    generated or updated the travel timeline.
    Args:
        title: Title of the itinerary.
        destination: Main city/region of the trip.
        start_date: Start date of the trip (YYYY-MM-DD).
        end_date: End date of the trip (YYYY-MM-DD).
        days: A list of days, where each day has 'day_number', 'date', and an array of 'activities'.
              Each activity must contain 'name', 'time', 'latitude', 'longitude', 'description', and 'weather_condition'.
        itinerary_id: (Optional) ID of the existing itinerary to overwrite. If not provided, a new one is created.
    Returns:
        JSON string containing the saved itinerary's details and ID.
    """
    # Convert protobuf structures into standard Python lists/dicts
    days = to_pure_python(days)

    # 1. Detect if the model passed a flat list of activities instead of daily grouped objects
    is_flat_list = False
    if days and isinstance(days, list):
        first_item = days[0]
        if isinstance(first_item, dict) and ("name" in first_item or "description" in first_item or "location" in first_item):
            is_flat_list = True

    if is_flat_list:
        print("Backend detected flat list of activities. Structuring into daily segments...")
        # Check if activities specify day info
        has_day_info = any(("day_number" in act or "day" in act) for act in days)
        
        if has_day_info:
            grouped = {}
            for act in days:
                d_val = act.get("day_number") or act.get("day") or 1
                try:
                    d_num = int(float(d_val))
                except Exception:
                    d_num = 1
                if d_num not in grouped:
                    grouped[d_num] = []
                grouped[d_num].append(act)
            
            structured_days = []
            for d_num in sorted(grouped.keys()):
                structured_days.append({
                    "day_number": d_num,
                    "date": f"Day {d_num}",
                    "activities": grouped[d_num]
                })
            days = structured_days
        else:
            # Distribute activities evenly across the dates of the trip
            try:
                d1 = datetime.strptime(start_date, "%Y-%m-%d")
                d2 = datetime.strptime(end_date, "%Y-%m-%d")
                num_days = max(1, (d2 - d1).days + 1)
            except Exception:
                d1 = datetime.utcnow()
                num_days = 4
                
            import math
            items_per_day = max(1, math.ceil(len(days) / num_days))
            
            structured_days = []
            for i in range(num_days):
                day_num = i + 1
                start_idx = i * items_per_day
                end_idx = start_idx + items_per_day
                day_activities = days[start_idx:end_idx]
                
                # Only append day if there are activities or it's the first day
                if day_activities or day_num == 1:
                    try:
                        from datetime import timedelta
                        curr_date = (d1 + timedelta(days=i)).strftime("%Y-%m-%d")
                    except Exception:
                        curr_date = f"Day {day_num}"
                    
                    structured_days.append({
                        "day_number": day_num,
                        "date": curr_date,
                        "activities": day_activities
                    })
            days = structured_days

    # Automatically geocode any activities that are missing coordinates
    for day in days:
        activities = day.get("activities", [])
        for act in activities:
            # Normalize keys first to ensure frontend renders them correctly
            if "name" not in act and "location" in act:
                act["name"] = act["location"]
            if "time" not in act and "start_time" in act:
                act["time"] = act["start_time"]

            # If name is missing, extract it from description using parser
            if "name" not in act or not act["name"]:
                act["name"] = extract_name_from_description(act.get("description", ""))

            lat = act.get("latitude")
            lon = act.get("longitude")
            if lat is None or lon is None:
                place_name = act.get("name", "")
                if place_name:
                    print(f"Auto-geocoding missing coordinates for: {place_name}")
                    try:
                        # Geocode search query in the trip's destination context
                        raw_res = search_places_of_interest(place_name, destination)
                        res_list = json.loads(raw_res)
                        if res_list:
                            act["latitude"] = res_list[0]["latitude"]
                            act["longitude"] = res_list[0]["longitude"]
                            print(f"Successfully geocoded {place_name} to ({act['latitude']}, {act['longitude']})")
                    except Exception as ge:
                        print(f"Failed to auto-geocode {place_name}: {ge}")

    # 1. Calculate routing geometries for each day
    routes = []
    for day in days:
        activities = day.get("activities", [])
        waypoints = []
        for act in activities:
            lat = act.get("latitude")
            lon = act.get("longitude")
            if lat is not None and lon is not None:
                waypoints.append((float(lat), float(lon)))
        
        route_info = get_route_geometry_sync(waypoints)
        routes.append({
            "day_number": day.get("day_number"),
            "route": route_info
        })
        
    timeline_str = json.dumps(days)
    routes_str = json.dumps(routes)
    
    with get_db_session() as session:
        if itinerary_id:
            db_itinerary = session.get(Itinerary, itinerary_id)
            if db_itinerary:
                db_itinerary.title = title
                db_itinerary.destination = destination
                db_itinerary.start_date = start_date
                db_itinerary.end_date = end_date
                db_itinerary.timeline_json = timeline_str
                db_itinerary.routes_json = routes_str
                session.add(db_itinerary)
                session.commit()
                session.refresh(db_itinerary)
                return json.dumps({"status": "updated", "id": db_itinerary.id, "title": db_itinerary.title})
        
        # Create new
        new_itinerary = Itinerary(
            title=title,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            timeline_json=timeline_str,
            routes_json=routes_str
        )
        session.add(new_itinerary)
        session.commit()
        session.refresh(new_itinerary)
        return json.dumps({"status": "created", "id": new_itinerary.id, "title": new_itinerary.title})
