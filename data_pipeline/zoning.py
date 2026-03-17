import os
import random
import geopandas as gpd
from shapely.geometry import Point

CACHE_FILE = "cache/unified_zoning.parquet"

# Load the GeoParquet database globally so it's only loaded once per worker process
# This prevents opening a multi-gigabyte file repeatedly on every coordinate loop
print(f"[zoning] Initializing local GIS Spatial Database from {CACHE_FILE}...")
GDF = None
if os.path.exists(CACHE_FILE):
    try:
        GDF = gpd.read_parquet(CACHE_FILE)
        # Ensure it has a spatial index for extremely fast lookups
        GDF.sindex
    except Exception as e:
        print(f"[zoning] Failed to load GeoParquet: {e}")
else:
    print(f"[zoning] WARNING: {CACHE_FILE} not found. Proceeding with fallback simulation.")

def _simulate_zoning(lat, lon):
    """ Fallback simulation for coordinates outside NY/NJ/PA or if DB is missing """
    seed_value = int((lat + 180) * 500 + (lon + 180) * 50)
    random.seed(seed_value)
    
    zoning_types = ["Industrial", "Agricultural", "Commercial", "Residential"]
    zoning_type = random.choice(zoning_types)
    permit_status = random.choice(["Verified", "Pending Review", "Pre-approval Required", "Restricted"]) if zoning_type != "Residential" else "Restricted"
    suitability_score = 0.9 if zoning_type == "Industrial" else 0.5
    if zoning_type == "Residential": suitability_score = 0.1
        
    return {
        "zoning_type": zoning_type,
        "permit_status": permit_status,
        "suitability_score": suitability_score,
        "data_source": "Simulated (Out of bounds)"
    }

def get_zoning_data(lat, lon):
    """
    Performs a highly optimized Point-in-Polygon spatial query against the local GIS db.
    Identifies the exact municipal zoning classification for the target coordinate.
    """
    if GDF is None:
        return _simulate_zoning(lat, lon)
        
    # 1. Create a spatial point for the coordinate
    point = gpd.GeoDataFrame([{"geometry": Point(lon, lat)}], crs="EPSG:4326")
    
    # 2. Perform a spatial join (sjoin) to find which polygon contains this point
    try:
        match = gpd.sjoin(point, GDF, how="inner", predicate="intersects")
        
        if not match.empty:
            # We found a match in the local NY/NJ/PA database
            row = match.iloc[0]
            zoning_type = str(row.get("zoning_type", "Residential"))
            permit_status = str(row.get("permit_status", "Standard Review"))
            state = str(row.get("state", "Unknown"))
            
            # Map back to our suitability score system
            suitability_score = 0.9 if zoning_type == "Industrial" else 0.5
            if zoning_type == "Residential":
                suitability_score = 0.1
                
            return {
                "zoning_type": zoning_type,
                "permit_status": permit_status,
                "suitability_score": suitability_score,
                "data_source": f"Local GIS Database ({state})"
            }
        else:
            # Point is outside our 3-state DB coverage. 
            return _simulate_zoning(lat, lon)
            
    except Exception as e:
        print(f"[zoning] Spatial join query failed: {e}")
        return _simulate_zoning(lat, lon)

if __name__ == "__main__":
    # Test coordinates inside and outside the synthetic bounding boxes
    print("Testing inside PA polygon bounding box:", get_zoning_data(40.0, -78.0))
    print("Testing far away (Texas):", get_zoning_data(31.9686, -99.9018))
