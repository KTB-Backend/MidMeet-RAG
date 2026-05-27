# Data Design

> **목적**: 시드 데이터의 구체적인 구조, 필드 정의, 작성 기준, 샘플 스키마를 정의한다.
> 데이터 정책(허용 출처, 금지 사항)은 [`data-policy.md`](../references/data-policy.md)를 참고한다.

---

## 1. 시드 데이터 단위

**식당·카페 한 곳 = 시드 레코드 하나.**

### 왜 식당 단위인가

- **정보 손실 방지**: 처음부터 상권 단위로 뭉치면 개별 식당의 분위기 차이가 사라진다. 식당 단위로 저장하면 언제든 상권으로 집계할 수 있다.
- **검색 정밀도**: 벡터 검색의 대상이 "강남 카페들의 평균 분위기"가 아니라 "카페 A의 분위기"여야 세밀한 매칭이 가능하다.
- **좌표 활용**: 각 식당의 정확한 좌표를 메타데이터로 갖고 있어야 거리 점수를 계산할 수 있다.

---

## 2. 시드 레코드 스키마

### 2-1. 필수 필드

| 필드 | 타입 | 설명 | 제약 |
|------|------|------|------|
| `place_id` | string | 내부 식별자 | 고유해야 함. 예: `"hd_001"` (상권 코드 + 순번) |
| `name` | string | 장소명 | 실제 상호명 |
| `address` | string | 주소 또는 행정구역 | 도로명 또는 지번 주소 |
| `latitude` | float | 위도 | 한반도 범위: 33.0–38.9 |
| `longitude` | float | 경도 | 한반도 범위: 124.6–131.9 |
| `atmosphere_text` | string | 분위기 서술 텍스트 | 50자 이상, 검색 매칭 표현 포함 필수 |
| `attributes` | object | 구조화 속성 | 아래 스키마 참고 |
| `source` | object | 출처 정보 | 작성자·확인일 포함 필수 |

### 2-2. attributes 스키마

```json
{
  "category": "카페 | 식당 | 술집",
  "parking": true | false | null,
  "wifi": true | false | null,
  "noise_level": "조용함 | 보통 | 시끄러움 | null",
  "seating_type": ["개인석", "단체석", "바 좌석"],
  "outdoor": true | false | null,
  "reservation": true | false | null,
  "price_range": "1인 평균 가격대 또는 null",
  "operating_hours": "운영시간 또는 null"
}
```

알 수 없는 값은 `null`로 표기한다. 추측하지 않는다.

### 2-3. source 스키마

```json
{
  "type": "hand_crafted | public_data",
  "author": "작성자 이름 또는 식별자",
  "verified_at": "YYYY-MM-DD",
  "reference": "참고한 공공데이터 URL 또는 현장 방문 메모",
  "notes": "기타 provenance 메모"
}
```

---

## 3. 전체 레코드 샘플 (JSON)

```json
{
  "place_id": "hd_001",
  "name": "카페 예시",
  "address": "서울 마포구 홍대입구역 인근",
  "latitude": 37.5573,
  "longitude": 126.9245,
  "atmosphere_text": "통유리창으로 햇볕이 잘 들어오고 좌석 간격이 넓어 대화하기 좋다. 배경 음악이 잔잔해 소음이 적으며, 조용히 이야기 나누기에 적합한 분위기다. 단체 좌석은 없으나 2~4인 소그룹 모임에 적합하다.",
  "attributes": {
    "category": "카페",
    "parking": false,
    "wifi": true,
    "noise_level": "조용함",
    "seating_type": ["개인석"],
    "outdoor": false,
    "reservation": null,
    "price_range": "1인 7,000–12,000원",
    "operating_hours": "09:00–22:00"
  },
  "source": {
    "type": "hand_crafted",
    "author": "junsik",
    "verified_at": "2026-05-28",
    "reference": "현장 방문 확인",
    "notes": "홍대 상권 파이프라인 테스트용 첫 번째 시드"
  }
}
```

---

## 4. CSV 스키마 초안 (플랫 구조)

벡터 DB 외에 스프레드시트로 시드를 관리할 때 사용하는 플랫 구조.

```
place_id, name, address, latitude, longitude, atmosphere_text,
attr_category, attr_parking, attr_wifi, attr_noise_level,
attr_seating_type, attr_outdoor, attr_reservation,
attr_price_range, attr_operating_hours,
source_type, source_author, source_verified_at, source_reference, source_notes
```

- `attr_seating_type`은 쉼표로 구분된 문자열 (예: `"개인석,단체석"`).
- `null` 값은 빈 셀.

---

## 5. atmosphere_text 작성 기준

`atmosphere_text`는 벡터 검색의 직접적인 대상이다. 품질이 검색 정확도를 결정한다.

### 좋은 atmosphere_text의 조건

| 조건 | 예시 |
|------|------|
| 검색 매칭 표현 포함 | "조용함", "대화하기 좋음", "좌석 간격 넓음", "단체석 있음" |
| 구체적인 분위기 묘사 | "소규모 모임에 적합", "카운터석이 있어 혼자 방문하기에도 좋음" |
| 감각적 서술 | "배경음악이 잔잔하고 조명이 따뜻함", "통유리창으로 자연광이 많이 들어옴" |
| 사용 맥락 | "2~4인 소그룹", "업무 미팅", "친구 모임" |

### 피해야 할 atmosphere_text

| 피해야 할 것 | 이유 |
|-------------|------|
| "카페입니다" | 카테고리 나열. 검색 매칭 근거 없음 |
| "맛있는 커피를 팝니다" | 분위기와 무관한 정보 |
| LLM이 생성한 분위기 묘사 | 실재 장소 정보가 아님. 검수 불가 |
| 50자 미만 짧은 서술 | 임베딩 품질 저하 |

### atmosphere_text 최소 길이

50자 이상을 권장한다. 구체적인 묘사가 많을수록 검색 품질이 높아진다.

---

## 6. 좌표 메타데이터의 역할

좌표는 두 가지 목적으로 사용된다.

1. **거리 점수 계산**: 중간지점과 각 시드 사이의 Haversine 거리를 계산해 정규화 점수로 변환한다.
2. **지도 표시**: 추천 결과를 카카오맵에 핀으로 표시할 때 사용한다.

**중요**: 좌표는 카카오 로컬 API로 검증하거나 현장 확인을 통해 정확성을 보장한다.

---

## 7. 데이터 파일 위치

```
data/seeds/raw/          # 원본 시드 파일 (커밋됨)
  ├── hongdae.json       # 홍대 상권 시드 (예시)
  └── gangnam.json       # 강남 상권 시드 (예시)

data/seeds/processed/    # 임베딩 준비 완료 레코드 (커밋됨)
  └── venues.json        # 전체 정규화 레코드 (통합 파일 또는 상권별 분리)

data/chroma/             # 로컬 Chroma 인덱스 (커밋 금지)
```

---

## 8. MVP 시드 계획

| 단계 | 상권 | 시드 수 |
|------|------|---------|
| MVP 시작 | 서울 핵심 상권 1곳 (홍대 또는 강남 등) | 20–30개 |
| MVP 확장 | 핵심 상권 4–5곳 | 100–150개 |
| 이후 | 추가 상권 | 미정 |

파이프라인을 끝까지 돌려본 뒤 시드를 확장한다. 처음부터 150개를 만드는 것보다 20–30개로 파이프라인을 완성하는 것이 더 중요하다.

---

## 9. 크롤링 제외 원칙

- 크롤링은 사용하지 않는다. 약관 위반·차단·유지보수 리스크를 회피한다.
- 장소·좌표 데이터는 카카오 로컬 API만 사용한다.
- 분위기 서술 텍스트는 실재 장소를 확인한 뒤 사람이 직접 작성하고 검수한다.

상세 정책 → [`data-policy.md`](../references/data-policy.md)
