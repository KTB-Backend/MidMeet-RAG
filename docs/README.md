# Documentation — 인덱스 (목차)

이 파일은 프로젝트 지식의 **단일 목차**다. `CLAUDE.md`·`AGENTS.md`는 상세 내용을 복제하지 않고 이 인덱스를 가리킨다.

`product-specs/project-brief.md`가 프로젝트 범위·기술 결정·설계 원칙의 **진실의 원천(Source of Truth)**이다.
다른 문서가 이와 충돌하면 `project-brief.md`를 우선한다. 방향 변경은 반드시 `project-brief.md`에서 시작한다.

---

## 디렉터리 구조

```
docs/
├── product-specs/   # 제품 요구사항·기획 (진실의 원천)
├── design-docs/     # 기술 설계·아키텍처 결정
├── exec-plans/      # 실행 계획·작업 흐름
├── references/      # 정책·평가 등 참조 자료
└── prompts/         # LLM 프롬프트 템플릿
```

---

## 문서 목록

### product-specs/ — 제품 요구사항

| 파일 | 용도 |
|------|------|
| [`project-brief.md`](product-specs/project-brief.md) | ★ 진실의 원천 — MVP 범위·제외 범위·기술 스택·의사결정 |

### design-docs/ — 기술 설계

| 파일 | 용도 |
|------|------|
| [`architecture.md`](design-docs/architecture.md) | 전체 시스템 구조·모듈 경계·설정 주입표 |
| [`rag-design.md`](design-docs/rag-design.md) | RAG 파이프라인 설계·스코어링 수식·**구현 순서 정본** |
| [`data-design.md`](design-docs/data-design.md) | **시드 스키마 정본** — 필드 정의·작성 기준·샘플 JSON |
| [`api-design.md`](design-docs/api-design.md) | API 인터페이스 초안 (DRAFT, 프레임워크 TBD) |

### exec-plans/ — 실행 계획

| 파일 | 용도 |
|------|------|
| [`task-plan.md`](exec-plans/task-plan.md) | 마일스톤·작업 단위·담당 도구·완료 조건 |
| [`agent-workflow.md`](exec-plans/agent-workflow.md) | Codex CLI 작업 흐름·완료 체크리스트 |
| [`how-to-run-test.md`](exec-plans/how-to-run-test.md) | 로컬 venv 단계별 실행·테스트 런북(단계별 통과 기준 포함) |

### references/ — 정책·평가

| 파일 | 용도 |
|------|------|
| [`data-policy.md`](references/data-policy.md) | 허용 데이터 출처·크롤링 금지·산출물 관리 (스키마는 data-design 참조) |
| [`evaluation.md`](references/evaluation.md) | **평가 정본** — 평가 레이어·필수 쿼리·모델 비교·통과 기준 |

### prompts/ — 프롬프트 템플릿

| 파일 | 용도 |
|------|------|
| [`prompts/recommendation-system.md`](prompts/recommendation-system.md) | LLM 추천 생성용 시스템 프롬프트 |

---

## 담당 도구별 주요 참조 경로

**Claude Code** (설계·검토·검증):
`product-specs/project-brief.md` → `design-docs/architecture.md` → `design-docs/rag-design.md` → `references/evaluation.md`

**Codex CLI** (구현·테스트):
`exec-plans/agent-workflow.md` → `design-docs/rag-design.md` → `design-docs/data-design.md` → `design-docs/api-design.md`

---

## 문서 작성 원칙

- **한 사실 = 한 정본 문서.** 같은 내용을 두 곳에 복제하지 않는다. 다른 문서는 정본을 링크로 가리킨다. (stale 방지)
- 새 문서를 추가하면 이 인덱스에 항목을 등록한다.
- 방향 변경은 `product-specs/project-brief.md`를 먼저 수정하고 관련 문서에 반영한다.
- 미확정 사항은 `TBD`로 명시하고 임의로 확정하지 않는다.
