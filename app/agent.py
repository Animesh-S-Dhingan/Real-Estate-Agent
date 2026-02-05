import json
import re
from typing import TypedDict

from app.config import GOOGLE_API_KEY
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from app.tools import geolocation_tool, nearby_entities_tool, negative_news_tool, area_analysis_tool


class AgentState(TypedDict, total=False):
    location: str
    area_sqft: float
    lat: float
    lng: float
    nearby_count: int
    negative_news: int
    area_category: str
    predicted_rate: float
    explanation: str


llm = ChatGoogleGenerativeAI(
    model="models/gemini-3-flash-preview",
    temperature=0.2,
    google_api_key=GOOGLE_API_KEY
)



def geo_node(state: AgentState):
    geo = geolocation_tool(state["location"])
    return {"lat": geo.get("lat", 0), "lng": geo.get("lng", 0)}


def nearby_node(state: AgentState):
    data = nearby_entities_tool(state["lat"], state["lng"])
    return {"nearby_count": data.get("count", 0)}


def news_node(state: AgentState):
    news = negative_news_tool(state["location"])
    return {"negative_news": news.get("negative_news_count", 0)}


def area_node(state: AgentState):
    category = area_analysis_tool(state["area_sqft"])
    return {"area_category": category}


import json
import re

def predict_node(state: AgentState):

    prompt = f"""
You are a real estate price prediction engine.

Return ONLY valid JSON. No markdown. No commentary.

Format:
{{
  "predicted_rate": 6500,
  "explanation": "short reason"
}}

Inputs:
Location: {state['location']}
Nearby places: {state.get('nearby_count', 0)}
Negative news: {state.get('negative_news', 'None')}
Area: {state['area_sqft']} sqft
Area category: {state.get('area_category', 'medium')}
"""

    response = llm.invoke(prompt)

    print("Gemini raw response:", response)

    # ✅ Extract text correctly
    text = ""

    if isinstance(response.content, list):
        # Gemini returns list of dicts
        text = response.content[0].get("text", "")
    elif isinstance(response.content, str):
        text = response.content
    else:
        text = str(response)

    text = text.strip()
    print("Gemini parsed text:", text)

    try:
        json_match = re.search(r"\{[\s\S]*\}", text)
        if not json_match:
            raise ValueError("No JSON found")

        data = json.loads(json_match.group())

        return {
            "predicted_rate": float(data["predicted_rate"]),
            "explanation": data["explanation"]
        }

    except Exception as e:
        print("JSON parse error:", e)
        return {
            "predicted_rate": 0,
            "explanation": f"Failed to parse Gemini response: {text}"
        }




graph = StateGraph(AgentState)

graph.add_node("geo", geo_node)
graph.add_node("nearby", nearby_node)
graph.add_node("news", news_node)
graph.add_node("area", area_node)
graph.add_node("predict", predict_node)

graph.set_entry_point("geo")
graph.add_edge("geo", "nearby")
graph.add_edge("nearby", "news")
graph.add_edge("news", "area")
graph.add_edge("area", "predict")
graph.add_edge("predict", END)

agent_executor = graph.compile()
