# Someday protocol

`someday`는 날짜에 귀속되지 않고, 하지 않아도 문제가 없는 선택적 후보 목록이다.

## 조회

실제 요청에서 `#나중에`, `#나중에 뭐 있었지?`, `나중에 목록 보여줘`, `심심한데 나중에 해볼 것 뭐 있어?`를 사용하면 `neoctl someday list`를 실행한다. 코드 블록, 인용문, 설명 속 문자열은 트리거가 아니다.

## 추가

`#나중에 새로 생긴 카페 가보기`, `이 영화 나중에 볼 목록에 넣어줘`, `언젠가 Blender Geometry Nodes 공부해보기`처럼 명시적으로 요청하면 제목에서 `#나중에` 토큰을 제거하고 `neoctl someday add`로 저장한다. 설명이 있으면 `--description`을 사용한다.

납부·제출·갱신·예약·신고·약속한 후속 조치·업무 납품·건강상 필요한 조치·명시적 기한·미실행 시 손해가 있는 항목은 저장 전에 정확히 한 번 묻는다: `이건 #나중에보다 꼭 해야 하는 일에 가까워 보여. someday로 둘까, pending으로 넣을까?`

사용자가 `someday`, `#나중에`, `나중에로`를 고르면 someday에, `pending`, `밀린 일`, `해야 할 일로`를 고르면 pending에 저장한다. 선택이 없으면 저장하지 않으며 양쪽에 동시에 저장하지 않는다.

## 낮은 적극성

명시적으로 요청받을 때만 조회한다. 기상·취침 점검, 알림, `brief.md`, pending 목록, 일반 상태 보고, trusted-group projection에는 자동 노출하지 않는다. 완료되지 않은 항목을 `밀린 일`이라고 부르지 않는다.

## Trusted Telegram group

자동 projection에는 someday를 포함하지 않는다. 허용된 trusted Telegram group에서는 메시지에 독립된 `#나중에` 토큰이 실제 요청으로 명시된 경우에만 someday 조회·추가와 pending 분류·추가를 허용한다. 토큰은 위치와 무관하지만 code, pre, blockquote, expandable blockquote, 과거 발언 인용, `abc#나중에`, `#나중에목록`, 설명 문맥은 실행 트리거가 아니다. 허용되지 않은 group, DM, channel, bot message도 처리하지 않는다.

선택적 항목은 바로 someday에 저장한다. 납부·제출·갱신·예약·신고·약속한 후속 조치·업무 납품·건강상 필요한 조치·명시적 기한·미실행 시 손해가 있는 항목처럼 의무성이 명백하면 저장 전에 정확히 한 번 `이건 #나중에보다 꼭 해야 하는 일에 가까워 보여. someday로 둘까, pending으로 넣을까?`라고 묻는다. 질문 전에는 어느 store도 수정하지 않는다. `someday`와 `pending`에 같은 항목을 동시에 기록하지 않는다.

저장 대상 workspace와 subject는 항상 `owner`다. 친구의 `내`, `나` 항목은 바로 저장하지 말고 누구 항목인지 한 번 확인한다. trusted group에서는 done·undo·remove와 그 밖의 mutation을 노출하지 않는다.
