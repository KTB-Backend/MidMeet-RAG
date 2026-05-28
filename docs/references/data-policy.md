# Data Policy

> **범위**: 이 문서는 **데이터 정책**(허용 출처·금지 사항·산출물 관리)만 다룬다.
> 시드 레코드 스키마·필드 정의·작성 기준의 **정본**은 [`data-design.md`](../design-docs/data-design.md)다.

## Core Rules

- 크롤링을 사용하지 않는다.
- LLM이 지어낸 분위기 설명을 factual seed data로 저장하지 않는다.
- 추천 문장은 검색된 seed와 메타데이터에 근거해야 한다.
- 생성 결과에 근거가 없는 주장은 넣지 않는다.

위 규칙은 **프로덕션 시드 코퍼스**에 적용된다. 개발/평가용 합성 픽스처는 아래 예외를 따른다.

## Development Fixtures (예외)

- 합성 픽스처는 파이프라인·평가 부트스트랩 **개발/평가 전용**으로만 허용한다.
- `source.type="fixture"`로 명시하고 `data/seeds/fixtures/`에 둔다.
- **프로덕션 코퍼스로 승격하거나 사용자 추천 결과로 노출하지 않는다.**
- 구분 정본 → [`data-design.md`](../design-docs/data-design.md) §10.

## Accepted Sources

- Kakao Local API: 장소명, 주소, 좌표, 실시간 장소 검색.
- 공공데이터: 주차, 와이파이, 좌석, 운영 정보 등 구조화 속성.
- 수제 seed: 실재 장소를 확인한 뒤 사람이 작성하거나 검수한 분위기 설명.

## Seed Record Schema

시드 레코드의 필수 필드·필드 정의·`atmosphere_text` 작성 기준·샘플 JSON은 정본 문서에 있다.
→ [`data-design.md`](../design-docs/data-design.md)

## Generated Data

Chroma index, SQLite 파일, 모델 출력 샘플, 다운로드한 모델 가중치는 기본적으로 커밋하지 않는다. 재현 가능한 원천 seed와 평가 fixture만 버전 관리한다.
