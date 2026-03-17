import requests

# USGS Water Services - NWIS Daily Values API (Returns direct streamflow)
# Docs: https://waterservices.usgs.gov/rest/DV-Service.html
USGS_DV_URL = "https://waterservices.usgs.gov/nwis/dv/"

def get_water_access(lat, lon, search_radius_deg=0.5):
    """
    Queries USGS NWIS Water Services to find the nearest active stream gauge 
    within ~55km (0.5 degree radius) and retrieves recent average daily streamflow (cfs).
    No API key required.
    """
    site_id = None
    site_name = "Unknown"
    distance_km = None
    avg_flow_cfs = None

    try:
        # Request daily values for parameter 00060 (Discharge/Streamflow in cfs)
        # Use a bounding box search
        bbox = f"{lon - search_radius_deg:.4f},{lat - search_radius_deg:.4f}," \
               f"{lon + search_radius_deg:.4f},{lat + search_radius_deg:.4f}"
        
        params = {
            "format": "json",
            "bBox": bbox,
            "parameterCd": "00060",  # Streamflow parameter
            "siteStatus": "active",
            "period": "P7D"          # Last 7 days
        }
        
        resp = requests.get(USGS_DV_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        # Parse USGS "WaterML" JSON structure
        time_series = data.get("value", {}).get("timeSeries", [])
        
        if time_series:
            # Find the closest site among returned time series
            best_dist = float('inf')
            best_series = None
            
            for ts in time_series:
                loc = ts.get("sourceInfo", {}).get("geoLocation", {}).get("geogLocation", {})
                s_lat = loc.get("latitude")
                s_lon = loc.get("longitude")
                if s_lat and s_lon:
                    dx = (s_lon - lon) * 88.5
                    dy = (s_lat - lat) * 111.0
                    d = (dx**2 + dy**2)**0.5
                    if d < best_dist:
                        best_dist = d
                        best_series = ts
            
            if best_series:
                source_info = best_series.get("sourceInfo", {})
                site_name = source_info.get("siteName", "Unknown")
                site_id = source_info.get("siteCode", [{}])[0].get("value", "N/A")
                distance_km = round(best_dist, 1)
                
                # Average the values from the last 7 days
                values = best_series.get("values", [{}])[0].get("value", [])
                valid_flows = []
                for v in values:
                    val_str = v.get("value")
                    if val_str is not None:
                        try:
                            valid_flows.append(float(val_str))
                        except ValueError:
                            pass
                
                if valid_flows:
                    avg_flow_cfs = round(sum(valid_flows) / len(valid_flows), 1)

    except Exception as e:
        print(f"[water_access] USGS NWIS API error: {e}")

    # --- Scoring ---
    if avg_flow_cfs is None:
        water_score = 0.5 if distance_km and distance_km < 30 else 0.3
        flow_label = "Unknown"
    elif avg_flow_cfs >= 500:
        water_score = 0.95
        flow_label = "Abundant"
    elif avg_flow_cfs >= 100:
        water_score = 0.75
        flow_label = "Adequate"
    elif avg_flow_cfs >= 20:
        water_score = 0.5
        flow_label = "Limited"
    else:
        water_score = 0.2
        flow_label = "Scarce"

    return {
        "nearest_gauge": site_name,
        "gauge_id": site_id or "N/A",
        "distance_to_gauge_km": distance_km or "N/A",
        "avg_streamflow_cfs": avg_flow_cfs or "N/A",
        "water_availability": flow_label,
        "water_score": water_score,
        "data_source": "USGS Water Services API" if site_id else "USGS (no gauge found)"
    }

if __name__ == "__main__":
    print("Ashburn, VA:", get_water_access(39.0438, -77.4874))
    print("Chicago, IL:", get_water_access(41.8781, -87.6298))
