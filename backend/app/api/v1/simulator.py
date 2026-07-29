"""Category-specific policy benefit simulator routes."""

from fastapi import APIRouter

from app.schemas.simulator import (
    EmploymentSimulatorRequest,
    FinanceSimulatorRequest,
    HousingSimulatorRequest,
    SimulatorResult,
    TaxSimulatorRequest,
    TransportSimulatorRequest,
    WelfareSimulatorRequest,
)
from app.services.policy_engine.simulator import (
    calculate_employment,
    calculate_finance,
    calculate_housing,
    calculate_tax,
    calculate_transport,
    calculate_welfare,
)

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.post("/housing", response_model=SimulatorResult)
def simulate_housing(payload: HousingSimulatorRequest) -> SimulatorResult:
    """Compare housing costs before and after a policy."""

    return calculate_housing(payload)


@router.post("/transport", response_model=SimulatorResult)
def simulate_transport(payload: TransportSimulatorRequest) -> SimulatorResult:
    """Compare transport costs before and after a policy."""

    return calculate_transport(payload)


@router.post("/finance", response_model=SimulatorResult)
def simulate_finance(payload: FinanceSimulatorRequest) -> SimulatorResult:
    """Compare financing costs before and after a policy."""

    return calculate_finance(payload)


@router.post("/tax", response_model=SimulatorResult)
def simulate_tax(payload: TaxSimulatorRequest) -> SimulatorResult:
    """Compare tax costs before and after a policy."""

    return calculate_tax(payload)


@router.post("/employment", response_model=SimulatorResult)
def simulate_employment(payload: EmploymentSimulatorRequest) -> SimulatorResult:
    """Compare disposable income before and after an employment policy."""

    return calculate_employment(payload)


@router.post("/welfare", response_model=SimulatorResult)
def simulate_welfare(payload: WelfareSimulatorRequest) -> SimulatorResult:
    """Compare living costs before and after a welfare policy."""

    return calculate_welfare(payload)
