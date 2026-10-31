"""Deterministic investment calculations (PRD INV-003 / INV-004)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.schemas.market import InvestmentInput, InvestmentResult

CALC_VERSION = "v1"
Q = Decimal("0.01")


def _money(value: Decimal) -> str:
    return str(value.quantize(Q, rounding=ROUND_HALF_UP))


def _pct(value: Decimal) -> str:
    return str(value.quantize(Q, rounding=ROUND_HALF_UP))


def calculate_investment(data: InvestmentInput) -> InvestmentResult:
    stamp = data.purchase_price * data.stamp_duty_pct / Decimal("100")
    registration = data.purchase_price * data.registration_pct / Decimal("100")
    brokerage = data.purchase_price * data.brokerage_pct / Decimal("100")
    total_acquisition = data.purchase_price + stamp + registration + brokerage + data.other_costs

    annual_gross = data.monthly_rent * Decimal("12")
    occupied_months = Decimal("12") - data.vacancy_months_per_year
    if occupied_months < 0:
        occupied_months = Decimal("0")
    annual_effective = data.monthly_rent * occupied_months
    annual_opex = data.annual_maintenance + data.annual_property_tax + data.other_annual_expenses

    gross_yield = (
        (annual_gross / data.purchase_price * Decimal("100")) if data.purchase_price > 0 else Decimal("0")
    )
    net_yield = (
        ((annual_effective - annual_opex) / total_acquisition * Decimal("100"))
        if total_acquisition > 0
        else Decimal("0")
    )

    # Sensitivity: ±10% rent and +1 vacancy month
    rent_up = data.monthly_rent * Decimal("1.1")
    rent_down = data.monthly_rent * Decimal("0.9")
    sens = {
        "rent_plus_10_net_yield_pct": _pct(
            ((rent_up * occupied_months - annual_opex) / total_acquisition * Decimal("100"))
            if total_acquisition
            else Decimal("0")
        ),
        "rent_minus_10_net_yield_pct": _pct(
            ((rent_down * occupied_months - annual_opex) / total_acquisition * Decimal("100"))
            if total_acquisition
            else Decimal("0")
        ),
        "vacancy_plus_1_month_net_yield_pct": _pct(
            (
                (
                    data.monthly_rent * max(Decimal("0"), occupied_months - Decimal("1"))
                    - annual_opex
                )
                / total_acquisition
                * Decimal("100")
            )
            if total_acquisition
            else Decimal("0")
        ),
    }

    return InvestmentResult(
        calculation_version=CALC_VERSION,
        total_acquisition_cost=_money(total_acquisition),
        annual_gross_rent=_money(annual_gross),
        annual_effective_rent=_money(annual_effective),
        annual_operating_expenses=_money(annual_opex),
        gross_yield_pct=_pct(gross_yield),
        net_yield_pct=_pct(net_yield),
        assumptions=[
            f"Stamp duty {data.stamp_duty_pct}% (verify with current official rates).",
            f"Registration {data.registration_pct}% (estimate only).",
            f"Brokerage {data.brokerage_pct}%.",
            f"Vacancy assumption: {data.vacancy_months_per_year} months/year.",
            "Gross yield uses asking purchase price; net yield uses total acquisition cost.",
        ],
        sensitivity=sens,
        disclaimer=(
            "Estimate only — not a certified valuation, tax advice, or guarantee of rental income."
        ),
        limitations=[
            "Rates and rules require current official verification.",
            "Does not include financing costs unless provided in other_costs.",
        ],
    )
