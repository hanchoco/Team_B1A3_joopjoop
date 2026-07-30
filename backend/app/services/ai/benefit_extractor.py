"""
정책 원문 -> 지원 혜택(policy_benefits) 초안 추출

rule_extractor.py(자격조건), checklist_generator.py(제출서류)와 동일한 구조를 따릅니다:
  추출(dataclass) -> create_*_draft() -> (검토) -> validate_*_payload()

원칙:
  - AI(Solar)는 자유 텍스트(지원 내용)만 다룹니다. 구조화된 숫자 필드가 확실하지 않으면
    만들지 않습니다.
  - AI가 만든 결과는 전부 초안입니다.
"""

from dataclasses import asdict, dataclass

try:
    from .prompt_templates import BENEFIT_SYSTEM_PROMPT
    from .solar_client import SolarClient
except ImportError:
    from prompt_templates import BENEFIT_SYSTEM_PROMPT
    from solar_client import SolarClient


# ============================================================
# 타입
# ============================================================

@dataclass
class ExtractedBenefit:
    """policy_benefits 한 행을 담는 타입."""
    benefit_type: str = "OTHER"
    amount_type: str = "VARIABLE"
    min_amount: object = None
    max_amount: object = None
    payment_cycle: str = None
    duration_months: int = None
    max_total_amount: object = None
    display_text: str = None

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 코드 레지스트리 (models/policy.py의 Enum과 동일한 값)
# ============================================================

ALLOWED_BENEFIT_TYPES = {
    "CASH", "DISCOUNT", "LOAN", "SAVINGS", "TAX_REDUCTION", "SERVICE", "OTHER",
}
ALLOWED_AMOUNT_TYPES = {"FIXED", "RANGE", "FORMULA", "VARIABLE"}
ALLOWED_PAYMENT_CYCLES = {"ONCE", "MONTHLY", "YEARLY", "MATURITY", "VARIABLE"}


# ============================================================
# 메인 함수 (실제 프로덕션 진입점)
# ============================================================

async def extract_benefits(policy_payload: dict, *, client: SolarClient) -> list[ExtractedBenefit]:
    """
    policy_payload: youth_policy_api.py가 만든 정규화된 정책 dict.
    client: SolarClient 인스턴스 (seed_policy_data.py가 생성해서 넘겨줌)
    반환: ExtractedBenefit 리스트 (보통 0~1개)
    """
    raw = policy_payload.get("raw_payload") or policy_payload

    support_content = (
        raw.get("plcySprtCn", "") or policy_payload.get("support_content_text", "") or "(없음)"
    )
    user_input = f"""
[정책명] {raw.get('plcyNm') or policy_payload.get('title')}
[지원 내용] {support_content}
"""
    ai_result = await client.complete_json(BENEFIT_SYSTEM_PROMPT, user_input)

    valid_fields = ExtractedBenefit.__dataclass_fields__.keys()
    benefits = []
    for item in ai_result.get("benefits", []):
        benefit_type = item.get("benefit_type")
        amount_type = item.get("amount_type")
        if benefit_type not in ALLOWED_BENEFIT_TYPES:
            continue
        if amount_type not in ALLOWED_AMOUNT_TYPES:
            continue
        payment_cycle = item.get("payment_cycle")
        if payment_cycle is not None and payment_cycle not in ALLOWED_PAYMENT_CYCLES:
            payment_cycle = None
        benefits.append(
            ExtractedBenefit(
                **{
                    **{k: v for k, v in item.items() if k in valid_fields},
                    "benefit_type": benefit_type,
                    "amount_type": amount_type,
                    "payment_cycle": payment_cycle,
                }
            )
        )
    return benefits


def create_benefit_draft(benefit: ExtractedBenefit) -> dict:
    """ExtractedBenefit -> DB INSERT용 dict."""
    return benefit.to_dict()


def validate_benefit_payload(payload: dict) -> list[ExtractedBenefit]:
    """저장된 초안 JSON에서 다시 읽어들인 혜택 목록을 검증하고
    ExtractedBenefit 객체 리스트로 복원합니다.
    payload: {"benefits": [{...dict...}, ...]}
    """
    items = payload.get("benefits")
    if not isinstance(items, list):
        raise ValueError("benefits must be a list")

    valid_fields = ExtractedBenefit.__dataclass_fields__.keys()
    result = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each benefit must be an object")
        benefit_type = item.get("benefit_type")
        amount_type = item.get("amount_type")
        if benefit_type not in ALLOWED_BENEFIT_TYPES:
            raise ValueError(f"unsupported benefit_type: {benefit_type}")
        if amount_type not in ALLOWED_AMOUNT_TYPES:
            raise ValueError(f"unsupported amount_type: {amount_type}")
        payment_cycle = item.get("payment_cycle")
        if payment_cycle is not None and payment_cycle not in ALLOWED_PAYMENT_CYCLES:
            raise ValueError(f"unsupported payment_cycle: {payment_cycle}")
        min_amount = item.get("min_amount")
        max_amount = item.get("max_amount")
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise ValueError("min_amount cannot be greater than max_amount")
        result.append(ExtractedBenefit(**{k: v for k, v in item.items() if k in valid_fields}))
    return result
