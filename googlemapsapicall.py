import googlemaps
from geopy.distance import geodesic
from MangoDB_connection import log_chatbot_error

def get_lat_long_google(address, api_key):
    try:
        gmaps = googlemaps.Client(key=api_key)

        # Geocoding an address
        geocode_result = gmaps.geocode(address)

        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            print("line 13", location)

            return {
                "address": address,
                "display_name": '',
                "latitude": float(location['lat']),
                "longitude": float(location['lng']),
                "success": True
            }
        else:
            return {"address": address, "success": False, "error": "No results found"}
        #     return , location['lng']
        # else:
        #     return None, None
    except Exception as e:
        log_chatbot_error(e)



def vincenty_distance(lat1, lon1, lat2, lon2):
    """Calculate distance (in kilometers) between two latitude/longitude points."""
    try:
        point1 = (float(lat1), float(lon1))
        point2 = (float(lat2), float(lon2))
        return geodesic(point1, point2).meters
    except Exception as e:
        log_chatbot_error(e)
        return None

