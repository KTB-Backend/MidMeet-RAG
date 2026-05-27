# RAG Design

> **목적**: RAG 파이프라인의 설계 결정과 각 단계의 구현 명세를 정의한다.
> 시스템 전체 구조는 [`architecture.md`](architecture.md), 평가 기준은 [`evaluation.md`](evaluation.md)를 참고한다.

---

## 1. 파이프라인 개요

파이프라인은 **인덱싱 단계**와 **질의 단계** 두 흐름으로 나뉜다.

```
[인덱싱 단계] (사전 실행)
시드 로딩 → 검증 → 분위기 텍스트 임베딩 → Chroma 저장 (메타데이터 포함)

[질의 단계] (사용자 요청 시)
분위기 조건 임베딩 → Chroma 검색 (top-k) → 하이브리드 스코어링 → 프롬프트 조립 → LLM 생성 → 결과 출력
```

---

## 2. 인덱싱 단계

### 2-1. 시드 로딩

- `data/seeds/processed/`에서 JSON 레코드를 읽는다.
- 각 레코드는 식당·카페 한 곳을 나타낸다.
- 필수 필드 누락 또는 값 이상 시 인덱싱을 중단하고 오류를 보고한다.

### 2-2. 시드 검증

인덱싱 전 각 레코드를 검증한다.

| 검증 항목 | 기준 |
|-----------|------|
| 필수 필드 존재 | `place_id`, `name`, `address`, `latitude`, `longitude`, `atmosphere_text`, `attributes`, `source` |
| 좌표 유효 범위 | 위도 33~39, 경도 124~132 (한반도 범위) |
| `atmosphere_text` 최소 길이 | 50자 이상 권장 |
| `source` 존재 | 출처 없는 시드는 인덱싱 거부 |

### 2-3. 임베딩

- 임베딩 대상: `atmosphere_text` 필드.
- 모델: `dragonkue/snowflake-arctic-embed-l-v2.0-ko` (교체 가능 추상화 필수).
- 출력 차원: 1024-dim float vector.
- 배치 처리로 시드 전체를 일괄 임베딩한다.

### 2-4. Chroma 저장

```
document  : atmosphere_text
embedding : 1024-dim vector
metadata  : {
  place_id, name, address,
  latitude, longitude,
  attributes (JSON string),
  source (JSON string)
}
```

- Chroma 컬렉션 이름과 경로는 환경변수로 주입한다.
- 재인덱싱 시 동일 `place_id`는 업데이트하고 새 레코드는 추가한다.

---

## 3. 질의 단계

### 3-1. 분위기 조건 임베딩

- 사용자가 입력한 자연어 조건("조용히 이야기하기 좋은 카페")을 같은 임베딩 모델로 벡터화한다.
- **동일 모델 사용 필수**: 인덱싱 모델과 질의 모델이 다르면 코사인 유사도가 무의미해진다.

### 3-2. Chroma 벡터 검색

- `top_k` 개의 후보를 코사인 유사도 기준으로 검색한다.
- 검색 결과에는 각 후보의 `atmosphere_score`(코사인 유사도)와 메타데이터가 포함된다.
- `top_k`는 환경변수 `RETRIEVAL_TOP_K`로 설정 (기본값 10).

### 3-3. 하이브리드 스코어링

벡터 검색 결과에 거리 점수를 합산해 최종 순위를 계산한다.

#### 거리 점수 정규화

거리(km)와 분위기 유사도(0–1)는 스케일이 다르므로 거리를 0–1로 정규화한다.

```
distance_score = max(0, 1 - distance_km / MAX_DISTANCE_KM)
```

- `MAX_DISTANCE_KM`: 환경변수로 설정 (기본값 3.0km). 이 반경 밖은 distance_score = 0.
- 중간지점과 각 시드 좌표 사이의 직선거리를 Haversine 공식으로 계산한다.

#### 가중합

```
final_score = α × atmosphere_score + (1 - α) × distance_score
```

- `α`: 환경변수 `ATMOSPHERE_WEIGHT`로 설정 (기본값 0.7).
- 하드코딩 금지. 가중치 튜닝은 설정 변경만으로 가능해야 한다.
- `final_score` 기준으로 내림차순 정렬해 상위 결과를 반환한다.

#### 점수 출력 요구사항

검색 결과에는 반드시 세 점수를 모두 포함한다.

```python
{
    "place_id": str,
    "name": str,
    "atmosphere_score": float,   # 코사인 유사도 (0–1)
    "distance_score": float,     # 정규화 거리 점수 (0–1)
    "final_score": float,        # 가중합 최종 점수 (0–1)
    "distance_km": float,        # 실제 거리 (km)
    ...metadata
}
```

---

## 4. 생성 단계

### 4-1. 프롬프트 조립

- 검색된 상위 `k`개 시드의 `atmosphere_text`, `attributes`, `source`를 프롬프트에 삽입한다.
- 각 시드의 `place_id`를 근거로 명시한다.
- 프롬프트 템플릿: [`docs/prompts/recommendation-system.md`](prompts/recommendation-system.md) 참고.

### 4-2. 생성 LLM 호출

- 모델: `Qwen/Qwen3-4B-Instruct-2507` (교체 가능 추상화 필수).
- **출처 충실성 원칙**: LLM이 시드 텍스트 외의 정보를 생성하지 않도록 프롬프트에서 강하게 제약한다.
- 생성 결과에는 각 추천마다 근거 시드 ID를 포함시킨다.

### 4-3. 생성 결과 검증

생성 결과를 반환하기 전 다음을 확인한다.

- 모든 분위기 claim이 시드의 `atmosphere_text` 또는 `attributes`에 추적 가능한가.
- 근거 없는 주장이 포함되지 않았는가.
- 각 추천에 근거 시드 ID가 명시되어 있는가.

---

## 5. 모델 교체 가능 구조

### 5-1. 임베딩 어댑터

```python
class EmbeddingAdapter(ABC):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

# 현재 구현체
class SnowflakeArcticEmbedAdapter(EmbeddingAdapter): ...

# 교체 후보 (나중에 추가)
class BGEm3Adapter(EmbeddingAdapter): ...
```

모델 이름은 `EMBEDDING_MODEL_NAME` 환경변수로 주입해 런타임에 결정한다.

### 5-2. 생성 어댑터

```python
class GenerationAdapter(ABC):
    def generate(self, prompt: str) -> str: ...

# 현재 구현체
class Qwen3LocalAdapter(GenerationAdapter): ...

# 교체 후보 (나중에 추가)
class OpenAIAdapter(GenerationAdapter): ...   # TBD
class AnthropicAdapter(GenerationAdapter): ... # TBD
```

로컬 모델 실행이 어려운 경우 API 어댑터로 교체한다. 교체 시 프롬프트와 출처 충실성 제약은 그대로 유지한다.

---

## 6. 출처 충실성 원칙

RAG의 핵심 신뢰성 원칙.

- **LLM은 검색된 시드 정보 안에서만 답한다.** 시드에 없는 사실은 생성하지 않는다.
- **근거가 부족하면 추측하지 않는다.** "제공된 근거만으로는 확인하기 어렵다"고 답한다.
- **각 추천에 근거 시드 ID를 명시한다.** 사용자가 원문 근거를 확인할 수 있어야 한다.
- LLM이 지어낸 분위기를 시드 데이터로 저장하지 않는다. 시드는 항상 실재 장소 기반으로 직접 작성·검수한다.

---

## 7. 파이프라인 구현 순서

다음 순서를 기본값으로 삼는다. 이전 단계가 안정화되지 않으면 다음 단계로 넘어가지 않는다.

1. 시드 스키마 정의 및 검증
2. 임베딩 어댑터 구현 (추상화 계층 포함)
3. Chroma 인덱싱
4. 쿼리 검색
5. 거리 정규화
6. 하이브리드 스코어링
7. 근거 기반 프롬프트 조립
8. 생성 어댑터 구현 (추상화 계층 포함)
9. 평가 하네스
10. API · UI 연동 (TBD)
