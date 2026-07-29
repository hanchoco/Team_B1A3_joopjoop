# AGENTS.md

Codex, Claude Code 등 모든 AI 코딩 에이전트가 공통으로 준수하는 지침 파일.
모듈/경로 기준으로 작성. 작업 전 반드시 숙지.

## 1. 프로젝트 개요

- 서비스명: joopjoop (줍줍)
- 목적: 청년 맞춤형 정책 추천, 예상 혜택 시뮬레이션, AI 정책 Q&A
- 스택: Frontend(React) + Backend(FastAPI) 모노레포, MySQL, Docker
- 컨테이너는 `frontend` / `backend` / `db` 3개로 각각 독립 실행 (frontend·backend는 원래부터 항상 별도 컨테이너, 각자 자기 Dockerfile 사용)
- AI 기능(Q&A, 자격조건 추출, 체크리스트 생성)만 별도 컨테이너로 분리하지 않고 backend 컨테이너 안에 모듈로 통합한다 (프론트/백엔드 분리와는 무관한 결정)
- 기획 문서 우선순위: 목업 이미지와 본문 텍스트가 불일치할 경우 **본문 텍스트가 항상 우선**

## 2. Git 규칙

- 작업 레포: `hanchoco/AI-Builder-Sprint` (포크 레포)에서만 커밋/이슈/PR 진행
- 원본 레포 `Apptive/AI-Builder-Sprint`에는 어떠한 직접 작업도 금지
- `main` 브랜치 직접 커밋 금지
- 브랜치명: `feat/<모듈명>` (예: `feat/policy-engine`, `feat/simulator-ui`)
- 작업 완료 후 PR 생성, `main` 머지는 PR을 통해서만 진행
- 커밋 메시지 컨벤션: `feat:`, `fix:`, `docs:`, `style:`

## 3. 프로젝트 구조

- `/frontend` : React 기반 SPA (Vite), 자체 `Dockerfile`로 독립 컨테이너 빌드
- `/backend` : FastAPI 기반 REST API (AI 기능 포함), 자체 `Dockerfile`로 독립 컨테이너 빌드
- 기능별 담당 경로:
  - Core API(회원/마이페이지): `backend/app/api/v1/users.py`, `backend/app/crud/`
  - Policy Engine(매칭/시뮬레이션): `backend/app/services/policy_engine/`
  - AI(Q&A/자격조건 추출/체크리스트 생성): `backend/app/services/ai/`
  - 알림/스케줄링: `backend/app/services/notification/`
    - `scheduler.py` : 관심 정책 마감일 주기 체크, D-7/D-3/D-day 트리거
    - `sender.py` : 이메일/푸시 발송
  - 외부 API 연동(온통청년): `backend/app/integrations/youth_policy_api.py`
  - DB 모델: `backend/app/models/`
    - `user.py` : 회원 기본 정보(출생연도/거주지역/소득구간/취업상태/가구형태/주거형태)
    - `user_category_profile.py` : 카테고리별 추가 질문 응답(온보딩 단계, 카테고리마다 항목이 달라 유연한 구조 사용)
    - `policy.py` : 정책 원본 데이터(온통청년 수집분 포함)
    - `policy_condition.py` : AI(`rule_extractor.py`)가 정책 원문에서 추출한 자격조건(구조화된 형태로 저장, matcher.py가 소비)
    - `policy_document.py` : 정책별 필요 서류(AI `checklist_generator.py`가 생성)
    - `user_policy.py` : 사용자-정책 관계, 상태값 `관심`/`준비중`/`신청완료` + 준비중일 때 체크리스트 진행률(%)
    - `user_document_progress.py` : 사용자별 서류 준비 상태
    - `notification_setting.py` : 사용자별 알림 on/off(이메일/푸시 분리)
  - 스키마: `backend/app/schemas/`

## 4. 정책 판정 체계

화면 흐름: 카테고리 선택 → 맞춤 정책 추천 목록(카드 레벨 판정) → 카드 클릭 → 정책 상세(조건 레벨 판정)

판정은 **레벨이 다른 두 종류**이며 절대 혼용하지 않는다.

- **조건 레벨** (정책 상세, 개별 자격조건 단위): `충족` / `추가 확인 필요` / `불충족` — 3단계
  - 조건 값은 `models/policy_condition.py`에서 읽어옴(AI가 정책 등록 시점에 미리 추출해둔 결과, 실시간 추출 아님)
  - `services/policy_engine/matcher.py`의 `evaluate_condition()`에서 조건 1개씩 판정
- **카드 레벨** (정책 카드 배지, 목록/대시보드/마이페이지 요약): `가능성 높음` / `추가 확인 필요` — 2단계
  - `matcher.py`의 `evaluate_policy()`에서 조건 레벨 결과를 집계해 산출
  - 모든 조건이 `충족`이면 → `가능성 높음`, 하나라도 아니면(=`추가 확인 필요`/`불충족` 포함) → `추가 확인 필요`
- `schemas/policy.py`에 `ConditionStatus`(3단계)와 `PolicyCardStatus`(2단계) 타입을 분리 정의, 하나의 enum으로 합치지 않는다

## 5. 시뮬레이터 규칙

- 시뮬레이터 입력 필드는 카테고리(주거/교통/금융/세금/고용/복지)마다 다르게 설계한다 (공통 필드로 통일하지 않음)
- 금액 등 구체적인 입력값은 DB/프로필에 저장하지 않고, 사용자가 시뮬레이터를 열 때마다 매번 직접 입력한다
- Frontend: `frontend/src/components/simulator/`에 카테고리별 폼 컴포넌트 분리
  - `HousingSimulatorForm.tsx`(월세/관리비/보증금 등), `TransportSimulatorForm.tsx`, `FinanceSimulatorForm.tsx`, `TaxSimulatorForm.tsx`, `EmploymentSimulatorForm.tsx`, `WelfareSimulatorForm.tsx`
- Backend: `services/policy_engine/simulator.py`에 카테고리별 계산 함수 분리 (`calculate_housing()`, `calculate_transport()` 등), 공통 함수 하나로 억지로 합치지 않는다
- 한 카테고리 안에서도 정책별로 계산 로직이 크게 다르면(예: 월세지원 vs 대출이자지원) 함수를 정책 단위로 더 세분화할 수 있다 — 발견 시 팀 논의 후 결정

## 6. 코딩 컨벤션

### Frontend (`/frontend`)
- 컴포넌트: PascalCase, 파일명은 컴포넌트명과 동일하게 작성
- 페이지 단위: `src/pages/<기능명>/` 폴더로 분리
  - `Login`, `Signup`, `Onboarding`, `Dashboard`, `CategorySelect`, `PolicyList`, `PolicyDetail`, `Simulator`, `Checklist`, `Chatbot`, `MyPage`, `MyPolicies`, `Settings`
- API 호출은 반드시 `src/api/*.ts`에서만 수행, 컴포넌트 내부에서 직접 fetch/axios 호출 금지
- 전역 상태: `src/store/`, 컴포넌트 로컬 상태: `useState`/`useReducer`
- 타입 정의는 `src/types/`에 작성, `any` 타입 사용 금지

### Backend (`/backend`)
- 라우터(`app/api/v1/*.py`)는 요청/응답 처리만 담당, 비즈니스 로직은 `services/`에 위임
- 정책 자격 매칭 로직은 `services/policy_engine/matcher.py`에서만 구현
- 혜택 합산 시뮬레이션 로직은 `services/policy_engine/simulator.py`에서만 구현
- ORM 모델(`models/`)과 Pydantic 스키마(`schemas/`)는 반드시 분리 유지
- 함수/변수는 snake_case, 클래스는 PascalCase, 모든 함수는 타입힌트 필수
- **DB 접근은 `crud/` 계층을 통해서만 수행**, 라우터/서비스/AI 모듈에서 직접 쿼리 금지 (AI가 데이터를 잘못 건드리는 사고를 막기 위한 필수 규칙)

## 7. AI 연동 규칙

- Upstage Solar LLM Q&A는 `backend/app/services/ai/solar_client.py`에서만 구현
- 정책 자격조건 자동 추출은 `backend/app/services/ai/rule_extractor.py`에서만 구현, 결과는 `models/policy_condition.py`에 저장
- 체크리스트(필요 서류) 자동 생성은 `backend/app/services/ai/checklist_generator.py`에서만 구현, 결과는 `models/policy_document.py`에 저장
- **AI가 생성/추출한 결과는 DB에 바로 반영하지 않고, 검토용 임시 테이블/파일에 먼저 저장한 뒤 담당자 확인 후 확정 반영한다** (AI 오작동으로 인한 데이터 오염 방지)
- 프롬프트 템플릿은 `backend/app/services/ai/prompt_templates.py`에 분리 관리, 하드코딩 금지
- API 키, 시크릿 등 민감정보는 `.env`로만 관리, 코드/커밋에 절대 포함 금지
- AI Q&A는 현재 조회 중인 정책의 조건/내용만 컨텍스트로 사용, 대화 기록은 DB에 저장하지 않음
- 온통청년 API 응답 데이터는 `backend/app/integrations/youth_policy_api.py`를 거쳐서만 수집
- 정책 데이터 초기 적재(수집 → 자격조건 추출 → 체크리스트 생성 → DB 저장)는 `backend/scripts/seed_policy_data.py` 하나로 통일, 컨테이너 분리 없이 backend 컨테이너 안에서 배치 스크립트로 실행(`docker compose exec backend python scripts/seed_policy_data.py`)

## 8. 알림 규칙

- 알림 대상: 사용자가 관심 정책으로 저장(스크랩)한 정책만
- 발송 시점: 마감 7일 전 / 3일 전 / 마감 당일 (3회 고정, 임의 변경 금지)
- 채널: 이메일/푸시 개별 on-off 가능, 전체 토글도 지원
- 스케줄링/발송 로직은 `backend/app/services/notification/`에서만 구현

## 9. 공통 작업 원칙

- 담당 모듈 경로 외 임의 리팩터링 금지, 변경 범위는 관련 모듈로 한정
- 새 패키지 추가 시 `requirements.txt`(backend) / `package.json`(frontend) 즉시 갱신
- 커밋 전 lint/format 실행: frontend(`eslint`, `prettier`), backend(`ruff`, `black`)
- 정책 매칭/시뮬레이션 로직 변경 시 테스트 코드 없이 커밋 금지
