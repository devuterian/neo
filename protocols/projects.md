# Project protocol

## 계층

```text
project
└── milestone
    └── task
```

세 단위 모두 UUID를 가진다.

- 프로젝트 JSON: `data/projects/<english-slug>.json`
- 프로젝트 제목은 사람이 읽는 현재 이름이다.
- slug는 영문 소문자, 숫자, 하이픈만 사용한다.
- 프로젝트 제목을 바꿔도 UUID는 유지한다.
- slug를 바꿀 때는 `neoctl project rename --slug ... --approve`를 사용한다.

## 프로젝트 상태

```text
draft / active / waiting / paused / complete / cancelled
```

- `draft`: 정의나 수락이 끝나지 않음
- `active`: 현재 진행 가능
- `waiting`: 외부 주체 때문에 멈춤
- `paused`: 사용자 자신의 사유 때문에 멈춤
- `complete`: 완료 조건 충족
- `cancelled`: 완료하지 않고 종료

`waiting`은 `waiting.on`을 필수로 기록한다. `paused`는 `pause.reason`을 필수로 기록한다.

## 마일스톤

마일스톤 상태:

```text
planned / active / complete / cancelled
```

- 현재 마일스톤은 프로젝트마다 최대 하나다.
- `remaining_effort`는 0.5 단위의 예상 작업량이다.
- 실제 작업시간과 자동 환산하지 않는다.
- 날짜는 프로젝트 JSON에 기록하지 않는다.
- Calendar event ID만 `calendar_event_id`에 연결한다.

작업 종료 후 Hermes는 결과와 완료 조건을 비교해 새 `remaining_effort`를 제안한다. 사용자가 승인하면 다음 명령을 실행한다.

```bash
neoctl milestone effort PROJECT MILESTONE VALUE --approve
```

## 태스크

태스크 목록 조회:

```bash
neoctl task list [--project PROJECT] [--status todo|in_progress|waiting|done|cancelled]
```

태스크는 todolist의 영구 항목이다.

```text
todo / in_progress / waiting / done / cancelled
```

- 태스크는 하나의 마일스톤에 속한다.
- 여러 생활일에서 같은 `task_id`를 참조할 수 있다.
- 하루 계획에 넣었다고 태스크 상태를 자동 완료하지 않는다.
- 체크인하면 `in_progress`가 된다.
- 체크아웃 때 실제 결과에 따라 `in_progress`, `waiting`, `done` 중 하나로 기록할 수 있다.
- 날짜는 태스크에 저장하지 않는다.

## 프로젝트 조회

```bash
neoctl project list                   # 모든 프로젝트 목록
neoctl project show PROJECT           # 특정 프로젝트 상세 (slug 또는 UUID)
```

## 프로젝트 생성

1. 프로젝트 제목과 영문 slug를 확인한다.
2. 범위와 설명을 정리한다.
3. 생성안을 보여준다.
4. 승인 후 실행한다.

```bash
neoctl project create --title "..." --slug ... --approve
```

5. 마일스톤 제목과 최초 예상 작업량을 제안한다.
6. 승인 후 마일스톤을 만든다.
7. 필요한 태스크를 todolist로 추가한다.
8. Calendar 이벤트 생성안은 `protocols/calendar.md`에 따라 별도로 승인받는다.

## 오늘 태스크 선택

- 기본적으로 한 태스크를 추천한다.
- `workday_capacity`가 1이고 두 프로젝트를 나눌 이유가 있으면 0.5씩 두 태스크를 계획할 수 있다.
- 사용자가 선택하기 전에는 하루 계획을 확정하지 않는다.
- 하루 JSON에는 UUID와 당시 제목 snapshot을 함께 저장한다.

## 작업 시작

1. 태스크 결과와 첫 행동을 짧게 확인한다.
2. `neoctl work check-in TASK_UUID`를 실행한다.
   - `--project PROJECT`로 프로젝트 지정 가능
   - `--at ISO_DATETIME`으로 체크인 시각 명시 가능
3. 열린 작업 세션은 전체 시스템에서 하나만 허용한다.

## 체크아웃

1. 실제로 한 일
2. 막힌 점
3. 태스크 상태
4. 다음 첫 행동
5. 남은 작업량 재검토

을 확인한다.

```bash
neoctl work check-out [--at ISO_DATETIME] [--task-status done|in_progress|waiting] [--waiting-on "..."] [--note "..."]
```

`--task-status waiting`일 때는 `--waiting-on`으로 대기 사유를 기록한다.

남은 작업량은 같은 명령에서 자동 변경하지 않는다. 별도 제안과 승인을 거친다.

## 정정·삭제와 typed mutation

프로젝트와 nested milestone/task는 parent project domain을 통해서만 조작한다. raw JSON, 파일 경로, JSON Pointer를 mutation 입력으로 받지 않는다.

- neoctl resource update project PROJECT --field description --value "..."는 일반 변경이다.
- neoctl resource correct project PROJECT --field title --value "..." --reason "..."는 기존 기록이 잘못됐을 때의 정정이다. 정정은 before/after와 reason을 결과에 남긴다.
- 삭제는 대상·사유를 확인하고 --confirm을 붙인다. 생활일 계획이나 세션이 참조하는 프로젝트는 삭제하지 않는다.
- project-index는 derived 문서라 직접 update/delete하지 않고 rebuild·validate 경계로만 다룬다.
