# Calendar protocol

## 정본

Google Calendar가 다음 날짜의 유일한 정본이다.

- 외부 일정
- 마일스톤 날짜
- 최종 납기 날짜와 시각
- 예정 작업 일정

프로젝트 JSON에는 날짜를 넣지 않는다.

```json
{
  "deadline_calendar_event_id": "google-event-id",
  "milestones": [
    {
      "calendar_event_id": "google-event-id"
    }
  ]
}
```

## Calendar 구분

### 개인 Calendar

- 읽기 전용
- 외부 일정
- 토마토 event color는 작업에 영향을 줄 가능성이 높은 신호
- 토마토가 아니어도 실제 시간을 차지하면 설명에 포함할 수 있음

### 프로젝트용 Calendar

- 마일스톤
- 최종 납기
- 예정 작업 일정
- 사용자 승인 후 쓰기

## `data/indexes/calendar.json`

최근 조회 결과를 정규화한 파생 index다.

- 삭제 후 재생성 가능해야 한다.
- `source.fetched_at`을 반드시 기록한다.
- 연결 실패 시 기존 이벤트를 최신이라고 간주하지 않는다.
- 실패 상태에서도 마지막 캐시는 보존할 수 있다.

현재 index 조회:

```bash
neoctl calendar show
```

조회 결과 반영:

```bash
neoctl calendar refresh                  # Google API로 직접 fetch + import
neoctl calendar import-index --input /tmp/calendar-index.json  # 수동 import (외부 스크립트 결과)
```

연결 실패:

```bash
neoctl calendar mark-unavailable --error "..."
```

## 이벤트 연결

마일스톤 이벤트 생성이 성공하면 반환된 event ID를 연결한다.

```bash
neoctl milestone link-calendar PROJECT MILESTONE --event-id EVENT_ID
```

최종 납기:

```bash
neoctl project link-deadline PROJECT --event-id EVENT_ID
```

이 연결 명령은 날짜를 복사하지 않는다.

## 이벤트 메타데이터

가능하면 이벤트 private metadata를 사용한다. 불가능하면 설명에 JSON 블록을 넣는다.

```text
--- NEO-META-BEGIN ---
{"schema":1,"event_type":"milestone","project_id":"...","milestone_id":"...","task_id":null,"day_id":null}
--- NEO-META-END ---
```

이벤트 유형:

```text
milestone / deadline / work_plan / external
```

제목만으로 영구 연결을 판정하지 않는다.

## 승인

조회는 자동으로 실행할 수 있다.

다음 작업은 변경안을 보여주고 승인받은 뒤 실행한다.

- 마일스톤 생성·이동·삭제
- 최종 납기 생성·이동·삭제
- 예정 작업 일정 생성·이동·삭제

최종 납기 이동은 반드시 명시적으로 확인한다.

## 변경 감지

연결된 이벤트가 수동으로 이동되면 이전값과 현재값을 보여주고 이유를 묻는다. 현재 날짜는 Calendar에만 둔다. 이유가 중요한 결정이면 프로젝트 `decisions`에 기록한다.

이벤트가 사라지면 마일스톤이나 프로젝트를 삭제하지 않는다. 연결 끊김을 보고하고 재연결 또는 재생성을 제안한다.

## 중복 방지

이벤트 생성 전에 다음 순서로 확인한다.

1. 저장된 Google event ID
2. NEO metadata의 UUID
3. 같은 Calendar의 유사한 날짜·제목·유형 후보
4. 기존 이벤트가 있으면 재연결 제안
