"""AI search, chat, and legacy prediction endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.agent_service import run_ai_chat, run_ai_search
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import APIError
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AISearchRequest,
    AISearchResponse,
    LLMResponse,
    PredictionRequest,
    PredictionResponse,
    PromptRequest,
)

router = APIRouter()
settings = get_settings()


@router.post("/ai/search", response_model=AISearchResponse)
def ai_search(payload: AISearchRequest, db: Session = Depends(get_db)):
    return run_ai_search(db, payload)


@router.post("/ai/chat", response_model=AIChatResponse)
def ai_chat(payload: AIChatRequest, db: Session = Depends(get_db)):
    return run_ai_chat(db, payload)


@router.post("/llm", response_model=LLMResponse)
def call_llm(req: PromptRequest):
    """Legacy direct LLM endpoint for the WASM browser agent."""
    if not settings.google_api_key:
        return LLMResponse(text="GOOGLE_API_KEY is not configured on the server.")
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(req.prompt)
        return LLMResponse(text=response.text)
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            return LLMResponse(text="API quota exceeded. Please try again later.")
        return LLMResponse(text=f"Error: {msg}")


@router.post("/predict", response_model=PredictionResponse)
def predict_price(request: PredictionRequest):
    """Legacy LangGraph price-prediction pipeline (geo → nearby → news → LLM)."""
    try:
        from app.agent import agent_executor
    except Exception as exc:
        raise APIError(503, "SERVICE_UNAVAILABLE", f"Prediction agent unavailable: {exc}") from exc

    if not settings.google_api_key:
        raise APIError(503, "SERVICE_UNAVAILABLE", "GOOGLE_API_KEY required for prediction agent.")

    result = agent_executor.invoke({"location": request.location, "area_sqft": request.area_sqft})
    return PredictionResponse(
        predicted_rate=result.get("predicted_rate", 0),
        explanation=result.get("explanation", ""),
        limitations=[
            "LLM estimate only — not a certified valuation.",
            "Uses asking-market heuristics and public signals; not completed transactions.",
        ],
    )
