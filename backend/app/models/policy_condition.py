"""
app/models/policy_condition.py

DB.pdf 6-1장 policy_conditions 테이블 기준 SQLAlchemy 모델.
rule_extractor.py의 process_policy()가 반환하는 policy_conditions 리스트의
각 항목(dict) 키가 이 모델의 컬럼명과 1:1로 맞습니다:
  condition_key, operator, expected_value_json, condition_group_no,
  is_required, check_mode, description, failure_message, sort_order

주의: 이 파일은 다빈(AI)이 초안만 만든 것입니다. 실제 반영 전 나경님 확인 필요
(특히 Base import 경로, 다른 모델과의 관계 설정 방식은 프로젝트 컨벤션에 맞춰 조정).
"""

from sqlalchemy import (
    Column,
    BigInteger,
    SmallInteger,
    String,
    Boolean,
    JSON,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base  # 프로젝트 공용 Base. 경로 다르면 나경님이 수정.


# ------------------------------------------------------------------
# 코드값 참고 (MySQL ENUM 대신 VARCHAR + 이 상수를 씁니다 - DB.pdf 1장 권장사항)
# ------------------------------------------------------------------

class ConditionOperator:
    EQ = "EQ"
    NE = "NE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    BETWEEN = "BETWEEN"
    CONTAINS = "CONTAINS"
    EXISTS = "EXISTS"
    MANUAL_CHECK = "MANUAL_CHECK"


class CheckMode:
    AUTO = "AUTO"       # 나이/지역처럼 rule_extractor.py가 숫자로 직접 매핑한 조건
    MANUAL = "MANUAL"   # 그 외 AI가 자유텍스트에서 추출한 조건 (사람/엔진의 추가 판단 필요)
    DOCUMENT = "DOCUMENT"


# condition_key 레지스트리 (rule_extractor.py의 AI_SYSTEM_PROMPT와 동일하게 유지해야 함)
class ConditionKey:
    AGE = "profile.age"
    REGION_CODE = "profile.region_code"
    INCOME_BAND_CODE = "profile.income_band_code"
    HOUSING_TYPE_CODE = "profile.housing_type_code"
    HOUSEHOLD_TYPE_CODE = "profile.household_type_code"
    HOUSEHOLD_SIZE = "profile.household_size"
    EMPLOYMENT_STATUS_CODE = "profile.employment_status_code"
    EMPLOYMENT_COMPANY_SIZE = "employment.company_size"
    EMPLOYMENT_CONTRACT_TYPE = "employment.contract_type"
    EMPLOYMENT_TENURE_MONTHS = "employment.tenure_months"
    EMPLOYMENT_INSURANCE_ENROLLED = "employment.insurance_enrolled"
    EMPLOYMENT_JOB_FIELD = "employment.job_field"


# ------------------------------------------------------------------
# 모델
# ------------------------------------------------------------------

class PolicyCondition(Base):
    __tablename__ = "policy_conditions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    policy_id = Column(BigInteger, ForeignKey("policies.id"), nullable=False, index=True)

    condition_key = Column(String(100), nullable=False)       # 예: "profile.age"
    operator = Column(String(30), nullable=False)              # ConditionOperator 값 중 하나
    expected_value_json = Column(JSON, nullable=True)          # 정책 기준값, 예: {"min":19,"max":34}

    condition_group_no = Column(SmallInteger, nullable=False, default=0)  # 같은 그룹=AND, 다른 그룹=OR
    is_required = Column(Boolean, nullable=False, default=True)
    check_mode = Column(String(20), nullable=False, default=CheckMode.MANUAL)  # AUTO/MANUAL/DOCUMENT

    description = Column(String(500), nullable=True)       # 화면 표시용 조건 설명
    failure_message = Column(String(500), nullable=True)   # 불충족 시 보여줄 문구

    sort_order = Column(SmallInteger, nullable=False, default=0)

    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)

    # policy = relationship("Policy", back_populates="conditions")  # Policy 모델 쪽 설정에 맞춰 조정

    def __repr__(self):
        return f"<PolicyCondition {self.condition_key} {self.operator} policy_id={self.policy_id}>"
