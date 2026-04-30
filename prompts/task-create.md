# Task 생성 가이드

## 구조

```
tasks/{task-name}/
├── index.json        # 태스크 메타데이터
├── phase-01.md       # Phase 1 프롬프트
├── phase-02.md       # Phase 2 프롬프트
└── ...
```

## index.json 형식

```json
{
  "name": "task-name",
  "description": "태스크 설명",
  "total_phases": 11,
  "current_phase": 0,
  "status": "pending",
  "error_message": null,
  "blocked_reason": null,
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

### status 값
- `pending`: 아직 시작 안 함
- `in_progress`: 실행 중
- `completed`: 모든 phase 완료
- `failed`: phase 실행 중 오류
- `blocked`: 사용자 개입 필요

## phase-NN.md 형식

각 phase 파일은 AI 에이전트가 실행할 자기완결적 프롬프트여야 한다.

```markdown
# Phase N: 제목

## 목표
이 phase가 완료되면 달성되는 것.

## 컨텍스트
- 참조해야 할 설계 문서 경로
- 이전 phase에서 생성된 파일/구조

## 구현 항목
구체적인 구현 목록. 파일 경로 포함.

## 검증
이 phase 완료를 확인하는 방법.
- 실행 커맨드
- 예상 결과
```

## 규칙
1. 각 phase는 독립적으로 실행 가능해야 한다 (이전 phase 결과물 위에서).
2. phase 프롬프트에 설계 문서 경로를 명시해서 에이전트가 참조할 수 있게 한다.
3. 검증 항목은 자동화 가능한 형태 (커맨드 + 예상 결과)로 작성한다.
4. 크레덴셜은 .env에서 읽도록 하고, phase 프롬프트에 실제 값을 넣지 않는다.
