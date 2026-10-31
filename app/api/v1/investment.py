from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.models.market import InvestmentScenario
from app.models.user import User
from app.schemas.market import InvestmentInput, InvestmentResult
from app.services.investment import calculate_investment

router = APIRouter()


@router.post("/investment/calculate", response_model=InvestmentResult)
def investment_calculate(
    payload: InvestmentInput,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    result = calculate_investment(payload)
    scenario = InvestmentScenario(
        user_id=user.id if user else None,
        property_id=payload.property_id,
        input_parameters=payload.model_dump(mode="json"),
        calculation_version=result.calculation_version,
        results=result.model_dump(mode="json"),
    )
    db.add(scenario)
    db.commit()
    return result
