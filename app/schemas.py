from pydantic import BaseModel


class PredictionRequest(BaseModel):
    location: str
    area_sqft: float


class PredictionResponse(BaseModel):
    predicted_rate: float
    explanation: str


# Schemas for browser LLM endpoint
class PromptRequest(BaseModel):
    prompt: str


class LLMResponse(BaseModel):
    text: str
