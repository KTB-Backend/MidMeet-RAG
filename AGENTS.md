# AGENTS.md — Codex CLI 구현 지침 (목차)

이 파일은 Codex CLI의 **운영 매뉴얼이자 목차**다. 상세 지식은 복제하지 않고 `docs/`를 가리킨다.
설계·아키텍처 결정은 Claude Code(`CLAUDE.md`)가 담당한다. 판단이 필요하면 **에스컬레이션 기준**대로 멈추고 보고한다.

- 문서 인덱스 → [`docs/README.md`](docs/README.md)
- 진실의 원천 → [`docs/product-specs/project-brief.md`](docs/product-specs/project-brief.md)

---

## 프로젝트 한 줄 요약

**"어디서 만날래?"** — 여러 출발지의 중간지점 근처 식당·카페를 **분위기와 거리** 기준으로 추천하는 RAG 서비스. 웹앱 완성이 아니라 **파이프라인 학습·튜닝**이 주목적이다.

---

## Codex의 역할

**구현 전담**: Python 구현·리팩토링, RAG 파이프라인(임베딩·검색·스코어링·생성), 카카오 로컬 API 연동, 시드 로딩·검증, pytest 작성. 문서-코드 불일치 발견 시 보고한다.

---

## 기술 스택 (요약)

- **확정**: Python 3.11 / 카카오 로컬 API / 임베딩 `dragonkue/snowflake-arctic-embed-l-v2.0-ko` / Chroma / 생성 `Qwen/Qwen3-4B-Instruct-2507` / 카카오맵.
- **TBD (임의 결정 금지)**: 백엔드 프레임워크 · 프론트엔드 · 배포.
- 상세·설정 주입표 → `docs/design-docs/architecture.md` §12, `docs/product-specs/project-brief.md` §6.

---

## 코드 지도

- 모듈 경계·디렉터리 구조·의존 규칙 → `docs/design-docs/architecture.md` §3.
- 핵심 규칙: 의존 방향은 항상 바깥(`apps/` `scripts/` `tests/`) → `packages/rag_core/`. `rag_core`는 API·UI에 의존하지 않는다.

---

## 파이프라인 구현 순서

- 정본 → `docs/design-docs/rag-design.md` §7. 이전 단계가 안정되기 전 다음 단계로 넘어가지 않는다.
- 작업 흐름 세부 → `docs/exec-plans/agent-workflow.md`.

---

## 구현 규칙 (반드시 준수)

**기본**
- 작은 단위로 변경한다. 관련 없는 파일을 수정하지 않는다.
- `project-brief.md`와 충돌하는 구현은 하지 않는다. 미확정 기술은 `TBD`/`TODO`로 남긴다.

**RAG**
- 임베딩·생성 LLM은 교체 가능한 추상화 계층을 경유한다. 모델명을 비즈니스 로직에 하드코딩하지 않는다.
- LLM은 검색된 시드 정보 안에서만 답하도록 프롬프트를 제약한다.
- 거리·분위기 점수는 0–1로 정규화한 뒤 가중합한다. 가중치는 설정/상수로 분리한다.
- 모델명·Chroma 경로·API 키·top_k·거리 반경은 환경변수/설정으로 주입한다. (표 → `architecture.md` §12)

**데이터**
- 크롤링 금지. 장소·좌표는 카카오 로컬 API만 사용한다. 정책 → `docs/references/data-policy.md`.
- LLM이 생성한 분위기를 factual 시드로 저장하지 않는다. 시드 스키마 정본 → `docs/design-docs/data-design.md`.
- 근거 없는 주장을 생성 결과에 포함하지 않는다.

**보안**
- `.env`·Chroma 인덱스·모델 가중치·캐시·임시 산출물을 커밋하지 않는다. API 키를 코드에 직접 쓰지 않는다.

---

## 문서 갱신 의무

변경 시 해당 **정본** 문서를 코드와 함께 갱신한다. (한 사실 = 한 정본)

| 변경 대상 | 정본 문서 |
|-----------|-----------|
| 파이프라인 구조·모듈 경계 | `docs/design-docs/architecture.md` |
| 시드 스키마 | `docs/design-docs/data-design.md` |
| 데이터 정책 | `docs/references/data-policy.md` |
| API 계약 | `docs/design-docs/api-design.md` |

---

## 완료 조건

- 관련 pytest 통과(`python -m pytest`). 실행 방법 문서화.
- 변경 파일·이유 요약. `project-brief.md` 충돌 없음. 미확정은 `TBD`.
- 검색 결과에 semantic·distance·final score 포함. 생성 결과에 근거 시드 ID 연결.
- 로컬 모델 실행 곤란 시 대체 경로·추상화 지점 문서화.
- 상세 평가 기준 → `docs/references/evaluation.md`.

---

## 에스컬레이션 기준 (멈추고 Claude Code에 보고)

- 새 모듈 경계·패키지 구조 변경이 필요할 때.
- 시드 스키마 필드 추가·삭제가 필요할 때.
- 하이브리드 스코어링 가중치 기본값 결정이 필요할 때.
- 백엔드·프론트엔드 프레임워크 선택이 필요할 때.
- `project-brief.md`와 요구사항이 충돌하거나, 문서-코드 불일치 해소가 어려울 때.
