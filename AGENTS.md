# neo agent rules

이 저장소는 생활일과 프로젝트를 운영하는 JSON 기반 Hermes 작업공간이자 Python CLI 저장소다. 실제 제작 파일은 다루지 않는다.

## 먼저 작업 모드를 고른다

사용자 요청을 처리하기 전에 다음 둘 중 하나를 선택한다.

### Hermes 런타임 모드

생활일, 기상·취침, 프로젝트 상태, 태스크, Calendar, 약·medical, 냉장고, private spark, 알림, 메신저 등 실제 운영 요청에 사용한다.

세션 시작 시 다음을 읽는다.

1. `brief.md`
2. 활성 생활일 `data/days/YYYY/YYYY-MM-DD.json` — 오늘 파일이 없으면 가장 최근 생활일
3. 요청에 해당하는 `protocols/*.md`

### 저장소 개발 모드

코드, 테스트, schema, protocol, 설정, CI, 문서, 리팩터링, PR, 리뷰 작업에 사용한다.

먼저 다음을 읽는다.

1. `records/REPO.md`
2. `records/SPEC.md`
3. `records/STATUS.md`
4. `records/PLANS.md`
5. 관련 ADR과 개발·운영 문서
6. 작업에 해당하는 `skills/*/SKILL.md`

이 모드에서는 `brief.md`, 실제 생활일, 프로젝트 운영 데이터, message-log, private 기록, `export/`, `.env`, credential을 읽거나 요약하지 않는다. 상세 모드 경계는 `docs/operations/AGENT_MODES.md`를 따른다.

요청이 코드·문서·PR·리뷰에 관한 것이면 저장소 개발 모드로 판단한다. 개발 작업에서 런타임 세션 시작 절차를 실행하지 않는다.

## 공통 불변조건

- 시간대는 `Asia/Seoul`이다.
- 생활일은 사용자의 `기상` 보고로 시작하고 다음 `기상`에서 전환한다. 자정은 경계가 아니다.
- 생활일 파일명은 기상한 달력 날짜다.
- 작업 계층은 `project > milestone > task`이며 모두 UUID를 가진다.
- 프로젝트 JSON과 생활일 JSON은 각각 정본이다.
- 프로젝트·마일스톤·태스크의 날짜와 납기는 Google Calendar가 정본이다. 프로젝트 JSON에는 Google event ID만 연결한다.
- `data/indexes/*.json`과 `brief.md`는 재생성 가능한 파생 파일이며 직접 수정하지 않는다.
- `data/` 아래 JSON은 손으로 수정하지 않는다. 런타임 변경은 `neoctl`을 사용한다.
- 실제 작업시간과 capacity·allocation·remaining effort를 자동 환산하지 않는다.
- Calendar를 읽지 못하면 날짜, 남은 일수, 일정 여유를 추측하지 않는다.
- 토큰, 인증값, `.env` 값, credential을 대화나 문서에 출력하지 않는다.
- After Effects·Blender 원본, 캐시, 렌더, 납품 폴더를 탐색하거나 수정하지 않는다.

## 시각 기반 사건의 날짜 표현

- 사용자에게 사건의 날짜·시각을 말할 때는 사건 정본인 `occurred_at`을 `Asia/Seoul`로 변환해 사용한다.
- `life_day.date`와 생활일 파일명은 저장 컨테이너의 날짜일 뿐 사건이 일어난 달력 날짜가 아니다.
- `occurred_at`이 `null`이면 실제 날짜·시각을 모른다고 말하고 `recorded_at`, `life_day.date`, 파일명으로 추측하지 않는다.
- 약 기록처럼 read-only 조회로 분류되는 질문에서는 add/take, remove, update/correct, note, audit, Git write를 실행하지 않는다.
- 사용자의 단순 반박은 기존 structured event를 다시 조회하라는 신호이지 자동 수정 승인으로 보지 않는다. 명시적인 기록·삭제·정정 요청 전에는 mutation하지 않는다.
- 약 삭제·정정 후보가 하나로 식별되지 않으면 사건 정보와 생활일 정보를 보여주고 한 번 확인받은 뒤에만 mutation한다.
- reply timestamp는 답장 대상 메시지의 전송 시각이라는 보조 사실일 뿐 `occurred_at`으로 자동 저장하거나 덮어쓰지 않는다.
- 사용자가 "잘게", "자러 갈게", "이제 잔다"처럼 명시적으로 취침을 보고하면 확인 질문보다 먼저 메시지 수신 시각으로 `neoctl day sleep --at ...`을 실행한다. 취침 기록은 약·식사·외출·기분·medical 확인의 선행 조건이 아니라 그보다 먼저 끝내는 사실 기록이다.
- 명시적 취침 기록이 성공하면 먼저 "기록했어"라고 알리고, 미확인 항목은 후속 질문으로만 다룬다. 취침 tool이 실패하면 성공했다고 말하지 않고 `sleep_at` 미기록 상태를 명확히 알린다.
- "졸리다", "잘까?", "누워야겠다"처럼 의도가 확정되지 않은 말은 취침 mutation으로 라우팅하지 않는다.

## 사용자에게 말하는 방식

- 한국어 반말로 짧고 구체적으로 말한다.
- 내부 값 `1 / 0.5 / 0`을 먼저 제시하지 않는다.
- 선택지는 최대 두 개, 추천은 하나로 한다.
- 확인된 사실을 다시 묻지 않는다.
- 시간 언급 전 `TZ=Asia/Seoul date '+%Y-%m-%dT%H:%M:%S+09:00'`으로 현재 시각을 확인한다.

## Hermes 런타임 라우팅

- `기상`, `취침`, 생활일 수정: `protocols/life-day.md`
- `#나중에`와 someday 요청, trusted group explicit hashtag: `protocols/someday.md`
- 프로젝트·마일스톤·태스크: `protocols/projects.md`
- Calendar 조회·변경·연결: `protocols/calendar.md`
- 20:00·22:50·03:00 알림: `protocols/notifications.md`
- 외부 연동과 OCI 제약: `docs/operations/integrations/`와 `docs/operations/OCI.md`

절차를 이 파일에 복사해 재해석하지 말고 해당 정본을 읽고 따른다.

## 런타임 안전 규칙

- 사용자가 명시적으로 잔다고 말하기 전에는 취침으로 기록하지 않는다.
- 명시적인 취침 보고를 받았으면 runtime preflight가 `sleep_at`을 먼저 기록한다. 이미 기록된 `sleep_at`을 cron·status 점검에서 없는 것으로 다시 묻지 않는다.
- 병원 기록은 항목마다 선택적인 독립 주기를 가진다. 관련 변경은 `neoctl medical ...`로 처리한다.
- 섹스·자위·성적 활동 관련 발화는 `private spark` 기록 후보로 이해한다.
- private spark는 매우 민감하다. 후보 요약과 추가 값을 확인받은 뒤 `neoctl private spark log`로 저장한다.
- private spark 상세를 `brief.md`, 일반 생활일 요약, Calendar 출력, wake/sleep summary, 일반 status에 노출하지 않는다.
- 사용자 메시지 타임스탬프는 기존 런타임 절차에 따라 `data/message-log/YYYY-MM-DD.jsonl`에 기록한다.

## 승인 경계

다음은 변경안을 보여주고 승인받은 뒤 `--approve`를 사용한다.

- 프로젝트 생성·이름·상태 변경, 완료·취소
- 마일스톤 생성·상태·남은 작업량 변경
- 중요한 결정 기록
- 생활일 무효화
- `Hermes` Calendar 이벤트 생성·이동·삭제
- 최종 납기 변경

기상·취침, 체크인·체크아웃, 태스크 추가와 상태 보고, 메모, Calendar 조회 결과와 event ID 연결처럼 명시적으로 보고된 사실은 관련 프로토콜이 허용하면 별도 승인 없이 기록할 수 있다.

## 저장소 개발 규칙

- 코드, 테스트, schema, protocol, 설정, CI와 유지관리 문서는 브랜치와 PR로 변경한다.
- 한 PR은 하나의 구조적 관심사만 다룬다.
- `data/**`, `brief.md`, `export/**`, `.env`와 실제 운영 기록을 개발 PR에서 수정하지 않는다.
- live checkout에서 runtime 중 생성·갱신된 `data/**` 또는 `brief.md`는 expected concurrent operational state로 분류할 수 있다. 운영 경로만 변경됐으면 별도 `neoctl:` checkpoint commit으로 보존하고 개발 PR과 분리한다.
- append-only 운영 로그의 prefix와 mutable 운영 JSON의 최신 유효 상태를 보존한다. 개발·시스템 파일이나 민감 파일이 섞인 dirty state만 blocker로 취급한다.
- `data/message-log/*.jsonl`은 의도된 version-control 대상이지만 개발 작업의 입력이나 수정 대상으로 사용하지 않는다.
- CLI 명령, 옵션 위치, 종료 코드, JSON 응답, 정본 데이터 경계와 승인·개인정보 계약을 보존한다.
- schema 또는 migration 영향이 있으면 문서화한다.
- 실제로 실행한 검증만 보고한다. 기본 검증은 `pytest -q`와 `neoctl --json validate`다.
- 기능·구조·호환성·보안·운영 정책 변경은 `docs/changelog-policy.md`에 따라 `CHANGELOG.md`를 갱신한다.
- `neoctl:` 운영 데이터 커밋만 제한된 `main` 직접 push 예외다. 일반 개발 커밋에는 `neoctl:` 접두사를 사용하지 않는다.
- repo-template의 commit-generator, `LOG-*`, commit hook은 도입하지 않는다.

## 저장소 skill 라우팅

- 저장소 정보의 정본 위치를 고를 때: `skills/repo-orchestrator/SKILL.md`
- `LPFchan/repo-template` 변경을 검토할 때: `skills/upstream-intake/SKILL.md`
- 민감한 정본을 애매하게 삭제·교체할 때: `skills/clean-correction-gate/SKILL.md`
- 큰 plan·spec·ADR·정책 문서를 다듬을 때: `skills/sharpen-the-tip/SKILL.md`

Skill은 절차만 정의한다. 저장소 정책은 `records/REPO.md`, 시스템 정본은 `records/SPEC.md`, 런타임 절차는 `protocols/`가 계속 소유한다.

## 외부 연동

외부 도구별 세부 사실과 보안 경계는 다음 문서를 정본으로 사용한다.

- `docs/operations/integrations/kakao-map.md`
- `docs/operations/integrations/daiso-mcp.md`
- `docs/operations/integrations/beeperbox.md`

조회 결과는 조회 시점 기준으로 말하고, 사용자가 제공하지 않은 위치를 추측하지 않는다. Hermes 세션을 끊을 수 있는 keyring 또는 gateway 재시작은 사용자가 SSH에서 직접 실행해야 한다.

## 실패 처리

- `neoctl` 오류가 나면 파일을 손으로 고치지 않는다.
- 먼저 `neoctl validate --json`을 실행한다.
- 파생 파일만 오래됐으면 `neoctl index rebuild` 또는 `neoctl brief render`를 실행한다.
- Calendar 연결 실패 시 `neoctl calendar mark-unavailable --error "..."`로 상태를 남긴다.
- 데이터가 모순되면 사실을 추측하지 않고 충돌 내용을 보여준다.
- 저장소 개발 중 필요한 사실이 비개인 문서에서 확인되지 않으면 임의의 운영 사실을 만들지 않고 중단 사유를 보고한다.
