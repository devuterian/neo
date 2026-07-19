# Neo

**생활 기록과 프로젝트를 한 흐름으로 관리하는, 내 데이터 중심의 개인 작업공간.**

Neo는 자정 대신 `기상`으로 하루를 나누고, 생활 기록·프로젝트·할 일·병원 일정을 JSON으로 보관하는 Python CLI야. 직접 명령어로 써도 되고 Hermes Agent와 Telegram을 연결해 자연어로 기록할 수도 있어.

## 주요 기능

- 기상부터 다음 기상까지 이어지는 생활일
- 식사, 외출, 수면, 낮잠, 기분, 약 복용 기록
- 프로젝트 → 마일스톤 → 태스크와 실제 작업 세션
- pending과 날짜 없는 someday 분리
- 여러 병원·치료 항목의 독립적인 반복 주기 관리
- 냉장고와 민감 기록의 분리 보관
- Google Calendar 연동 구조
- Hermes Agent·Telegram에서 제한된 조회와 기록

## 설치

Python 3.11 이상과 Git이 필요해.

```bash
git clone https://github.com/devuterian/neo.git
cd neo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
neoctl init
neoctl validate
```

`neoctl init`은 로컬 전용 `config/app.json`, 빈 `data/`, `brief.md`를 만든다. 이 파일들은 기본적으로 Git에 올라가지 않아.

## 빠른 사용법

```bash
# 하루 시작과 종료
neoctl day wake
neoctl day sleep

# 약 기록: 특정 약은 기본값으로 정해져 있지 않다
neoctl day med take --name "약 이름" --dose "복용량"

# 프로젝트
neoctl project create --title "샘플 프로젝트" --slug sample --approve

# 여러 병원 주기
neoctl medical add \
  --provider "샘플 치과" \
  --title "정기 검진" \
  --at 2026-07-20 \
  --cycle-days 180

neoctl medical add \
  --provider "샘플 의원" \
  --title "추적 진료" \
  --at 2026-07-20 \
  --cycle-days 30

neoctl medical list
neoctl medical record MEDICAL_ID
```

병원 기록은 일회성 진료도 저장할 수 있어. 반복 일정이 없는 경우 `--cycle-days`를 생략하면 된다. 각 항목의 마지막 날짜와 주기는 서로 독립적으로 계산된다.

## 데이터와 개인정보

실제 사용자 데이터는 다음 경로에 생기며 공개 저장소에서는 기본적으로 무시된다.

- `data/`
- `brief.md`
- `config/app.json`
- `.env`와 인증 파일

개인 데이터를 Git으로 동기화하려면 반드시 별도의 비공개 저장소를 사용해. 공개 저장소에 기존 데이터나 Git 이력을 합치지 않는 것을 권장한다.

## Hermes와 Telegram

Hermes는 Neo의 주요 사용 방식 중 하나지만 필수는 아니야. 연결하면 `neoctl`을 고정된 작업공간에서 호출해 생활일과 프로젝트를 자연어로 다룰 수 있다.

공개판은 특정 사용자 이름, Telegram ID, 서버 경로를 내장하지 않는다. 사용자 이름·작업공간 경로·허용 사용자 ID는 배포 환경에서 직접 설정해야 한다. 자세한 원칙은 [`integrations/hermes-agent/README.md`](integrations/hermes-agent/README.md)를 참고해.

## 기본 설정

- 기본 시간대: `Asia/Seoul` (설정 가능)
- 기본 언어와 문서: 한국어
- 생활일 경계: 자정이 아니라 다음 기상
- 일정 정본: Google Calendar

## 개발

```bash
python -m pip install -e '.[dev]'
pytest -q
```

## 라이선스

[MIT](LICENSE)
