# Task Plan

> **목적**: 구현 마일스톤과 각 작업의 담당 도구, 완료 조건을 정의한다.
> 작업 우선순위의 근거는 [`project-brief.md`](../product-specs/project-brief.md)의 "다음 할 일" 섹션이다.
> 담당 도구: **Claude Code** (설계·검토·검증) / **Codex CLI** (구현·테스트·리팩토링)

---

## 마일스톤 개요

| 마일스톤 | 내용 | 상태 |
|----------|------|------|
| M0 | 기반 설계 확정 | ✅ 완료 |
| M1 | 시드 데이터 준비 (픽스처 먼저 → 실데이터 나중) | ⬜ 대기 |
| M2 | RAG 파이프라인 구현 (픽스처로 검증) | ⬜ 대기 |
| M3 | 평가 하네스 | ⬜ 대기 |
| M4 | 지도 UI 연동 | ⬜ TBD |
| M5 | 모델 튜닝 및 상권 확장 | ⬜ TBD |

---

## M0 — 기반 설계 확정 ✅

**담당**: Claude Code

| 작업 | 설명 | 완료 조건 |
|------|------|-----------|
| 프로젝트 기획서 확정 | `docs/product-specs/project-brief.md` 작성 | MVP 범위·제외 범위·의사결정 정리 |
| 아키텍처 설계 | `docs/design-docs/architecture.md` 작성 | 모듈 경계·의존 규칙·설정 주입 정의 |
| RAG 파이프라인 설계 | `docs/design-docs/rag-design.md` 작성 | 스코어링 수식·추상화 구조 정의 |
| 데이터 구조 설계 | `docs/design-docs/data-design.md` 작성 | 시드 스키마·샘플 JSON 정의 |
| API 설계 초안 | `docs/design-docs/api-design.md` 작성 | Python 인터페이스 후보 정의 (DRAFT) |
| 평가 기준 정의 | `docs/references/evaluation.md` 작성 | 평가 레이어·체크리스트 정의 |
| AGENTS.md / CLAUDE.md 정비 | AI 개발 하네스 구축 | 역할 분리·중복 제거 |

---

## M1 — 시드 데이터 준비

**담당**: 수동 작업 (Claude Code가 기준 제공)

> **전략: 픽스처 먼저, 실데이터 나중.** 합성 픽스처(M1-0)로 파이프라인(M2)을 끝까지 돌려 검증한 뒤, 실데이터 수제작 시드(M1-1·M1-2)를 작성해 동일 경로로 교체한다. 픽스처와 실데이터의 구분 정본은 [`data-design.md`](../design-docs/data-design.md) §10이다.

### M1-0. 합성 픽스처 작성 (파이프라인 부트스트랩)

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI (생성) → Claude Code (스키마 준수 확인) |
| **작업** | `source.type="fixture"`인 합성 레코드 5~10개 작성 (`data/seeds/fixtures/`) |
| **기준** | [`data-design.md`](../design-docs/data-design.md) 스키마 준수. 실재 장소 검증 불필요, 사용자 추천 노출 금지 |
| **완료 조건** | 검증 통과(하드 실패 0개), 파이프라인 부트스트랩 가능 |

### M1-1. 시작 상권 선정 (실데이터, 파이프라인 안정화 후/병행)

| 항목 | 내용 |
|------|------|
| **담당** | Claude Code (후보 분석·제안) → 사용자 결정 |
| **작업** | 서울 핵심 상권 후보(강남·홍대·성수 등) 중 파이프라인 테스트에 적합한 1곳 선정 |
| **완료 조건** | 상권 선정 완료, 이유 문서화 |

### M1-2. 실데이터 시드 텍스트 작성 (파이프라인 안정화 후)

| 항목 | 내용 |
|------|------|
| **담당** | 수동 작업 (사용자) |
| **작업** | 선정된 상권에서 식당·카페 20–30개 시드 레코드 작성 (`data/seeds/raw/`) |
| **기준** | `docs/design-docs/data-design.md`의 스키마와 atmosphere_text 작성 기준 준수 |
| **완료 조건** | `data/seeds/raw/` 에 JSON 파일 저장, 필드 전체 작성, atmosphere_text 50자 이상 권장 |

### M1-3. 시드 검증

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI (검증 스크립트 구현 = M2 S0) → Claude Code (검증 결과 확인) |
| **작업** | 필수 필드·좌표 범위·`place_id` 고유성·`source` 존재(하드 실패), `atmosphere_text` 길이(경고) 자동 검증. 픽스처·실데이터 공통 적용 |
| **완료 조건** | `python -m pytest tests/test_seed_validation.py` 통과, 하드 실패 0개 |

---

## M2 — RAG 파이프라인 구현

**담당**: Codex CLI (구현) / Claude Code (설계 검토·완료 조건 검증)

> **M2는 M1-0 합성 픽스처만으로 끝까지 실행·검증 가능하다.** 실데이터(M1-1·M1-2)를 기다리지 않는다. 각 단계는 [`rag-design.md`](../design-docs/rag-design.md) §7 순서를 따르며, 이전 단계 안정화 전 다음으로 넘어가지 않는다. 위임 단위(S0~S8)는 단계별 순차 위임이다.

### M2-1. 카카오 로컬 API 연동 및 중간지점 계산

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI |
| **작업** | `KakaoLocalClient.geocode()` 구현, `compute_centroid()` 구현 |
| **대상 파일** | `packages/rag_core/geo.py` (또는 `scripts/kakao_client.py`) |
| **완료 조건** | `pytest tests/test_geo.py` 통과, centroid 수학 검증 포함 |

### M2-2. 임베딩 어댑터

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI |
| **작업** | `EmbeddingAdapter` 추상 클래스 + `SnowflakeArcticEmbedAdapter` 구현 |
| **대상 파일** | `packages/rag_core/embedder.py` |
| **완료 조건** | 텍스트 리스트 → float 벡터 리스트 변환 동작 확인, 단위 테스트 통과 |

### M2-3. Chroma 인덱싱

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI |
| **작업** | 시드 레코드를 Chroma에 저장하는 `scripts/index_seeds.py` 구현 |
| **대상 파일** | `packages/rag_core/indexer.py`, `scripts/index_seeds.py` |
| **완료 조건** | 인덱싱 후 Chroma 레코드 수 확인, 메타데이터 보존 확인 |

### M2-4. 쿼리 검색

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI |
| **작업** | 분위기 조건 임베딩 후 Chroma에서 top-k 검색 |
| **대상 파일** | `packages/rag_core/retriever.py` |
| **완료 조건** | 검색 결과에 `atmosphere_score` 포함, `pytest tests/test_retriever.py` 통과 |

### M2-5. 거리 정규화 및 하이브리드 스코어링

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI |
| **작업** | Haversine 거리 계산, `distance_score` 정규화, `final_score` 가중합 |
| **대상 파일** | `packages/rag_core/scorer.py` |
| **완료 조건** | 세 점수(atmosphere, distance, final) 출력 확인, 점수 0–1 범위 검증, `pytest tests/test_scorer.py` 통과 |

### M2-6. 근거 기반 프롬프트 조립

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI |
| **작업** | 검색된 시드를 프롬프트에 삽입, `docs/prompts/recommendation-system.md` 템플릿 사용 |
| **대상 파일** | `packages/rag_core/assembler.py` |
| **완료 조건** | 프롬프트에 시드 ID와 atmosphere_text 포함 확인, 시드 외 정보 미포함 확인 |

### M2-7. 생성 어댑터

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI |
| **작업** | `GenerationAdapter` 추상 클래스 + `Qwen3LocalAdapter` 구현 |
| **대상 파일** | `packages/rag_core/generator.py` |
| **완료 조건** | 추천 이유 생성 확인, 근거 시드 ID 출력 확인, 로컬 실행 불가 시 대체 경로 문서화 |

### M2-8. 전체 하네스 실행

| 항목 | 내용 |
|------|------|
| **담당** | Codex CLI (구현) + Claude Code (결과 검토) |
| **작업** | `scripts/query_harness.py` 구현 (입력 → 좌표 → 중간지점 → 검색 → 생성 → 출력 전체 흐름) |
| **완료 조건** | `python -m scripts.query_harness --query "조용한 카페" --locations "강남역,홍대역"` 실행 성공 |

---

## M3 — 평가 하네스

**담당**: Codex CLI (구현) / Claude Code (기준 설계·결과 해석)

| 작업 | 담당 | 완료 조건 |
|------|------|-----------|
| pytest 단위 테스트 보강 | Codex CLI | centroid 수학, 거리 정규화, 점수 가중합, 메타데이터 보존 |
| evals/ 고정 fixture 작성 | Codex CLI + 수동 | 기본 테스트 쿼리 4개 이상에 대한 기대 결과 정의 |
| 출처 충실성 검증 스크립트 | Codex CLI | 생성 결과의 claim을 시드 원문과 대조하는 스크립트 |
| 검색·생성 리포트 출력 | Codex CLI | 실행 시 점수·시드 ID·근거 텍스트를 포함한 리포트 생성 |

---

## M4 — 지도 UI 연동 (TBD)

**상태**: RAG 파이프라인 안정화 후 결정.

| 항목 | 내용 |
|------|------|
| **프레임워크** | TBD |
| **작업 후보** | 카카오맵 SDK 연동, 추천 핀 표시, 중간지점 마커, 추천 이유 팝업 |
| **시작 조건** | M3 완료 후 |

---

## M5 — 모델 튜닝 및 상권 확장 (TBD)

**상태**: M3 완료 후 시작.

| 작업 | 담당 | 설명 |
|------|------|------|
| 임베딩 모델 비교 | Claude Code (기준) + Codex CLI (구현) | arctic-embed vs BGE-m3, 동일 쿼리로 비교 |
| 가중치 튜닝 | Claude Code (설계) + Codex CLI (실험) | α 값 변화에 따른 추천 품질 변화 확인 |
| 생성 LLM 비교 | Claude Code (기준) + Codex CLI (구현) | Qwen3-4B vs Gemma 3 4B 등 |
| 상권 확장 | 수동 (시드 작성) + Codex CLI (인덱싱) | 홍대 → 강남 → 성수 등으로 확장 |

---

## 다음 즉시 할 일

1. **S0 시드 로더·검증 + M1-0 합성 픽스처 5~10개** (Codex CLI, `data/seeds/fixtures/`)
2. **M2 파이프라인 단계별 위임 (S1~S8)** — 임베딩→인덱싱→검색→스코어링→프롬프트→생성→전체 하네스. 이전 단계 안정화 후 진행
3. **파이프라인 안정화 후 실데이터 전환**: M1-1 상권 선정 → M1-2 실데이터 시드 20–30개 작성 → 재인덱싱
   - Codex 구현 프롬프트는 단계별로 요청 시 Claude Code가 `/codex-task`로 작성
