import requests

def get_weather_pue(lat, lon):
    """
    Fetches real-time weather data from Open-Meteo and estimates PUE.
    The Higher the temperature, the higher the cooling cost (PUE).
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "current_weather" in data:
            temp = data["current_weather"]["temperature"]
            # Baseline PUE of 1.1 at 15C. 
            # Every 10C above 15C adds 0.05 to PUE.
            pue_estimate = 1.1 + max(0, temp - 15) * 0.005
            pue_estimate = round(min(1.6, max(1.1, pue_estimate)), 3)
            
            return {
                "ambient_temp_c": temp,
                "pue_estimate": pue_estimate,
                "weather_source": "Open-Meteo Live"
            }
    except Exception as e:
        print(f"Weather API Error: {e}")
        
    # Fallback simulation if API fails
    return {
        "ambient_temp_c": 20.0,
        "pue_estimate": 1.25,
        "weather_source": "Fallback"
    }

if __name__ == "__main__":
    # Test for Ashburn, VA (39.0438, -77.4874)
    print(get_weather_pue(39.0438, -77.4874))
