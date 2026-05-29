# How to Run / Test — 로컬 검증 런북

> **목적**: 로컬 venv에서 지금까지 구축한 RAG 파이프라인을 **단계별로 직접 실행·검증**한다.
> 위에서 아래로 명령을 복사해 실행하면 된다. 각 단계에 **통과 기준**을 함께 적었다.
> 진행 현황 정본은 [`task-plan.md`](task-plan.md), 평가 기준 정본은 [`../references/evaluation.md`](../references/evaluation.md).
> 모든 명령은 **프로젝트 루트**에서, **venv 활성화 상태**로 실행한다.

---

## 현재 상태 한눈에

| 계층 | 단계 | 결정적 단위테스트(tests/) | 통합 스모크(evals/) | 실행 스크립트 |
|------|------|:---:|:---:|------|
| 시드 로딩·검증 | S0 | ✅ | — | — |
| 임베딩 어댑터 | S2 | ✅ | ✅(실모델) | — |
| Chroma 인덱싱 | S3 | ✅ | ✅(Chroma) | `scripts/index_seeds.py` |
| 쿼리 검색 | S4 | ✅ | ✅(Chroma) | — |
| 거리·하이브리드 스코어링 | S5 | ✅ | — (순수 함수) | — |
| 프롬프트 조립 | S6 | ⬜ 예정 | | |
| 생성(LLM) | S7 | ⬜ 예정 | | |
| 카카오 geocode | S1 | ⬜ 예정 | | |
| 전체 질의 하네스 | S8 | ⬜ 예정 | | `scripts/query_harness.py`(미구현) |

> **end-to-end 질의 스크립트는 아직 없습니다.** "출발지 입력 → 추천 결과 출력"을 한 번에 도는 `query_harness`는 **S8**에서 생깁니다. 지금은 (1) 결정적 단위테스트, (2) 통합 스모크, (3) 실모델 인덱싱까지 검증할 수 있습니다.

---

## 0. 사전 준비 (최초 1회)

```bash
# Python 3.11 확인 (.python-version = 3.11.9)
python --version          # 또는 python3.11 --version

# venv 생성·활성화
python -m venv .venv
source .venv/bin/activate

# 기본 설치 (결정적 테스트용)
python -m pip install -e ".[dev]"
```

> **설치 변형 3가지** — 검증 깊이에 따라 골라 설치한다.
> - `.[dev]` → 결정적 단위테스트(1번)만. 빠르고 네트워크 불필요.
> - `.[dev,vectorstore]` → + Chroma 통합 스모크(2번). `chromadb` 설치.
> - `.[dev,embeddings,vectorstore]` → + 실모델 인덱싱(3번). `sentence-transformers`·`chromadb` 설치, 임베딩 모델(~1–2GB) 자동 다운로드.

---

## 1. 결정적 단위 테스트 (모델·Chroma 불필요) — 먼저 이것부터

파이프라인 **로직**의 정확성을 모델·DB 없이 검증한다. 가장 빠르고 항상 같은 결과(결정적)다.

```bash
python -m pytest
```

**통과 기준**: `N passed`, **실패·에러 0건**. (현재 기준 `47 passed`. S6~S8 추가 시 숫자는 늘어난다.)
`tests/`만 수집된다(`pyproject.toml`의 `testpaths=["tests"]`). 모델·Chroma는 로드되지 않는다.

### 단계별로 따로 보고 싶을 때

각 파일이 **무엇을 보장하는지**와 함께:

```bash
python -m pytest tests/test_seed_validation.py   # S0: 필수필드·좌표범위·place_id 고유성 검증이 잘못된 시드를 잡는가
python -m pytest tests/test_fixtures.py           # S0: 합성 픽스처 7개가 스키마·검증을 통과하는가
python -m pytest tests/test_embedder.py           # S2: ABC 계약, query/document 프리픽스 라우팅
python -m pytest tests/test_indexer.py            # S3: 메타 JSON 직렬화, HNSW config 빌드, 재인덱싱 모델 가드
python -m pytest tests/test_retriever.py          # S4: distance→atmosphere_score 변환, Chroma 응답 매핑, 무결과 처리
python -m pytest tests/test_geo.py                # S5: centroid 산술평균, Haversine 거리
python -m pytest tests/test_scorer.py             # S5: 거리 정규화, 분위기 clamp, 가중합, 정렬·top-k, 소프트 스코어링
```

**통과 기준**(각 파일 공통): 해당 파일 전부 `passed`, 실패 0. 한 파일만 실패하면 그 계층에 회귀가 생긴 것.

---

## 2. 통합 스모크 (evals/ — 실제 Chroma 사용)

`tests/`가 **로직**을 본다면, `evals/`는 **실제 Chroma에 넣고 빼는 통합**을 본다(임베딩은 결정적 Fake 임베더 사용 → 모델 다운로드 불필요). 기본 `pytest`에는 수집되지 않으므로 **따로** 실행한다.

```bash
python -m pip install -e ".[dev,vectorstore]"
python -m pytest evals
```

**통과 기준**: `2 passed, 1 skipped`, 실패·에러 0건.
- `test_indexer_smoke.py` ✅ — 시드 3개를 실제 Chroma에 upsert → `count` 일치, 메타데이터(한글 attributes/source) 라운드트립, 동일 `place_id` 재upsert 시 개수 불변(idempotency).
- `test_retriever_smoke.py` ✅ — 인덱싱 후 "조용" 쿼리가 **조용한 시드를 최상위**로 반환(검색 순서·atmosphere_score).
- `test_embedder_smoke.py` ⏭️ skipped — 실모델(sentence-transformers) 미설치라 건너뜀. (3번에서 설치하면 실행)

> `skipped`는 실패가 아니다. 해당 의존성이 없을 때 안전하게 건너뛰도록 설계된 것이다.

---

## 3. 실모델 검증 (실제 임베딩 모델 다운로드)

실제 `dragonkue/snowflake-arctic-embed-l-v2.0-ko` 모델로 임베딩·인덱싱이 도는지 확인한다. **공개 모델이라 Hugging Face 인증 불필요**, 첫 실행 시 `~/.cache/huggingface/`로 자동 다운로드된다(~1–2GB, 네트워크 필요).

```bash
python -m pip install -e ".[dev,embeddings,vectorstore]"

# (선택) 실모델 임베딩 스모크 — 1024-dim 벡터가 나오는지
python -m pytest evals          # 이제 3 passed (embedder 스모크까지 실행)

# 실제 인덱싱: 픽스처 7개를 실제 모델로 임베딩 후 Chroma에 저장
python -m scripts.index_seeds --seed-dir data/seeds/fixtures
```

**통과 기준 (`index_seeds`)**: 오류 없이 종료하고 아래처럼 출력:
```
collection=venues
path=data/chroma/
indexed_count=7
collection_count=7
```
→ `indexed_count == collection_count == 7`(픽스처 개수)이면 성공. `data/chroma/`에 인덱스가 생긴다(커밋 금지, `.gitignore` 처리됨).
재실행해도 `collection_count`는 7로 유지된다(동일 `place_id` 업데이트).

---

## 전체를 한 번에 (풀 체크)

```bash
python -m pip install -e ".[dev,embeddings,vectorstore]"
python -m pytest            # 1) 결정적 단위 (전부 passed)
python -m pytest evals      # 2)+3) 통합 스모크 (3 passed)
python -m scripts.index_seeds --seed-dir data/seeds/fixtures   # 실모델 인덱싱 (count=7)
```

세 명령이 모두 위 통과 기준을 만족하면, **시드 → 임베딩 → 인덱싱 → 검색 → 하이브리드 스코어링**까지 정상입니다.

---

## 아직 실행 불가 (예정)

- **S6 프롬프트 조립 / S7 생성(LLM) / S8 전체 질의 하네스** 미구현.
- 따라서 *"출발지·분위기 입력 → 추천 결과(추천 이유 포함) 출력"* end-to-end 실행은 **S8(`scripts/query_harness.py`) 이후** 가능하다. 그때 이 문서에 4번 단계를 추가한다.
- 카카오 geocode(텍스트→좌표, S1)도 S8 직전에 붙는다. 그전까지 좌표는 시드 메타데이터·테스트 픽스처로만 검증한다.

---

## 문제 해결 (troubleshooting)

| 증상 | 원인·해결 |
|------|-----------|
| `pytest evals`가 전부 `skipped` | `chromadb` 미설치 → `pip install -e ".[dev,vectorstore]"`. |
| embedder 스모크만 계속 `skipped` | `sentence-transformers` 미설치 → `pip install -e ".[dev,embeddings,vectorstore]"`. |
| `index_seeds`가 모델 다운로드에서 멈춤 | 네트워크 필요. 사내망·프록시 환경이면 인터넷 접근 확인. 인증은 불필요(공개 모델). |
| `CollectionModelGuardError` (재인덱싱 시) | 기존 컬렉션을 **다른 임베딩 모델/차원**으로 만들었다는 뜻. `data/chroma/`를 지우고 재인덱싱하거나 `CHROMA_COLLECTION`을 다른 이름으로. |
| `python -m scripts.index_seeds` 인자 없이 실행 시 실패 | 기본 `--seed-dir`가 비어 있는 `data/seeds/processed/`다. 부트스트랩은 `--seed-dir data/seeds/fixtures`로 지정. |
| 테스트가 시스템 python으로 도는 느낌 | venv 활성화 확인(`which python`이 `.venv/bin/python`인지). |
