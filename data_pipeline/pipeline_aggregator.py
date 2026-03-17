import csv
import os
import sys

# Ensure the data_pipeline folder is on the path when called from other modules
sys.path.insert(0, os.path.dirname(__file__))

from power_capacity import get_power_capacity
from zoning import get_zoning_data
from carbon_intensity import get_carbon_intensity
from osm_proximity import get_live_osm_data
from weather_pue import get_weather_pue
from disaster_risk import get_disaster_risk
from water_access import get_water_access

def run_pipeline(coordinates, verbose=True):
    """
    Orchestrates all data pipeline modules for a list of (lat, lon) coordinates.
    
    Data Sources:
    - Open-Meteo:  Real-time weather & PUE estimate (no key)
    - OSM/Overpass: Address, substation, highway, fiber distances (no key)  
    - FEMA NRI:    Natural disaster risk score by county (no key)
    - USGS:        Nearest stream gauge & water availability (no key)
    - EIA API v2:  Electricity price + carbon intensity by state (requires EIA_API_KEY)
    - Zoning:      Land use classification (simulated - no municipal GIS API is universal)

    Returns: path to the output CSV file
    """
    output_file = os.path.join(os.path.dirname(__file__), "site_data.csv")
    
    # ── Phase 2: Real Data Dependencies Check ──
    zoning_db_path = os.path.join(os.path.dirname(__file__), "cache", "unified_zoning.parquet")
    if not os.path.exists(zoning_db_path):
        if verbose: print("\n[pipeline_aggregator] 🌐 Building NY/NJ/PA Unified Zoning GIS Database...")
        from zoning_gis_builder import build_unified_database
        build_unified_database()
        import importlib, zoning
        importlib.reload(zoning)
        global get_zoning_data
        from zoning import get_zoning_data

    queue_cache_path = os.path.join(os.path.dirname(__file__), "cache", "grid_queue_active.csv")
    if not os.path.exists(queue_cache_path):
        if verbose: print("\n[pipeline_aggregator] ⚡ Scraping PJM and NYISO Interconnection Queues...")
        from pjm_nyiso_scraper import run_scraper_and_cache_locally
        run_scraper_and_cache_locally(output_path=queue_cache_path)
        import importlib, power_capacity
        importlib.reload(power_capacity)
        global get_power_capacity
        from power_capacity import get_power_capacity
    
    results = []
    
    for i, (lat, lon) in enumerate(coordinates):
        if verbose:
            print(f"\n[{i+1}/{len(coordinates)}] Fetching data for ({lat}, {lon})...")

        # --- Real-time weather (Open-Meteo, free, no key) ---
        weather = get_weather_pue(lat, lon)
        if verbose:
            print(f"  ✅ Weather: {weather['ambient_temp_c']}°C, PUE={weather['pue_estimate']}")

        # --- OSM: address + infrastructure proximity (Overpass, free, no key) ---
        osm = get_live_osm_data(lat, lon)
        if verbose:
            print(f"  ✅ OSM: {osm['address'][:60]}...")
            print(f"     Substation={osm['dist_to_substation_km']}km, "
                  f"Highway={osm['dist_to_highway_km']}km, "
                  f"Fiber={osm['dist_to_fiber_km']}km")

        # --- FEMA NRI: disaster risk (ArcGIS public service, no key) ---
        disaster = get_disaster_risk(lat, lon)
        if verbose:
            print(f"  ✅ FEMA: {disaster.get('county')}, {disaster.get('state')} — "
                  f"Risk={disaster['fema_risk_score']}, Rating={disaster['fema_risk_rating']}")

        # --- USGS: water access (Water Services API, free, no key) ---
        water = get_water_access(lat, lon)
        if verbose:
            print(f"  ✅ USGS: {water['water_availability']} ({water['avg_streamflow_cfs']} cfs)")

        # --- EIA: power + carbon (key optional; falls back to regional simulation) ---
        power = get_power_capacity(lat, lon)
        carbon = get_carbon_intensity(lat, lon)
        if verbose:
            print(f"  ✅ EIA Power: {power['power_capacity_mw']} MW @ "
                  f"{power['retail_price_cents_kwh']}¢/kWh [{power['data_source']}]")
            print(f"  ✅ EIA Carbon: {carbon['carbon_intensity']} gCO2/kWh [{carbon['data_source']}]")

        # --- Zoning: land use (simulated — no universal municipal GIS API) ---
        zoning = get_zoning_data(lat, lon)
        if verbose:
            print(f"  ✅ Zoning: {zoning['zoning_type']} / {zoning['permit_status']}")

        row = {
            # Location
            "latitude": lat,
            "longitude": lon,
            "address": osm["address"][:80],
            "county": disaster.get("county", "N/A"),
            "state": power.get("state", "N/A"),
            # Power & Energy
            "power_capacity_mw": power["power_capacity_mw"],
            "grid_stability": power["grid_stability"],
            "retail_price_cents_kwh": power["retail_price_cents_kwh"],
            "carbon_intensity_gco2": carbon["carbon_intensity"],
            "carbon_source": carbon.get("primary_source", "N/A"),
            # Climate & PUE
            "ambient_temp_c": weather["ambient_temp_c"],
            "live_pue": weather["pue_estimate"],
            # Infrastructure Proximity
            "dist_to_substation_km": osm["dist_to_substation_km"],
            "dist_to_highway_km": osm["dist_to_highway_km"],
            "dist_to_fiber_km": osm["dist_to_fiber_km"],
            # Risk & Environment
            "fema_risk_score": disaster["fema_risk_score"],
            "fema_risk_rating": disaster["fema_risk_rating"],
            "safety_score": disaster["safety_score"],
            "water_availability": water["water_availability"],
            "avg_streamflow_cfs": water["avg_streamflow_cfs"],
            "water_score": water["water_score"],
            # Zoning (simulated)
            "zoning_type": zoning["zoning_type"],
            "permit_status": zoning["permit_status"],
            "zoning_suitability": zoning["suitability_score"],
        }
        results.append(row)

    # Save to CSV
    fieldnames = list(results[0].keys()) if results else []
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Pipeline complete. {len(results)} sites saved to:\n   {output_file}")
    return output_file, results


if __name__ == "__main__":
    # Primary data center candidate locations
    targets = [
        (38.8048, -77.0469),   # Alexandria, VA
        (40.7128, -74.0060),   # New York, NY
        (39.0438, -77.4874),   # Ashburn, VA (Data Center Alley)
        (41.8781, -87.6298),   # Chicago, IL
        (34.0522, -118.2437),  # Los Angeles, CA
    ]
    run_pipeline(targets)
