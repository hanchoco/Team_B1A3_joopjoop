# Simulator 계산 규칙 (`PolicyBenefit.calculation_rule_json`) 계약 문서

> **주의: 아래 6개 타입(`LOAN_INTEREST`, `SAVINGS_ASSET`, `CASH_VOUCHER`, `HOUSING_RENT`,
> `EMPLOYMENT_EDUCATION`, `TAX_DEDUCTION`)은 DB 필드가 아니다.**
> `PolicyBenefit` 모델에는 이 값을 저장하는 컬럼이 없다. 이 타입들은 나중에 Policy Engine
> 내부에서 `PolicyBenefit.benefit_type` + 정책의 `PolicyCategory`(카테고리) 조합으로
> **런타임에 도출**할 논리적 분류이며, 그 분류 결과에 따라 `calculation_rule_json`을
> 어떤 스키마로 해석할지 결정하는 용도로만 쓰인다. 즉 이 문서는 `calculation_rule_json`
> 컬럼(JSON, 프리폼) **안에 실제로 채워 넣을 값의 스키마 계약**을 정의한다.
>
> 이 문서는 `calculation_rule_json`에 실데이터를 입력하는 사람(팀원 또는 AI 추출 결과를
> 검토하는 담당자)이 참고하는 계약(contract) 문서이며, 코드에서 이 스키마를 강제하는
> 별도의 Pydantic 모델은 아직 없다(추후 Policy Engine 쪽에서 소비 로직을 만들 때 함께
> 검토 필요).

## 논리적 타입 도출 기준 (참고)

| 논리적 타입 | 관련 `benefit_type` | 관련 카테고리(예시) |
| --- | --- | --- |
| `LOAN_INTEREST` | `LOAN` | 금융 |
| `SAVINGS_ASSET` | `SAVINGS` | 금융 |
| `CASH_VOUCHER` | `CASH`, `DISCOUNT` | 복지, 고용 등 |
| `HOUSING_RENT` | `CASH`, `OTHER` | 주거 |
| `EMPLOYMENT_EDUCATION` | `CASH`, `SERVICE` | 고용 |
| `TAX_DEDUCTION` | `TAX_REDUCTION` | 세금 |

실제 도출 로직(우선순위, 예외 케이스 처리 등)은 Policy Engine 구현 시점에 확정한다.
이 표는 스키마를 채울 때 어떤 타입을 선택해야 할지 가늠하기 위한 참고용이다.

---

## 1. `LOAN_INTEREST` — 대출 이자 지원

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `policy_interest_rate_percent` | number | ✅ | 정책이 확정 적용하는 금리(%) |
| `interest_reduction_rate_percent` | number | optional | 일반 대출 대비 감면율(%) |
| `max_loan_amount` | number | ✅ | 최대 대출한도(원) |
| `max_support_months` | integer | ✅ | 최대 지원기간(개월) |
| `repayment_type` | string enum | ✅ | `EQUAL_PRINCIPAL_INTEREST`(원리금균등) / `EQUAL_PRINCIPAL`(원금균등) / `BULLET`(만기일시) 등 |

```json
{
  "type": "LOAN_INTEREST",
  "policy_interest_rate_percent": 1.8,
  "interest_reduction_rate_percent": 2.2,
  "max_loan_amount": 200000000,
  "max_support_months": 24,
  "repayment_type": "BULLET"
}
```

---

## 2. `SAVINGS_ASSET` — 자산형성/적금 지원

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `government_match_rate_percent` | number | ✅ | 정부 매칭 비율(%) |
| `monthly_max_support_amount` | number | ✅ | 월 최대 지원금(원) |
| `maturity_months` | integer | ✅ | 만기 기간(개월) |
| `base_interest_rate_percent` | number | ✅ | 기본금리(%) |
| `bonus_interest_rate_percent` | number | optional | 우대금리(%) |

```json
{
  "type": "SAVINGS_ASSET",
  "government_match_rate_percent": 100,
  "monthly_max_support_amount": 100000,
  "maturity_months": 36,
  "base_interest_rate_percent": 4.5,
  "bonus_interest_rate_percent": 1.0
}
```

---

## 3. `CASH_VOUCHER` — 현금/바우처 지급

`amount_type`(`FIXED` 또는 `PERCENTAGE`)으로 필드 구성이 분기된다.

- `benefit_type=CASH` → 일반적으로 `FIXED`로 매핑
- `benefit_type=DISCOUNT` → 일반적으로 `PERCENTAGE`로 매핑

### 3-1. `amount_type=FIXED`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `amount_type` | `"FIXED"` | ✅ | 분기 판별자 |
| `amount` | number | ✅ | 지급 금액(원) |
| `payment_cycle` | string | ✅ | `ONCE` / `MONTHLY` / `YEARLY` / `MATURITY` / `VARIABLE` |
| `max_count` | integer | ✅ | 최대 지급 횟수 |

```json
{
  "type": "CASH_VOUCHER",
  "amount_type": "FIXED",
  "amount": 300000,
  "payment_cycle": "ONCE",
  "max_count": 1
}
```

### 3-2. `amount_type=PERCENTAGE`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `amount_type` | `"PERCENTAGE"` | ✅ | 분기 판별자 |
| `rate_percent` | number | ✅ | 지원 비율(%) |
| `cap_amount` | number | ✅ | 지원 상한액(원) |
| `payment_cycle` | string | ✅ | `ONCE` / `MONTHLY` / `YEARLY` / `MATURITY` / `VARIABLE` |

```json
{
  "type": "CASH_VOUCHER",
  "amount_type": "PERCENTAGE",
  "rate_percent": 50,
  "cap_amount": 100000,
  "payment_cycle": "MONTHLY"
}
```

---

## 4. `HOUSING_RENT` — 주거/월세 지원

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `monthly_support_cap_amount` | number | ✅ | 월 지원 한도(원) |
| `support_months` | integer | ✅ | 지원 기간(개월) |
| `deposit_limit_amount` | number | optional | 보증금 제한(원) |
| `rent_limit_amount` | number | optional | 월세 제한(원) |

> 관리비(management fee)는 이 스키마의 지원 대상이 아닐 수 있다. 관리비 지원 여부는
> 정책마다 다르므로 이 필드들로 표현하지 않고, 필요 시 별도 필드(예: 프리텍스트 설명이나
> 향후 추가될 관리비 전용 필드)로 취급한다. `monthly_support_cap_amount`는 월세 지원
> 한도만을 의미한다.

```json
{
  "type": "HOUSING_RENT",
  "monthly_support_cap_amount": 200000,
  "support_months": 12,
  "deposit_limit_amount": 50000000,
  "rent_limit_amount": 600000
}
```

---

## 5. `EMPLOYMENT_EDUCATION` — 고용/교육 지원

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `training_allowance_amount` | number | optional | 훈련수당(원) |
| `education_subsidy_amount` | number | optional | 교육비 지원액(원) |
| `employment_success_bonus_amount` | number | optional | 취업성공수당(원) |
| `support_months` | integer | ✅ | 지원 기간(개월) |

```json
{
  "type": "EMPLOYMENT_EDUCATION",
  "training_allowance_amount": 300000,
  "education_subsidy_amount": 1000000,
  "employment_success_bonus_amount": 1500000,
  "support_months": 6
}
```

---

## 6. `TAX_DEDUCTION` — 세액/소득 공제

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `deduction_rate_percent` | number | ✅ | 공제율(%) |
| `max_deduction_amount` | number | optional | 공제한도(원) |
| `deduction_type` | string enum | ✅ | `TAX_CREDIT`(세액공제) / `INCOME_DEDUCTION`(소득공제) |

```json
{
  "type": "TAX_DEDUCTION",
  "deduction_rate_percent": 15,
  "max_deduction_amount": 3000000,
  "deduction_type": "TAX_CREDIT"
}
```

---

## 변경 이력 관리

이 문서는 `calculation_rule_json`을 소비하는 Policy Engine 로직이 실제로 구현되기 전
단계의 스키마 계약이다. 필드를 추가/변경할 때는 이 문서를 함께 갱신하고, 이미 저장된
기존 `calculation_rule_json` 데이터와의 마이그레이션 여부를 함께 검토한다.
