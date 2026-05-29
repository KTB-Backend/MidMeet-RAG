# Architecture

> **목적**: 이 문서는 시스템 전체 구조와 각 컴포넌트의 역할, 의존 관계를 정의한다.
> 파이프라인 설계 상세는 [`rag-design.md`](rag-design.md), 데이터 구조는 [`data-design.md`](data-design.md)를 참고한다.

---

## 1. 1차 목표

웹앱 완성이 아니라 **RAG 파이프라인 하네스**다. 구현은 다음 흐름을 독립적으로 실행하고 검증할 수 있어야 한다.

```
시드 데이터 → 임베딩 → Chroma 저장 → 하이브리드 스코어링 → 근거 기반 추천 생성
```

---

## 2. 전체 시스템 흐름

```
[출발지 텍스트 N개 입력]
         │
         ▼
[카카오 로컬 API]  ──────────────→  [위경도 좌표 N개]
                                           │
                                           ▼
                               [중간지점 계산 (Geometric Centroid)]
                                           │
                                           │◄── [사용자 분위기 조건 (자연어)]
                                           ▼
                               [분위기 조건 임베딩]
                                           │
                                           ▼
                              [Chroma 벡터 검색 (top-k)]
                                           │
                                           ▼
                              [하이브리드 스코어링]
                               ├── atmosphere_score (코사인 유사도, 0–1)
                               └── distance_score (정규화 거리, 0–1)
                                           │
                                           ▼
                              [상위 k개 후보 시드]
                                           │
                                           ▼
                    [Qwen3-4B 추천 이유 생성]◄── [시드 근거 + 프롬프트 제약]
                                           │
                                           ▼
                              [추천 결과 출력]
                               ├── 추천 이유 (자연어)
                               ├── 근거 시드 ID
                               └── atmosphere / distance / final score
                                           │
                                           ▼
                              [카카오맵 시각화 (TBD)]
```

---

## 3. 모듈 경계

```
packages/rag_core/    # 핵심 RAG 로직. API·UI 의존성 없음.
  ├── loader.py       # 시드 데이터 로딩·검증
  ├── embedder.py     # 임베딩 어댑터 (교체 가능 추상화)
  ├── indexer.py      # Chroma 인덱싱
  ├── retriever.py    # 쿼리 검색·하이브리드 스코어링
  ├── scorer.py       # 거리 정규화·가중합 계산
  ├── geo.py          # 좌표·중간지점 (centroid·Haversine 거리)
  ├── assembler.py    # 근거 기반 프롬프트 조립
  └── generator.py   # 생성 어댑터 (교체 가능 추상화)

apps/rag_api/         # 추후 추가할 얇은 API 계층 (프레임워크 TBD)
                      # rag_core를 호출만 함. RAG 로직 없음.

scripts/
  ├── index_seeds.py  # 시드 인덱싱 진입점
  └── query_harness.py # 단일 쿼리 실행 진입점

tests/                # 결정적(deterministic) pytest 테스트. 모델·Chroma 의존 없음.
evals/                # 모델·Chroma 의존적인 검증 케이스. 고정 fixture 사용.

data/
  ├── seeds/fixtures/  # 합성 픽스처 (개발·평가 전용, 커밋됨)
  ├── seeds/raw/       # 실데이터 수제작 시드 원본 (커밋됨)
  ├── seeds/processed/ # 검증·정규화 완료 = 인덱싱 입력 (커밋됨)
  └── chroma/          # 로컬 Chroma 인덱스 (커밋 금지)
```

**핵심 의존 규칙**: `rag_core`는 `apps/`, `scripts/`, `tests/` 어디에도 의존하지 않는다. 의존 방향은 항상 바깥 → `rag_core`다.

---

## 4. 카카오 로컬 API 연동

**역할**: 텍스트(지하철역명·주소·동네 이름) → 위경도 좌표 변환.

**연동 위치**: `rag_core` 외부. 좌표 변환은 입력 전처리 단계에서 수행한다. `rag_core`는 이미 변환된 좌표만 받는다. 이렇게 하면 `rag_core`가 Kakao API에 의존하지 않아 테스트 가능성이 높아진다.

```
scripts/query_harness.py
  └─▶ kakao_client.geocode(text) → (lat, lng)  # rag_core 외부
  └─▶ geo.compute_centroid([(lat1,lng1), ...]) → (lat, lng)
  └─▶ rag_core.retriever.search(centroid, query) → results
```

**API 키**: 환경변수 `KAKAO_REST_API_KEY`로 주입. 코드에 하드코딩 금지.

---

## 5. Chroma 벡터 DB 구조

```
Collection: venues  (이름은 환경변수로 설정 가능)
  ├── document:   atmosphere_text  (의미 검색 대상)
  ├── embedding:  1024-dim float vector  (snowflake-arctic-embed-l-v2.0-ko)
  └── metadata:
        place_id, name, address,
        latitude, longitude,
        attributes (JSON string),
        source (JSON string)
```

**경로**: 환경변수 `CHROMA_PATH`로 주입. 기본값 `data/chroma/`. 커밋 금지.

**인덱싱 시점**: `scripts/index_seeds.py`를 실행할 때마다 `data/seeds/processed/`의 레코드를 읽어 Chroma에 저장한다.

**실행 위치**: 임베딩·인덱싱은 로컬에서 수행한다. Chroma 인덱스는 시드에서 파생되는 재생성 산출물이므로 머신 간 전송 대상이 아니다(쿼리가 도는 곳에서 재인덱싱). 무거운 생성 모델만 필요 시 Colab/API로 분리한다.

---

## 6. 임베딩 모델 어댑터

**원칙**: 모델 이름이 비즈니스 로직에 하드코딩되지 않도록 추상화 계층을 둔다. 모델 교체는 설정 변경만으로 가능해야 한다.

```python
# packages/rag_core/embedder.py

class EmbeddingAdapter(ABC):
    def embed(self, texts: list[str], mode: str = "document") -> list[list[float]]:
        ...

class SnowflakeArcticEmbedAdapter(EmbeddingAdapter):
    """dragonkue/snowflake-arctic-embed-l-v2.0-ko"""
    def __init__(self, model_name: str | None = None): ...
    def embed(self, texts: list[str], mode: str = "document") -> list[list[float]]: ...
```

**설정**: 환경변수 `EMBEDDING_MODEL_NAME`으로 모델 이름 주입.
**현재 기본값**: `dragonkue/snowflake-arctic-embed-l-v2.0-ko`
**mode**: 인덱싱은 `document`, 질의는 `query`. query 모드에만 `"query: "` 프리픽스를 붙인다(모델 카드 기준). 상세 → [`rag-design.md`](rag-design.md) §2-3.

---

## 7. 생성 LLM 어댑터

**원칙**: 임베딩과 동일하게 교체 가능한 추상화 계층. 로컬 모델 실행이 어려울 경우 API 어댑터로 교체 가능해야 한다.

```python
# packages/rag_core/generator.py

class GenerationAdapter(ABC):
    def generate(self, prompt: str) -> str:
        ...

class Qwen3LocalAdapter(GenerationAdapter):
    """Qwen/Qwen3-4B-Instruct-2507 로컬 실행"""
    def __init__(self, model_name: str, **kwargs): ...
    def generate(self, prompt: str) -> str: ...

class APIAdapter(GenerationAdapter):
    """API 기반 LLM (추후 교체 옵션)"""
    ...  # TBD
```

**설정**: 환경변수 `GENERATION_MODEL_NAME`으로 모델 이름 주입.
**현재 기본값**: `Qwen/Qwen3-4B-Instruct-2507`
**주의**: 로컬 실행 불가 시 대체 경로를 문서화한다.

---

## 8. 지도 UI 연결 (TBD)

추천 결과를 카카오맵에 시각화하는 단계다. RAG 파이프라인이 안정화된 뒤 구현한다.

```
추천 결과 (place_id, name, latitude, longitude, reason)
         │
         ▼ (TBD: 어떤 계층에서 처리할지 미정)
[카카오맵 JavaScript SDK]
  ├── 출발지 핀
  ├── 중간지점 마커
  └── 추천 식당 핀 (클릭 시 추천 이유 팝업)
```

---

## 9. API 계층 (TBD)

`apps/rag_api/`는 RAG 파이프라인을 HTTP 또는 다른 인터페이스로 노출하는 얇은 계층이다.

- **프레임워크**: TBD. FastAPI, Flask 등 후보. 파이프라인 완성 후 결정.
- **역할**: `rag_core`를 호출만 함. RAG 로직을 직접 구현하지 않음.
- **초안**: [`api-design.md`](api-design.md) 참고.

---

## 10. 프론트엔드 (TBD)

- **프레임워크**: TBD.
- **요구 사항**: 출발지 입력 UI, 분위기 조건 입력, 카카오맵 표시, 추천 이유 노출.
- MVP에서는 CLI 또는 간단한 HTML로 대체 가능.

---

## 11. 배포 (TBD)

- **환경**: TBD.
- 로컬 모델(임베딩, LLM)을 포함하면 서버 사양 요구가 높아짐. 배포 전략은 모델 실행 방식과 함께 결정.

---

## 12. 설정 주입 규칙

비즈니스 로직에 하드코딩하지 않는 값:

| 설정 항목 | 환경변수 | 기본값 예시 |
|-----------|----------|-------------|
| 임베딩 모델명 | `EMBEDDING_MODEL_NAME` | `dragonkue/snowflake-arctic-embed-l-v2.0-ko` |
| 생성 LLM명 | `GENERATION_MODEL_NAME` | `Qwen/Qwen3-4B-Instruct-2507` |
| Chroma 경로 | `CHROMA_PATH` | `data/chroma/` |
| Chroma 컬렉션명 | `CHROMA_COLLECTION` | `venues` |
| 카카오 API 키 | `KAKAO_REST_API_KEY` | — |
| 검색 개수 k (벡터 검색) | `RETRIEVAL_TOP_K` | `10` |
| 추천 표시 개수 k (최종) | `RECOMMEND_TOP_K` | `5` |
| 최대 거리 반경 (km) | `MAX_DISTANCE_KM` | `3.0` |
| 분위기 가중치 α | `ATMOSPHERE_WEIGHT` | `0.7` |
| 거리 가중치 (1-α) | (1 - `ATMOSPHERE_WEIGHT`) | `0.3` |

---

## 13. 현재 미확정 사항 (Non-Goals For Now)

| 항목 | 상태 |
|------|------|
| 백엔드 웹 프레임워크 | TBD (FastAPI 등 후보) |
| 프론트엔드 프레임워크 | TBD |
| 배포 환경 | TBD |
| 대중교통 기반 최적 중간지점 | 파이프라인 안정화 후 |
| 공간 클러스터링(상권 단위 추천) | 시드 100개 이상 확보 후 |
| 협업형 위치 입력 (세션 관리) | API 계층 구축 후 |
