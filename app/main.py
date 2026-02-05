from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

from app.schemas import PredictionRequest, PredictionResponse, PromptRequest, LLMResponse
from app.agent import agent_executor
from app.config import GOOGLE_API_KEY

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

app = FastAPI(title="Real Estate Prediction Agent")

# Enable CORS for browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Real Estate Agent API is running"}


@app.post("/llm", response_model=LLMResponse)
async def call_llm(req: PromptRequest):
    """
    Direct LLM endpoint for browser-based LangGraph agent.
    Accepts a prompt and returns Gemini response.
    """
    try:
        response = gemini_model.generate_content(req.prompt)
        return LLMResponse(text=response.text)
    except Exception as e:
        error_msg = str(e)
        # Handle specific error types
        if "429" in error_msg or "quota" in error_msg.lower():
            return LLMResponse(text=f"⚠️ API quota exceeded. Please try again later or check your billing settings.")
        elif "404" in error_msg or "not found" in error_msg.lower():
            return LLMResponse(text=f"⚠️ Model not available. Please check configuration.")
        else:
            return LLMResponse(text=f"⚠️ Error: {error_msg}")


@app.post("/predict", response_model=PredictionResponse)
def predict_price(request: PredictionRequest):
    result = agent_executor.invoke({
        "location": request.location,
        "area_sqft": request.area_sqft
    })

    return PredictionResponse(
        predicted_rate=result["predicted_rate"],
        explanation=result["explanation"]
    )
