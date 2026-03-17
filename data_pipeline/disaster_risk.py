import requests

# FEMA National Risk Index - Public ArcGIS Feature Service (no API key required)
# Source: https://hazards.geoplatform.gov/portal/home/item.html?id=cf60c608803e4ccd87ca13cbe40d9151
# County-level natural hazard risk scores

FEMA_NRI_COUNTY_URL = (
    "https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/"
    "NRI_Table_Counties/FeatureServer/0/query"
)

def get_disaster_risk(lat, lon):
    """
    Queries FEMA's National Risk Index (NRI) public ArcGIS feature service.
    Returns composite risk score and breakdown by hazard type for the county
    that contains the given coordinates.
    
    No API key required. Data covers all US counties.
    Source: https://hazards.fema.gov/nri/
    """
    try:
        # Standard ArcGIS REST Point Intersection Query
        params = {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "COUNTY,STATE,RISK_SCORE,RISK_RATNG,EAL_SCORE,SOVI_SCORE,RESL_SCORE,"
                         "HWAV_RISKR,HRCN_RISKR,ERQK_RISKR,LNDS_RISKR,RFLD_RISKR,SWND_RISKR",
            "returnGeometry": "false",
            "inSR": "4326",
            "outSR": "4326",
            "f": "json"
        }
        resp = requests.get(FEMA_NRI_COUNTY_URL, params=params, timeout=20)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        
        if features:
            attrs = features[0]["attributes"]
            risk_score = attrs.get("RISK_SCORE", 50.0)
            risk_rating = attrs.get("RISK_RATNG", "Unknown")
            county = attrs.get("COUNTY", "Unknown")
            state = attrs.get("STATE", "Unknown")
            
            # Convert FEMA 0-100 risk score to a normalized 0-1 "safe" factor (inverted)
            # Higher risk score = lower site safety
            safety_score = round(1.0 - (float(risk_score or 50) / 100), 3)
            
            return {
                "county": county,
                "state": state,
                "fema_risk_score": round(float(risk_score or 50), 1),
                "fema_risk_rating": risk_rating or "Moderate",
                "safety_score": safety_score,
                "hazard_breakdown": {
                    "heat_wave": attrs.get("HWAV_RISKR", "N/A"),
                    "hurricane": attrs.get("HRCN_RISKR", "N/A"),
                    "earthquake": attrs.get("ERQK_RISKR", "N/A"),
                    "landslide": attrs.get("LNDS_RISKR", "N/A"),
                    "riverine_flood": attrs.get("RFLD_RISKR", "N/A"),
                    "strong_wind": attrs.get("SWND_RISKR", "N/A"),
                },
                "data_source": "FEMA NRI (ArcGIS Public Service)"
            }
    except Exception as e:
        print(f"[disaster_risk] FEMA NRI API error: {e} — using fallback")
    
    # --- Fallback: moderate risk with warning ---
    return {
        "county": "Unknown",
        "state": "Unknown",
        "fema_risk_score": 50.0,
        "fema_risk_rating": "Moderate",
        "safety_score": 0.5,
        "hazard_breakdown": {},
        "data_source": "Simulated (FEMA API unavailable)"
    }

if __name__ == "__main__":
    print("Ashburn, VA:", get_disaster_risk(39.0438, -77.4874))
    print("Los Angeles, CA:", get_disaster_risk(34.0522, -118.2437))
    print("Chicago, IL:", get_disaster_risk(41.8781, -87.6298))
