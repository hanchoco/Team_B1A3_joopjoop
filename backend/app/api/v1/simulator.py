"""Policy-benefit simulator routes (CalcType-based, see policy_engine.calc_type)."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.crud import policies as policy_crud
from app.schemas.simulator import SimulateBenefitRequest, SimulatorResult
from app.services import policy_service
from app.services.errors import NotFoundError, SimulationError
from app.services.policy_engine.simulator import UnsupportedCalcTypeError, simulate

router = APIRouter(tags=["simulator"])


@router.post(
    "/policies/{policy_id}/benefits/{benefit_id}/simulate",
    response_model=SimulatorResult,
)
def simulate_policy_benefit(
    policy_id: int,
    benefit_id: int,
    payload: SimulateBenefitRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SimulatorResult:
    """Run the CalcType-derived simulator calculation for one policy benefit."""

    bundle = policy_crud.get_policy_bundle(db, policy_id)
    if bundle is None or not bundle.policy.is_active:
        raise NotFoundError("정책을 찾을 수 없습니다.")
    benefit = next((item for item in bundle.benefits if item.id == benefit_id), None)
    if benefit is None:
        raise NotFoundError("정책 혜택을 찾을 수 없습니다.")

    policy_like = policy_service.build_policy_like_for_calc_type(bundle)
    try:
        return simulate(benefit, policy_like, payload.user_input)
    except (UnsupportedCalcTypeError, ValueError) as exc:
        raise SimulationError(str(exc)) from exc
