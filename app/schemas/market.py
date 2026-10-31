"""Price analysis and investment schemas."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PriceAnalysisResponse(BaseModel):
    listing_id: UUID
    asking_price: str | None
    area_basis: str | None
    asking_price_per_sq_ft: str | None
    benchmark: dict
    comparables_count: int = 0
    formula: str | None = None
    limitations: list[str] = Field(default_factory=list)


class InvestmentInput(BaseModel):
    purchase_price: Decimal
    stamp_duty_pct: Decimal = Decimal("5")
    registration_pct: Decimal = Decimal("1")
    brokerage_pct: Decimal = Decimal("1")
    other_costs: Decimal = Decimal("0")
    monthly_rent: Decimal
    vacancy_months_per_year: Decimal = Decimal("1")
    annual_maintenance: Decimal = Decimal("0")
    annual_property_tax: Decimal = Decimal("0")
    other_annual_expenses: Decimal = Decimal("0")
    property_id: UUID | None = None


class InvestmentResult(BaseModel):
    calculation_version: str = "v1"
    total_acquisition_cost: str
    annual_gross_rent: str
    annual_effective_rent: str
    annual_operating_expenses: str
    gross_yield_pct: str
    net_yield_pct: str
    assumptions: list[str]
    sensitivity: dict
    disclaimer: str
    limitations: list[str] = Field(default_factory=list)
