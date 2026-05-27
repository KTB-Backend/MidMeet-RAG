# RAG Evaluation

## Purpose

평가는 웹 UI 품질이 아니라 RAG 하네스가 올바른 후보를 찾고, 거리 제약을 반영하고, 근거 기반으로 답하는지 확인하는 데 집중한다.

## Evaluation Layers

1. **Seed validation**: 필수 필드, 좌표 범위, 출처, 분위기 텍스트 길이를 검사한다.
2. **Retrieval**: 질의와 의미적으로 맞는 장소가 상위 후보에 나타나는지 확인한다.
3. **Hybrid scoring**: 분위기 점수와 거리 점수가 최종 순위에 기대대로 반영되는지 확인한다.
4. **Generation**: 추천 이유가 검색된 seed 근거 안에 머무는지 확인한다.

## Required Test Queries

초기 fixture에는 다음 유형을 포함한다.

- "조용히 이야기하기 좋은 카페"
- "단체로 앉기 좋은 식당"
- "역에서 너무 멀지 않은 저녁 장소"
- "분위기는 좋지만 너무 시끄럽지 않은 곳"

## Metrics To Track

- top-k 후보의 seed ID와 장소명.
- semantic score, distance score, final score.
- 후보와 중간지점 사이 거리.
- 생성 문장별 근거 seed ID.
- 근거 없는 claim 수.

## Pass Criteria

하네스 실행 결과는 같은 fixture에서 재현 가능해야 한다. 검색 결과는 점수 구성요소를 출력해야 하며, 생성 결과는 근거 seed를 함께 노출해야 한다. 모델 품질이 애매한 경우에도 환각을 허용하지 않는다.
