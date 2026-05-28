# API Design (DRAFT)

> **상태**: DRAFT. 백엔드 웹 프레임워크가 확정되지 않았으므로 이 문서는 초안이다.
> 프레임워크가 결정되면 이 문서를 구체화한다.
>
> **현재 RAG 파이프라인은 API 없이 `scripts/query_harness.py`로 직접 실행한다.**
> 이 문서는 나중에 웹 서비스화할 때를 대비한 설계 후보다.

---

## 1. 내부 Python 인터페이스 (프레임워크 독립)

프레임워크가 무엇이든 `rag_core`의 Python 함수 인터페이스는 동일하다.
API 계층은 이 함수들을 HTTP 또는 다른 인터페이스로 감쌀 뿐이다.

### 1-1. 좌표 변환

```python
def geocode(query: str) -> tuple[float, float]:
    """
    카카오 로컬 API로 텍스트를 위경도 좌표로 변환.

    Args:
        query: 지하철역명, 주소, 동네 이름 등

    Returns:
        (latitude, longitude) 튜플

    Raises:
        GeocodingError: API 호출 실패 또는 결과 없음
    """
```

### 1-2. 중간지점 계산

```python
def compute_centroid(
    coordinates: list[tuple[float, float]]
) -> tuple[float, float]:
    """
    N개 좌표의 직선거리 중점(geometric centroid) 계산.

    Args:
        coordinates: [(lat1, lng1), (lat2, lng2), ...] (최소 1개)

    Returns:
        (centroid_latitude, centroid_longitude)
    """
```

### 1-3. 추천 요청

```python
@dataclass
class RecommendationResult:
    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    atmosphere_score: float   # 코사인 유사도 (0–1)
    distance_score: float     # 정규화 거리 점수 (0–1)
    final_score: float        # 가중합 최종 점수 (0–1)
    distance_km: float        # 실제 거리 (km)
    reason: str               # LLM 생성 추천 이유
    seed_ids: list[str]       # 근거 시드 ID 목록
    atmosphere_text: str      # 원문 시드 텍스트 (검증용)


def recommend(
    centroid: tuple[float, float],
    atmosphere_query: str,
    top_k: int = 5,
) -> list[RecommendationResult]:
    """
    중간지점과 분위기 조건으로 상위 k개 추천 결과 반환.

    Args:
        centroid: (latitude, longitude)
        atmosphere_query: 자연어 분위기 조건
        top_k: 최종 표시 추천 수 (RECOMMEND_TOP_K, 기본 5).
               내부 벡터 검색은 RETRIEVAL_TOP_K(기본 10)개를 가져와
               스코어링한 뒤 상위 top_k개를 반환한다.

    Returns:
        final_score 내림차순으로 정렬된 추천 목록
    """
```

---

## 2. REST API 후보 (TBD — 웹 프레임워크 결정 후 확정)

**프레임워크**: TBD (FastAPI 등 후보. 파이프라인 완성 후 결정)

### 2-1. 추천 요청

```
POST /api/v1/recommend
Content-Type: application/json
```

**요청 바디 후보**:

```json
{
  "locations": [
    "강남역",
    "홍대입구역",
    "신촌역"
  ],
  "atmosphere_query": "조용히 이야기하기 좋은 카페",
  "top_k": 5
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `locations` | string[] | ✅ | 출발지 텍스트 목록 (2개 이상 권장) |
| `atmosphere_query` | string | ✅ | 자연어 분위기 조건 |
| `top_k` | integer | ❌ | 최종 표시 추천 수 (RECOMMEND_TOP_K, 기본값 5). 내부 검색 수는 RETRIEVAL_TOP_K(기본 10) |

**응답 바디 후보**:

```json
{
  "centroid": {
    "latitude": 37.5573,
    "longitude": 126.9245
  },
  "recommendations": [
    {
      "place_id": "hd_001",
      "name": "카페 예시",
      "address": "서울 마포구 홍대입구역 인근",
      "latitude": 37.5573,
      "longitude": 126.9245,
      "atmosphere_score": 0.87,
      "distance_score": 0.74,
      "final_score": 0.83,
      "distance_km": 0.8,
      "reason": "좌석 간격이 넓고 배경 음악이 잔잔해 대화하기 좋습니다. [근거: hd_001]",
      "seed_ids": ["hd_001"]
    }
  ],
  "query_meta": {
    "atmosphere_query": "조용히 이야기하기 좋은 카페",
    "atmosphere_weight": 0.7,
    "max_distance_km": 3.0,
    "retrieved_count": 5
  }
}
```

### 2-2. 좌표 변환 (선택적 분리 엔드포인트)

```
POST /api/v1/geocode
```

```json
// 요청
{ "query": "강남역" }

// 응답
{ "latitude": 37.4979, "longitude": 127.0276, "name": "강남역" }
```

### 2-3. 에러 응답 형식 후보

```json
{
  "error": {
    "code": "GEOCODING_FAILED",
    "message": "위치를 찾을 수 없습니다: '존재하지않는곳역'",
    "field": "locations[2]"
  }
}
```

**에러 코드 후보**:

| 코드 | HTTP 상태 | 설명 |
|------|-----------|------|
| `GEOCODING_FAILED` | 422 | 위치 텍스트를 좌표로 변환 실패 |
| `NO_SEEDS_FOUND` | 404 | 검색 결과가 0건 (컬렉션이 비었거나 검색 실패). **반경 밖이라는 이유로는 발생하지 않음** — 거리는 소프트 스코어링(score=0)으로만 반영 |
| `INVALID_LOCATION_COUNT` | 422 | 위치 목록이 비어 있음 |
| `LLM_GENERATION_FAILED` | 500 | 추천 이유 생성 실패 |
| `INTERNAL_ERROR` | 500 | 기타 내부 오류 |

---

## 3. 카카오 로컬 API 래퍼

`rag_core` 외부에서 카카오 로컬 API를 감싸는 클라이언트.

```python
class KakaoLocalClient:
    def __init__(self, api_key: str): ...

    def geocode(self, query: str) -> tuple[float, float]:
        """텍스트 → 위경도 좌표 변환"""

    def search_place(self, query: str, x: float, y: float, radius: int = 3000):
        """중심 좌표 기준 장소 검색 (나중에 실시간 검색이 필요할 때)"""
```

API 키는 환경변수 `KAKAO_REST_API_KEY`로 주입. 코드에 하드코딩 금지.

---

## 4. 미확정 사항 (TBD)

| 항목 | 상태 | 비고 |
|------|------|------|
| 백엔드 웹 프레임워크 | TBD | FastAPI 등 후보, 파이프라인 완성 후 결정 |
| 인증 방식 | TBD | MVP에서는 불필요할 수 있음 |
| API 버전 관리 방식 | TBD | `/v1/` 접두사 사용 예정 |
| 응답 캐싱 | TBD | 동일 쿼리 반복 시 Chroma 재검색 여부 |
| 지도 UI와의 통합 방식 | TBD | REST API vs WebSocket 등 |
| 배포 환경 | TBD | — |

---

## 5. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-28 | 초안 작성 (DRAFT). 프레임워크 TBD 상태로 Python 인터페이스 중심으로 정의. |
| 2026-05-28 | 문서 정합: top_k를 RECOMMEND_TOP_K(표시)/RETRIEVAL_TOP_K(검색)로 구분, NO_SEEDS_FOUND 의미 명확화. |
