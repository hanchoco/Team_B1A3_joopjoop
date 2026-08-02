> **joopjoop (줍줍)** — AI 기반 맞춤형 청년 정책 체크리스트 플랫폼
> 

---

## 1. AI 활용 핵심 설계 철학

본 프로젝트는 개발 프로세스 전반(Dev-side)과 서비스 내부 로직(Service-side) 모두에서 AI를 활용하되, 팀 공통 지침(`AGENTS.md`)을 수립하여 아래 두 가지 원칙을 엄격히 준수했습니다.

1. **수치 정밀성과 자연어 처리의 역할 분리**:
    - 수치적 정밀도가 필요한 조건 판정 및 혜택 금액 계산은 **Rule Engine**이 전담합니다.
    - 비정형 공고문 해석, 카테고리 분류, 정책 설명 및 Q&A는 **Upstage Solar LLM**이 전담합니다.
2. **Human-in-the-Loop (검토 단계 필수화)**:
    - AI가 추출한 결과는 DB에 직접 반영되지 않고, 검토용 초안(`review_drafts/`) 파일로 먼저 저장됩니다.
    - 사람이 검토 및 승인(`-approve`) 명령을 내린 데이터만 DB에 확정 적재됩니다.

---

## 2. 개발 프로세스 전반의 AI 활용 (Dev-side AI)

### 2-1. 역할 분담 및 활용 도구

| 담당 영역 | 활용 AI 도구 | 핵심 역할 |
| --- | --- | --- |
| **Frontend** | Codex | React (Vite) UI 컴포넌트 설계, 상태 관리 및 API 연동 |
| **Backend Core** | Codex | RESTful API, Auth, 사용자/알림 CRUD 및 DB 계층 구축 |
| **Policy Engine** | Claude Code | 조건 평가 Matcher 및 CalcType 6종 시뮬레이터 개발 |
| **AI / Infra** | Claude Code | Upstage Solar LLM 파이프라인 구축, Docker 및 배포 |

### 2-2. 에이전트 통제 및 지침 체계 (`AGENTS.md` / `CLAUDE.md`)

여러 AI 코딩 에이전트 사용 시 발생할 수 있는 코드 컨벤션 파괴 및 아키텍처 파퓰레이션을 방지하기 위해 지침 파일 체계를 운용했습니다.

- **`AGENTS.md` (전 에이전트 공통 지침)**:
    - 계층 구조 통제 (`crud/` 계층 외 direct DB Query 엄격 금지)
    - 판정 체계의 명확한 분리 (조건 레벨 `SATISFIED/UNSATISFIED` vs 카드 레벨 `ELIGIBLE/NEEDS_REVIEW/INELIGIBLE`)
    - AI 추출 모듈의 DB 직접 접근 금지 및 검토 파일 적재 의무화
- **`CLAUDE.md` (Claude Code 전용 지침)**:
    - 다중 파일 수정 전 `Plan Mode` 사전 승인 절차 강제
    - Claude Code가 담당하는 핵심 도메인(`services/policy_engine/`, `services/ai/`) 변경 시 사전 검토 필수

---

## 3. 서비스 내 AI 모델 연동 명세 (Service-side AI)

- **사용 모델**: **Upstage Solar Pro** (`solar-pro2` / `solar-pro3`)
- **연동 모듈**: 비동기 통신 클라이언트 (`app/services/ai/solar_client.py`)

### 3-1. 정책 데이터 적재 파이프라인 (`scripts/seed_policy_data.py`)

온통청년 API 수집 ➡️ AI 5종 구조화 추출 ➡️ 검토 초안 저장(`review_drafts/`) ➡️ 사람 승인 ➡️ DB 반영

| 추출 모듈 경로 | 역할 | 사용 프롬프트 (`app/services/ai/prompt_templates.py`) |
| --- | --- | --- |
| `app/services/ai/rule_extractor.py` | 자격 조건(Condition) 구조화 추출 | `CONDITION_SYSTEM_PROMPT` |
| `app/services/ai/checklist_generator.py` | 필요 제출 서류 추출 | `DOCUMENT_SYSTEM_PROMPT` |
| `app/services/ai/benefit_extractor.py` | 지원 혜택 및 금액 구조화 추출 | `BENEFIT_SYSTEM_PROMPT` |
| `app/services/ai/category_classifier.py` | 8대 핵심 정책 카테고리 자동 분류 | `CATEGORY_SYSTEM_PROMPT` |
| `app/services/ai/calc_rule_extractor.py` | 시뮬레이터 파라미터 추출 | `CALC_RULE_*_PROMPT` (6종) |

### 3-2. 정책 상세 Q&A 챗봇 (`app/services/chatbot_service.py`)

- **Stateless 프롬프트**: 대화 이력을 Persist하지 않고, 현재 조회 중인 단일 정책의 원문과 조건 정의만 Context로 주입하여 환각을 최소화했습니다.

---

## 4. 환각(Hallucination) 방지 및 품질 안전장치

AI 추출 데이터의 신뢰성을 확보하기 위해 코드 레벨의 6가지 검증 안전장치를 구축하고 회귀 테스트로 고정했습니다.

1. **결정론적 데이터 보호**: 나이/지역 조건은 AI 추출 대신 코드의 하드코딩 매핑만 허용하며, AI가 임의 생성한 키는 자동 폐기합니다. (`AI_FORBIDDEN_CONDITION_KEYS`)
2. **원문 근거 검증 (Grounding Check)**: AI가 추출한 예외조항(`exception_note`)은 원문 텍스트 존재 여부를 문자열 대조하여 일치하지 않을 경우 폐기합니다.
3. **주제 키워드 대조**: 근거 문장과 조건 키 간의 주제 연관성(`TOPIC_KEYWORDS`)을 교차 검증합니다.
4. **무제한 조건 방지**: AI가 코드값 대부분을 나열하여 사실상 제한 없는 조건을 만들 경우 자동 폐기합니다. (`ENUM_COVERAGE_DROP_THRESHOLD`)
5. **다중 혜택 수치 분리**: 복수 혜택이 포함된 공고문 처리 시, 대상 혜택 외 나머지 혜택 목록을 명시적 제외 힌트로 전달하여 금액 뒤섞임을 방지합니다.
6. **시뮬레이터 완전성 검증**: CalcType별 필수 계산 파라미터 미달 시 해당 추출 결과를 폐기하여 0원 계산 오류를 차단합니다. (`is_calculation_rule_complete`)

---

## 5. AI 활용 증빙 및 검증 산출물 (Evidence)

- **검토 초안 산출물 (`review_drafts/*.json`)**:
    - AI가 추출하고 담당자가 검토/승인한 타임스탬프(`approved_at`)가 포함된 실제 데이터 배치 파일 포함
- **회귀 테스트 코드**:
    - `app/tests/test_seed_pipeline.py`: AI 환각 방지 검증 및 파이프라인 테스트
    - `app/tests/test_calc_rule_extractor.py`: `CalcType`별 시뮬레이터 파라미터 추출 완전성 테스트
    - `app/tests/test_chatbot_notifications_system.py`: Q&A 챗봇 Context 격리 및 Upstage API 오류 핸들링(503) 테스트