from decimal import Decimal

from app.schemas.market import InvestmentInput
from app.services.investment import calculate_investment


def test_gross_and_net_yield():
    result = calculate_investment(
        InvestmentInput(
            purchase_price=Decimal("10000000"),
            monthly_rent=Decimal("40000"),
            stamp_duty_pct=Decimal("5"),
            registration_pct=Decimal("1"),
            brokerage_pct=Decimal("0"),
            vacancy_months_per_year=Decimal("0"),
            annual_maintenance=Decimal("120000"),
        )
    )
    assert result.gross_yield_pct == "4.80"
    assert result.total_acquisition_cost == "10600000.00"
    # net = (480000 - 120000) / 10600000 * 100 = 3.396... -> 3.40
    assert result.net_yield_pct == "3.40"
    assert "Estimate only" in result.disclaimer
