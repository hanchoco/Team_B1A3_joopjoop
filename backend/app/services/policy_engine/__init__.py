"""Pure policy matching and benefit simulation services."""

from app.services.policy_engine.calc_type import (
    CalcType,
    can_simulate,
    resolve_calc_type,
)
from app.services.policy_engine.matcher import (
    ConditionEvaluation,
    PolicyEvaluation,
    evaluate_condition,
    evaluate_policy,
)
from app.services.policy_engine.simulator import (
    CALCULATORS,
    UnsupportedCalcTypeError,
    calculate_cash_voucher,
    calculate_employment_education,
    calculate_housing_rent,
    calculate_loan_interest,
    calculate_savings_asset,
    calculate_tax_deduction,
    simulate,
)

__all__ = [
    "CALCULATORS",
    "CalcType",
    "ConditionEvaluation",
    "PolicyEvaluation",
    "UnsupportedCalcTypeError",
    "calculate_cash_voucher",
    "calculate_employment_education",
    "calculate_housing_rent",
    "calculate_loan_interest",
    "calculate_savings_asset",
    "calculate_tax_deduction",
    "can_simulate",
    "evaluate_condition",
    "evaluate_policy",
    "resolve_calc_type",
    "simulate",
]
