# Architecture

## Goal

이 프로젝트의 1차 목표는 웹앱이 아니라 RAG 파이프라인 하네스다. 구현은 "시드 데이터 -> 임베딩 -> Chroma 저장 -> 하이브리드 스코어링 -> 근거 기반 추천 생성" 흐름을 독립적으로 실행하고 검증할 수 있어야 한다.

## Pipeline

1. **Seed loading**: `data/seeds/processed/`의 장소 단위 레코드를 읽는다.
2. **Seed validation**: 필수 필드, 좌표, 출처, 분위기 텍스트 품질을 검사한다.
3. **Embedding**: 한국어 임베딩 모델로 분위기 텍스트를 벡터화한다.
4. **Indexing**: 벡터와 메타데이터를 Chroma에 저장한다.
5. **Querying**: 사용자 조건을 임베딩하고 후보를 검색한다.
6. **Hybrid scoring**: 분위기 유사도와 거리 점수를 정규화해 가중합한다.
7. **Generation**: 검색된 seed 근거만 사용해 추천 이유를 생성한다.

## Module Boundaries

- `packages/rag_core/`: RAG 핵심 로직. API나 UI에 의존하지 않는다.
- `apps/rag_api/`: 나중에 추가할 얇은 API 계층. `rag_core`를 호출만 한다.
- `scripts/`: 하네스 실행 진입점. 인덱싱, 단일 쿼리, 평가 실행을 담당한다.
- `evals/`: 느리거나 모델 의존적인 검증 케이스를 둔다.

## Configuration

모델명, Chroma 경로, Kakao API 키, 검색 개수, 거리 반경, 분위기/거리 가중치는 환경변수나 설정 파일로 주입한다. 비즈니스 로직에 하드코딩하지 않는다.

## Non-Goals For Now

협업 세션, 지도 UI, 상권 클러스터링, 대중교통 시간 기반 최적화는 RAG 하네스가 안정화된 뒤 진행한다.
