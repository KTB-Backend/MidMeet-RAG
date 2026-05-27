# Data Policy

## Core Rules

- 크롤링을 사용하지 않는다.
- LLM이 지어낸 분위기 설명을 factual seed data로 저장하지 않는다.
- 추천 문장은 검색된 seed와 메타데이터에 근거해야 한다.
- 생성 결과에 근거가 없는 주장은 넣지 않는다.

## Accepted Sources

- Kakao Local API: 장소명, 주소, 좌표, 실시간 장소 검색.
- 공공데이터: 주차, 와이파이, 좌석, 운영 정보 등 구조화 속성.
- 수제 seed: 실재 장소를 확인한 뒤 사람이 작성하거나 검수한 분위기 설명.

## Seed Record Expectations

각 seed는 식당이나 카페 한 곳을 나타낸다. 최소 필드는 다음을 기준으로 한다.

- `place_id`: 내부 식별자.
- `name`: 장소명.
- `address`: 주소 또는 행정구역.
- `latitude`, `longitude`: 거리 계산용 좌표.
- `atmosphere_text`: 의미 검색 대상이 되는 분위기 설명.
- `attributes`: 주차, 와이파이, 좌석, 소음, 예약 등 구조화 속성.
- `source`: 출처, 작성자, 확인일 등 provenance.

## Atmosphere Text

좋은 seed는 "조용함", "대화하기 좋음", "좌석 간격", "단체석", "분위기"처럼 사용자 질의와 매칭될 표현을 포함한다. 단순 카테고리 나열은 검색 품질을 떨어뜨린다.

## Generated Data

Chroma index, SQLite 파일, 모델 출력 샘플, 다운로드한 모델 가중치는 기본적으로 커밋하지 않는다. 재현 가능한 원천 seed와 평가 fixture만 버전 관리한다.
