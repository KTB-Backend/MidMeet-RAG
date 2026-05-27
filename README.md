# MidMeet-RAG

"어디서 만날래?"는 여러 사람의 출발 위치와 자연어 분위기 조건을 바탕으로 모임 장소를 추천하는 RAG 기반 사이드 프로젝트입니다.

현재 목표는 웹앱 구현보다 RAG 파이프라인 하네스를 먼저 구축하는 것입니다.

```text
seed data -> embedding -> Chroma storage -> hybrid scoring -> grounded recommendation generation
```

## Current Focus

- 실재 장소 기반 seed 데이터 구조화.
- 한국어 분위기 텍스트 임베딩.
- Chroma 저장과 메타데이터 보존.
- 분위기 유사도와 거리 점수의 하이브리드 스코어링.
- 검색된 seed 근거에 제한된 추천 생성.

## Repository Map

- `docs/project-brief.md`: 프로젝트 기획과 설계 원칙.
- `docs/architecture.md`: RAG 하네스 아키텍처.
- `docs/data-policy.md`: seed 데이터와 출처 정책.
- `docs/rag-evaluation.md`: 검색, 스코어링, 생성 평가 기준.
- `docs/agent-workflow.md`: Codex 작업 순서와 완료 기준.
- `docs/prompts/recommendation-system.md`: 근거 기반 추천 생성 프롬프트.
- `packages/rag_core/`: 향후 RAG 핵심 로직 위치.
- `apps/rag_api/`: 향후 API 계층 위치.
- `data/seeds/`: seed 원천 및 처리 데이터 위치.

## Non-Negotiable Rules

- 크롤링을 사용하지 않습니다.
- LLM이 만든 분위기 설명을 factual seed data로 저장하지 않습니다.
- 추천 결과는 검색된 seed evidence에 기반해야 합니다.
- RAG 로직은 API 코드와 분리합니다.

## Planned Local Flow

아직 Python 구현 코드는 없습니다. 구현이 추가되면 다음 형태의 명령을 기준으로 정리합니다.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pytest tests/
python -m scripts.index_seeds
python -m scripts.query_harness
```

자세한 구현 순서는 `AGENTS.md`와 `docs/agent-workflow.md`를 따릅니다.
