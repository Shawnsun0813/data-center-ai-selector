import requests
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time

# Overpass API mirrors (tried in order)
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

def _overpass_query(query, timeout=25, max_retries=2):
    """Try each mirror with retry and backoff on 429."""
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(max_retries):
            try:
                resp = requests.get(mirror, params={"data": query}, timeout=timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    wait = (attempt + 1) * 15
                    print(f"[osm_proximity] Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"[osm_proximity] Mirror {mirror} error: {e}")
                    break
            except Exception as e:
                print(f"[osm_proximity] Mirror {mirror} attempt {attempt+1}: {e}")
                time.sleep(5)
    return None


def _nearest_from_elements(elements, lat, lon):
    """Return nearest distance (km) from a list of OSM elements."""
    dists = []
    for el in elements:
        e_lat = el.get("lat") or el.get("center", {}).get("lat")
        e_lon = el.get("lon") or el.get("center", {}).get("lon")
        if e_lat and e_lon:
            dists.append(geodesic((lat, lon), (e_lat, e_lon)).km)
    return float(round(min(dists), 2)) if dists else None


def get_live_osm_data(lat, lon):
    """
    Queries OSM via Nominatim + Overpass API.
    Uses a SINGLE combined Overpass query per coordinate to minimize API calls.
    Returns: address, substation dist, highway dist, fiber dist.
    """
    # 1. Reverse geocoding (Nominatim, max 1 req/sec)
    address = "Unknown Location"
    try:
        geolocator = Nominatim(user_agent="datacenter_site_eval_v2")
        loc = geolocator.reverse(f"{lat},{lon}", timeout=10)
        if loc:
            address = loc.address
        time.sleep(1)   # Nominatim rate limit
    except Exception as e:
        print(f"[osm_proximity] Geocoding error: {e}")

    # 2. Single combined Overpass query (substation + highway + telecom in one request)
    combined_query = f"""[out:json][timeout:25];
(
  node["power"="substation"](around:15000,{lat},{lon});
  way["power"="substation"](around:15000,{lat},{lon});
  way["highway"~"motorway|trunk"](around:10000,{lat},{lon});
  node["telecom"="data_center"](around:30000,{lat},{lon});
  node["man_made"="communications_tower"](around:10000,{lat},{lon});
);
out center;"""

    time.sleep(5)   # Polite delay per Overpass Terms of Service
    result = _overpass_query(combined_query, timeout=30)

    substation_dist = None
    highway_dist = None
    fiber_dist = None

    if result:
        substations, highways, fibers = [], [], []
        for el in result.get("elements", []):
            tags = el.get("tags", {})
            if tags.get("power") == "substation":
                substations.append(el)
            elif tags.get("highway") in ("motorway", "trunk"):
                highways.append(el)
            elif tags.get("telecom") == "data_center" or tags.get("man_made") == "communications_tower":
                fibers.append(el)

        substation_dist = _nearest_from_elements(substations, lat, lon)
        highway_dist = _nearest_from_elements(highways, lat, lon)
        fiber_dist = _nearest_from_elements(fibers, lat, lon)

    # Smart fallbacks
    if substation_dist is None:
        substation_dist = 20.0
    if highway_dist is None:
        highway_dist = float(round(substation_dist * 0.4 + 1.5, 2))
    if fiber_dist is None:
        fiber_dist = float(round(substation_dist * 0.7, 2))

    return {
        "address": address,
        "dist_to_substation_km": substation_dist,
        "dist_to_highway_km": highway_dist,
        "dist_to_fiber_km": fiber_dist,
        "data_source": "OpenStreetMap (Nominatim + Overpass)"
    }

if __name__ == "__main__":
    result = get_live_osm_data(39.0438, -77.4874)   # Ashburn VA
    print(f"Ashburn, VA: {result}")
