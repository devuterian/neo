# Changelog policy

`CHANGELOG.md`는 Git 커밋 전체를 나열하는 로그가 아니다. neo의 사용자, 운영자, 후속 개발자가 알아야 할 의미 있는 변경을 선별해 기록한다.

## 기록 대상

다음 중 하나에 해당하면 기본적으로 `CHANGELOG.md`의 `Unreleased`를 갱신한다.

- 새 기능 또는 기존 기능의 사용자 가시적 확장
- CLI 명령, 옵션 위치, 종료 코드 또는 JSON 응답 계약 변경
- 데이터 모델, schema, migration 또는 저장 구조 변경
- 파생 데이터 생성 방식과 정본 경계 변경
- 보안, 개인정보 보호, 승인 또는 공개 범위 변경
- 사용자가 체감할 수 있는 버그 수정
- 호환성, deprecated 기능 또는 제거된 기능
- 운영자가 수행해야 하는 설치, 설정 또는 마이그레이션 절차
- 큰 내부 리팩터링 중 공개 계약이나 유지보수 경계를 명확히 고정한 변경

## 기록하지 않는 대상

다음은 저장소에서 version-control되더라도 changelog 항목으로 만들지 않는다.

- `data/days/`의 일상적인 생활 기록
- `data/projects/`의 일반적인 진행 상태 갱신
- `data/message-log/`의 대화 로그
- `data/indexes/`의 자동 생성 index
- 자동 생성된 `brief.md`와 `export/`
- 식사, 기상, 취침, 약 복용, medical 실행 등 개인 운영 기록
- 단순 timestamp 또는 generated-at 변경
- 의미 없는 formatting, typo 또는 내부 이름 정리

운영 데이터가 version-control 대상이라는 정책과 changelog 기록 대상 여부는 별개다. 운영 데이터는 저장소에 계속 커밋하되 제품·구조 변경 changelog에는 복사하지 않는다.

## 작성 형식

- 아직 release되지 않은 변경은 `## Unreleased`에 적는다.
- 가능한 경우 `Added`, `Changed`, `Fixed`, `Security / Privacy`, `Deprecated`, `Removed` 중 적절한 분류를 사용한다.
- 각 항목에는 관련 PR 번호를 붙여 추적 가능하게 한다.
- 구현 파일 목록보다 사용자 또는 운영 관점의 결과를 설명한다.
- 호환성을 유지한 리팩터링은 무엇이 바뀌고 어떤 계약이 유지됐는지 함께 적는다.
- release 시 `Unreleased` 내용을 버전과 날짜가 있는 섹션으로 이동하고 빈 `Unreleased`를 다시 만든다.

## 개인정보 보호

비공개 저장소라도 changelog에는 다음 내용을 복사하지 않는다.

- 실제 message-log 또는 DM 원문
- private spark 기록
- 생활일 note와 작업 note 원문
- 실제 주소, 계좌, 세금, credential, token 또는 `.env` 값
- 개인 일정과 프로젝트의 불필요한 구체적 원문

변경을 설명하는 데 예시가 필요하면 실데이터 대신 일반화된 용어를 쓴다.

## PR 절차

기능·구조·보안 PR은 다음 중 하나를 수행한다.

1. `CHANGELOG.md`의 `Unreleased`를 갱신한다.
2. changelog가 필요 없다면 PR 본문에 이유를 적는다.

PR 템플릿의 changelog 체크 항목은 이 판단을 누락하지 않기 위한 장치다. 문서만 변경하는 PR도 향후 사용자 행동이나 운영 정책을 바꾼다면 changelog 대상이 될 수 있다.

## ChatGPT와 Codex의 역할 분리

이 프로젝트에서는 구현과 로컬 검증에 Codex를 사용할 수 있지만, changelog 초안과 문서 PR은 ChatGPT의 GitHub 작업 흐름에서 관리할 수 있다.

권장 흐름은 다음과 같다.

1. Codex는 구현 PR의 테스트, validation 및 merge 결과를 보고한다.
2. 사용자가 merge 결과를 ChatGPT에 전달한다.
3. ChatGPT는 merged PR의 설명, diff, 검증 결과를 근거로 `Unreleased`를 갱신하고 필요한 정책 문서를 별도 PR로 만든다.
4. ChatGPT는 운영 데이터 원문을 changelog에 포함하지 않고, 문서 PR을 자동으로 merge하지 않는다.

이 역할 분리는 Codex 토큰을 구현과 검증에 집중시키기 위한 운영 선택이다. changelog의 품질 기준과 검토 절차 자체는 동일하게 유지한다.
