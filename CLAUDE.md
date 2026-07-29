# CLAUDE.md

@AGENTS.md

Claude Code(claude.ai/code)가 이 레포에서 작업할 때 위 AGENTS.md 공통 지침을 우선 로드한다.
아래는 Claude Code에만 적용되는 추가 지침이다.

## 실행 명령어

- 프론트엔드 개발 서버: `cd frontend && npm run dev`
- 백엔드 개발 서버: `cd backend && uvicorn app.main:app --reload`
- 전체 스택(Docker, backend+frontend+db 컨테이너 3개): `docker-compose up --build`
- 정책 데이터 초기 적재(수집→AI 자격조건 추출→AI 체크리스트 생성→DB 저장): `docker compose exec backend python scripts/seed_policy_data.py`
- 백엔드 테스트: `cd backend && pytest`
- 프론트엔드 린트: `cd frontend && npm run lint`
- 백엔드 린트: `cd backend && ruff check .`
- 백엔드 포맷: `cd backend && black .`
- DB 마이그레이션 생성: `cd backend && alembic revision --autogenerate -m "<설명>"`
- DB 마이그레이션 적용: `cd backend && alembic upgrade head`

## 작업 모드 원칙

- 여러 파일에 걸친 변경이나 구조 변경은 Plan Mode로 변경 범위를 먼저 제시하고 승인받은 후 진행
- `backend/app/services/policy_engine/`(정책 매칭·시뮬레이션), `backend/app/services/ai/`(AI 자동 추출/생성 결과가 DB에 바로 반영되지 않는지 확인), `alembic/`(DB 마이그레이션) 변경은 실행 전 반드시 사용자 확인
- 3개 이상 파일에 걸친 작업은 TodoWrite로 작업 목록화 후 순차 진행
- 브랜치 생성, 커밋, PR 생성은 AGENTS.md의 Git 규칙을 그대로 따름
- PR 생성 전 관련 테스트를 실행하고 결과를 PR 설명에 포함

## 모듈별 컨텍스트 우선순위

- 정책 매칭/시뮬레이션 작업: `backend/app/services/policy_engine/` 기존 코드부터 확인
- 정책 판정 로직 작업 시 AGENTS.md 4번 섹션(정책 판정 체계)부터 확인 — 조건 레벨과 정책 레벨 둘 다 3단계이지만 값 체계가 다름(조건 레벨: 충족/추가 확인 필요/불충족, 정책 레벨: ELIGIBLE/NEEDS_REVIEW/INELIGIBLE), 서로 섞어 쓰지 않도록 주의
- 시뮬레이터 작업 시 AGENTS.md 5번 섹션(시뮬레이터 규칙) 확인 — 카테고리별로 폼/계산 함수가 분리되어 있어야 함, 입력값은 저장하지 않고 매 요청 처리
- AI Q&A/자격조건 추출/체크리스트 생성 작업: `backend/app/services/ai/` 기존 패턴부터 확인, DB 직접 반영 금지 규칙(AGENTS.md 7번) 준수
- 알림/스케줄링 작업: `backend/app/services/notification/` 기존 코드부터 확인, 발송 시점(D-7/D-3/D-day)은 고정값 준수
- 프론트 UI 작업: `frontend/src/components/` 내 기존 공통 컴포넌트 재사용 가능 여부 먼저 확인
- 외부 API(온통청년) 관련 작업: `backend/app/integrations/youth_policy_api.py` 응답 구조부터 확인

## 금지 사항

- `.env` 파일 내용을 커밋하거나 출력하지 않음
- 원본 레포(`Apptive/AI-Builder-Sprint`)에 대한 어떠한 git 작업도 수행하지 않음
- `main` 브랜치에 직접 커밋하지 않음
- AI 모듈(`services/ai/`)에서 `crud/` 계층을 거치지 않고 DB에 직접 쓰지 않음
