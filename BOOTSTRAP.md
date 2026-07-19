# 처음 연결하기

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
neoctl init
neoctl validate
neoctl doctor
```

`neoctl init`은 예시 설정을 복사하고 빈 데이터 구조를 만든다. `config/app.json`에서 시간대와 Calendar ID를 설정할 수 있다. 토큰과 실제 ID는 문서나 공개 저장소에 커밋하지 않는다.

Hermes를 연결할 때는 저장소 경로를 안정된 위치에 두고, Telegram allowlist에는 허용할 사용자 ID만 둔다. Hermes가 실행할 수 있는 도구는 `neoctl`과 필요한 읽기 기능으로 제한하는 것을 권장한다.
