import requests
from app.config import GOOGLE_MAPS_API_KEY, NEWS_API_KEY


def geolocation_tool(location: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": GOOGLE_MAPS_API_KEY}
    res = requests.get(url, params=params, timeout=10).json()

    if not res.get("results"):
        return {"lat": 0, "lng": 0}

    loc = res["results"][0]["geometry"]["location"]
    return {"lat": loc["lat"], "lng": loc["lng"]}


def nearby_entities_tool(lat: float, lng: float):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 2000,
        "key": GOOGLE_MAPS_API_KEY,
    }

    res = requests.get(url, params=params, timeout=10).json()
    return {"count": len(res.get("results", []))}


def negative_news_tool(location: str):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f"{location} crime OR fraud OR scam",
        "apiKey": NEWS_API_KEY,
    }

    res = requests.get(url, params=params, timeout=10).json()
    return {"negative_news_count": len(res.get("articles", []))}


def area_analysis_tool(area_sqft: float):
    if area_sqft < 500:
        return "small"
    elif area_sqft < 1500:
        return "medium"
    return "large"
