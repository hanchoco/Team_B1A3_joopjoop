# ☑️ joopjoop: AI 기반 맞춤형 정책 체크리스트 플랫폼

**"AI가 기계적인 서류 작업을 돕고, 청년은 본연의 삶(인간다움)에 집중하도록"**

joopjoop은 청년들이 자신에게 맞는 정부 혜택을 찾고 신청하는 과정의 피로도를 획기적으로 줄여주는 서비스입니다. 수많은 공공서비스와 복잡한 행정 용어, 방대한 요구 서류 앞에서는 누구나 막막함을 느낍니다.

저희는 AI를 활용해 이러한 소모적인 서류 해석 작업을 대신 수행하고, 누구나 쉽게 따라 할 수 있는 맞춤형 체크리스트로 변환합니다. 사용자가 행정의 장벽에 좌절하지 않고 자신의 삶과 미래를 설계하는 인간다운 시간에 온전히 집중할 수 있도록 돕는 것이 이 프로젝트의 핵심입니다.

---

## 배포 및 테스트 가이드

- 배포 URL: https://joopjoop.up.railway.app/
- **시연 추천 흐름**: `회원가입 ➡️ 로그인 ➡️ 메인 대시보드 혜택 요약 확인 ➡️ 맞춤 정책 탐색 ➡️ 예상 시뮬레이션 확인 ➡️ 체크리스트 생성 및 원스톱 발급 링크 클릭 ➡️ AI에게 물어보기(Q&A) 질문`

- *AI 코딩 에이전트 지침 파일* <br>
개발 과정에서 사용한 AI 에이전트 공통 지침은 `AGENTS.md`(전 에이전트 공통), Claude Code 전용 추가 지침은 `CLAUDE.md`에서 확인할 수 있습니다.
---

## 핵심 가치: AI가 만들어주는 맞춤형 '신청 준비 체크리스트'

joopjoop의 모든 기능은 사용자가 성공적으로 정책을 신청할 수 있도록 돕는 **'가입 준비하기(체크리스트)'** 화면으로 귀결됩니다. 체크리스트에서는 비정형 텍스트로 된 공고문에서 AI가 자격 조건과 필요 서류를 정확하게 추출하여 제공합니다.

- * **✓ 자격 조건 및 서류 맞춤 안내**: 충족된 조건은 완료로, 추가 확인이 필요한 조건은 사용자가 직접 체크할 수 있도록 분리하여 제공합니다.
- * **✓ 원스톱 발급 링크**: 주민등록등본, 건강보험 자격득실확인서 등 서류별로 필요한 발급처(정부24, 국민건강보험공단 등) 바로가기를 제공하여 번거로운 검색 과정을 없앴습니다.
- * **✓ 진행 상태 저장 (이어하기)**: 체크리스트의 진행률 바(Progress Bar)와 상태가 실시간으로 저장되며, 마이페이지의 '준비 중' 탭에서 언제든 이어서 진행할 수 있습니다.
<img width="958" height="1136" alt="Image" src="https://github.com/user-attachments/assets/c836b10c-d289-441c-b7d4-8f4dad91cfa0" />

---

## 주요 기능 및 사용자 흐름

체크리스트를 중심으로, 이를 탐색하고 지원하는 핵심 기능들입니다.

### 1. 홈 대시보드 및 마이페이지 (관리)

- **놓치기 직전 정책 & 혜택 요약**: 대시보드에서 마감이 임박한 정책과 내가 받을 수 있는 총 혜택 금액을 한눈에 확인합니다.
- **내 정책 관리**: 관심(스크랩), 준비 중(체크리스트 진행 중), 신청 완료 3가지 상태를 탭으로 쉽게 전환하며 정책 신청 현황을 관리합니다. 마감일 기준 7일, 3일, 당일 알림 기능도 지원합니다.
<img width="1467" height="1176" alt="Image" src="https://github.com/user-attachments/assets/e34e7a07-cf77-4b7f-811d-5845d523783d" /> <br> <br>

### 2. 정책 판정 및 맞춤 추천 (탐색)

- **기본/추가 정보 입력**: 가입 시 입력한 기본 정보(출생연도, 거주지역, 소득 등)와 카테고리별 추가 질문을 통해 사용자의 상태를 파악합니다.
- **지역 청년 정보 격차 해소**: 구·군 단위로 세분화된 지자체 정책까지 필터링해 정보력 차이로 인한 혜택 격차를 줄입니다.
<img width="1372" height="1354" alt="Image" src="https://github.com/user-attachments/assets/aaa5d7a2-6b37-47b5-85fb-aaccc277b01b" /> <br> <br>

### 3. 정책 상세 및 시뮬레이션 (결정)

- **예상 시뮬레이션**: 정책을 신청하여 혜택을 받았을 때의 월/연 기준 소득, 지출, 잔여 금액 변화를 비교해 구체적인 경제적 절감 효과를 시각적으로 보여줍니다.
- **AI에게 물어보기 (Q&A)**: 체크리스트를 진행하다 궁금한 점이 생기면 언제든 질문할 수 있습니다. Solar LLM이 현재 보고 있는 정책 조건만 컨텍스트로 삼아 정확하고 친절하게 답변합니다.
<img width="2281" height="1386" alt="Image" src="https://github.com/user-attachments/assets/b5a124e9-a797-40b9-b84d-c6678ad1bad0" /><br><br>
---

## 백엔드 및 AI 아키텍처 특징

- **정책 초기 적재 파이프라인**: 온통청년 API 연동(`integrations/youth_policy_api.py`)부터 AI 자격조건 추출, AI 체크리스트 생성, DB 저장까지 `scripts/seed_policy_data.py` 단일 파이프라인으로 통합하여 수행합니다.
  
- **안전한 데이터 관리**: AI가 추출 및 생성한 결과는 즉시 DB에 반영되지 않고 검토용 임시 저장소에 적재됩니다. 이후 담당자 확인을 거쳐 확정 반영되므로 오작동에 의한 데이터 오염을 방지합니다.
  
- **DB 접근 통제**: 데이터베이스 접근은 반드시 `crud/` 계층을 통해서만 수행되며 라우터나 서비스, AI 모듈에서의 직접 쿼리를 엄격히 금지합니다.
  
- **역할 분담**: 정확성이 필요한 조건 계산과 시뮬레이션은 룰 엔진(`services/policy_engine/matcher.py`, `simulator.py`)이 담당하고, 정책에 대한 자연스러운 설명과 따뜻한 대화는 AI(Solar LLM)가 맡아 기계적인 정확성과 인간적인 사용성을 모두 확보했습니다.

---

## 🖇️기술 스택

| 분류 | 기술 스택 | 세부 역할 |
| --- | --- | --- |
| **Frontend** | React (Vite) | 독립 컨테이너 구성 |
| **Backend** | FastAPI | AI 연동, 룰 엔진 및 시뮬레이터 포함 (독립 컨테이너) |
| **Database** | MySQL | 사용자 및 정책 데이터 저장 (독립 컨테이너) |
| **AI** | Upstage Solar LLM | 자격조건/필요서류 체크리스트 자동 생성, Q&A 챗봇 |
| **Infra** | Docker Compose | FE / BE / DB 3계층 아키텍처 환경 구축 |

---
## Upstage API 활용

joopjoop은 **Upstage Solar Pro**를 서비스의 핵심 두 축(① 정책 데이터 자동 구조화, ② 정책 Q&A 챗봇)에 실사용하고 있습니다.

| 활용 위치 | 코드 파일 경로 | 역할 및 비고 |
| --- | --- | --- |
| **정책 자격조건 추출** | `backend/app/services/ai/rule_extractor.py` | 비정형 공고문 ➡️ 구조화된 자격조건(`condition`) JSON |
| **필요서류 추출** | `backend/app/services/ai/checklist_generator.py` | 제출서류 목록 및 발급처 바로가기 안내 생성 |
| **지원혜택 추출** | `backend/app/services/ai/benefit_extractor.py` | 지원 금액·방식 구조화 |
| **카테고리 자동 분류** | `backend/app/services/ai/category_classifier.py` | 8대 핵심 카테고리 자동 분류 |
| **시뮬레이터 규칙 추출** | `backend/app/services/ai/calc_rule_extractor.py` | 혜택 유형별(6종) 계산 파라미터 추출 |
| **정책 Q&A 챗봇** | `backend/app/services/chatbot_service.py` | 현재 조회 중인 정책 컨텍스트 기반 1:1 Q&A |
| **프롬프트 관리** | `backend/app/services/ai/prompt_templates.py` | 6개 기능 시스템 프롬프트 중앙 관리 |
| **API 클라이언트** | `backend/app/services/ai/solar_client.py` | Upstage Solar 비동기 연동 (`solar-pro3`) |

> 💡 수동 실행 파이프라인(`seed_policy_data.py`)을 통해 온통청년 API 원문을 위 5개 추출 모듈에 순차 통과시키며, 결과는 검토용 초안(`review_drafts/`) 저장 후 담당자 승인을 거쳐 DB에 안전하게 반영됩니다.
> 
---

## 팀 소개 - B1A3

- **주효은**(정보컴퓨터공학과 컴퓨터공학전공) **- Frontend** <br>
React, 전체 화면, UX, API 연동

- **이유민**(정보컴퓨터공학과 컴퓨터공학전공) **- Backend & Integration** <br>
FastAPI, MySQL, DB 

- **김나경**(정보컴퓨터공학과 컴퓨터공학전공) **- Policy Engine** <br>
Matching Engine, 자격조건 판정, Benefit Calculator

- **한다빈**(정보컴퓨터공학과 컴퓨터공학전공) **- AI** <br>
온통청년 API, Solar LLM, 정책 Q&A, Docker, 배포 및 통합
