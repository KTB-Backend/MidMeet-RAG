# Documentation

`project-brief.md`가 프로젝트 범위·기술 결정·설계 원칙의 진실의 원천(Source of Truth)이다.
다른 문서가 `project-brief.md`와 충돌하면 `project-brief.md`를 우선한다.
방향 변경은 반드시 `project-brief.md`에서 시작한다.

---

## 문서 목록

### 기획 및 설계

| 파일 | 용도 |
|------|------|
| [`project-brief.md`](project-brief.md) | 기획서 — MVP 범위·제외 범위·기술 스택·의사결정 |
| [`architecture.md`](architecture.md) | 전체 시스템 구조·모듈 경계·컴포넌트 역할 |
| [`rag-design.md`](rag-design.md) | RAG 파이프라인 설계·스코어링 수식·추상화 구조 |
| [`data-design.md`](data-design.md) | 시드 데이터 스키마·작성 기준·샘플 JSON |
| [`api-design.md`](api-design.md) | API 인터페이스 초안 (DRAFT, 프레임워크 TBD) |

### 정책 및 평가

| 파일 | 용도 |
|------|------|
| [`data-policy.md`](data-policy.md) | 허용 데이터 출처·크롤링 금지·시드 작성 규칙 |
| [`rag-evaluation.md`](rag-evaluation.md) | 평가 레이어·필수 테스트 쿼리·통과 기준 |
| [`evaluation.md`](evaluation.md) | 평가 방법론·임베딩 모델 비교·LLM 비교·수동 체크리스트 |

### 작업 관리

| 파일 | 용도 |
|------|------|
| [`task-plan.md`](task-plan.md) | 마일스톤·작업 단위·담당 도구·완료 조건 |
| [`agent-workflow.md`](agent-workflow.md) | Codex CLI 작업 흐름·구현 순서·완료 체크리스트 |

### 프롬프트 템플릿

| 파일 | 용도 |
|------|------|
| [`prompts/recommendation-system.md`](prompts/recommendation-system.md) | LLM 추천 생성용 시스템 프롬프트 |

---

## 담당 도구별 주요 참조 문서

**Claude Code** (설계·검토·검증):
`project-brief.md` → `architecture.md` → `rag-design.md` → `evaluation.md`

**Codex CLI** (구현·테스트):
`agent-workflow.md` → `rag-design.md` → `data-design.md` → `api-design.md`

---

## 문서 작성 원칙

- 새 문서를 추가할 때 이 파일(README.md)의 목록에 항목을 추가한다.
- 방향 변경은 `project-brief.md`를 먼저 수정하고, 관련 문서에 반영한다.
- 미확정 사항은 `TBD`로 명시하고 임의로 확정하지 않는다.
