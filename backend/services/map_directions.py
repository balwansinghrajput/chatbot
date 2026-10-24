import httpx
import re

async def get_coordinates(query: str) -> dict | None:
    """Geocode a place name using free Nominatim API."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "AIChatbot/1.0"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return {
                    "lat": data[0]["lat"],
                    "lon": data[0]["lon"],
                    "display_name": data[0]["display_name"]
                }
    except Exception as e:
        print(f"[MapDirections] Geocoding error for '{query}': {e}")
    return None

async def get_route(origin_query: str, dest_query: str) -> dict | None:
    """Fetch routing data using free OSRM API."""
    print(f"[MapDirections] Geocoding origin: {origin_query}")
    origin = await get_coordinates(origin_query)
    if not origin:
        return None
        
    print(f"[MapDirections] Geocoding destination: {dest_query}")
    dest = await get_coordinates(dest_query)
    if not dest:
        return None

    # OSRM expects longitude,latitude
    url = f"http://router.project-osrm.org/route/v1/driving/{origin['lon']},{origin['lat']};{dest['lon']},{dest['lat']}"
    params = {
        "overview": "false",
        "steps": "true"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") != "Ok" or not data.get("routes"):
                return None
                
            route = data["routes"][0]
            distance_km = round(route["distance"] / 1000, 1)
            duration_min = round(route["duration"] / 60)
            
            # Extract steps
            steps = []
            if route.get("legs") and route["legs"][0].get("steps"):
                for step in route["legs"][0]["steps"]:
                    maneuver = step.get("maneuver", {})
                    instruction = f"{maneuver.get('type', '')} {maneuver.get('modifier', '')}".strip().capitalize()
                    name = step.get("name")
                    if name:
                        instruction += f" onto {name}"
                    dist = round(step.get("distance", 0))
                    if dist > 0:
                        instruction += f" ({dist}m)"
                    
                    if maneuver.get('type') != "depart" and maneuver.get('type') != "arrive":
                        steps.append(instruction)
            
            return {
                "origin": origin_query,
                "destination": dest_query,
                "origin_full": origin["display_name"],
                "dest_full": dest["display_name"],
                "distance": f"{distance_km} km",
                "duration": f"{duration_min} mins",
                "steps": steps
            }
    except Exception as e:
        print(f"[MapDirections] OSRM routing error: {e}")
        
    return None

async def extract_and_route(user_query: str) -> dict | None:
    """Extract origin and destination from user query and return route."""
    # Simple regex extraction for "directions from X to Y"
    match = re.search(r"(?:directions|route|map|distance)\s+from\s+(.+?)\s+to\s+(.+?)(?:\s|$|\?)", user_query, flags=re.IGNORECASE)
    if match:
        origin = match.group(1).strip()
        dest = match.group(2).strip()
        return await get_route(origin, dest)
        
    # Check for "to X from Y"
    match2 = re.search(r"(?:directions|route|map|distance)\s+to\s+(.+?)\s+from\s+(.+?)(?:\s|$|\?)", user_query, flags=re.IGNORECASE)
    if match2:
        dest = match2.group(1).strip()
        origin = match2.group(2).strip()
        return await get_route(origin, dest)

    return None
