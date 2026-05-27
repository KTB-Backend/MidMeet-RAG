# Agent Workflow

## Before Editing

1. [`project-brief.md`](../product-specs/project-brief.md)와 `AGENTS.md`를 먼저 확인한다.
2. 작업이 RAG 하네스 우선순위에 맞는지 판단한다.
3. 애플리케이션 코드가 필요한 요청인지, 문서/테스트/하네스 작업으로 충분한지 구분한다.

## Implementation Order

파이프라인 구현 순서의 **정본**은 [`rag-design.md`](../design-docs/rag-design.md) §7이다. 이전 단계가 안정되기 전 다음 단계로 넘어가지 않는다.

## Working Rules

- Python 구현은 `packages/rag_core/`에 먼저 둔다.
- API 코드는 `rag_core`를 호출만 하게 한다.
- 크롤링 코드를 만들지 않는다.
- LLM 출력물을 factual seed로 저장하지 않는다.
- 새 동작에는 테스트나 평가 fixture를 함께 추가한다.
- 변경 후 실행한 명령과 확인 결과를 남긴다.

## Done Checklist

- 문서화된 실행 명령이 있다.
- 결정적 로직은 `pytest`로 검증된다.
- retrieval 결과에 semantic, distance, final score가 보인다.
- generation 결과에 근거 seed가 연결된다.
- `.env`, Chroma index, 모델 가중치, 임시 산출물이 커밋되지 않는다.
