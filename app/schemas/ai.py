"""AI search and chat schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AISearchRequest(BaseModel):
    query: str = Field(min_length=3)
    session_id: UUID | None = None


class AISearchResponse(BaseModel):
    search_specification: dict[str, Any]
    clarification_required: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    results_reference: UUID | None = None
    results: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1)
    property_ids: list[UUID] = Field(default_factory=list)
    conversation_id: UUID | None = None


class AIChatResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    property_references: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)
    usage_metadata: dict[str, Any] = Field(default_factory=dict)


class PredictionRequest(BaseModel):
    location: str
    area_sqft: float


class PredictionResponse(BaseModel):
    predicted_rate: float
    explanation: str
    limitations: list[str] = Field(default_factory=list)


class PromptRequest(BaseModel):
    prompt: str


class LLMResponse(BaseModel):
    text: str
