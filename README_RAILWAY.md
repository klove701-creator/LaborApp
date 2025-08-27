# Railway 배포 가이드 (노무비 관리 시스템)

이 저장소는 Flask + Gunicorn + (선택)PostgreSQL 구성으로 **Railway**에 쉽게 배포할 수 있도록 준비되어 있습니다.
현재 프로젝트에는 `Procfile`/`requirements.txt`가 포함되어 있어 Docker 없이도 바로 배포가 가능합니다.

## 빠른 배포 (가장 쉬움)

1. GitHub에 이 폴더를 새 저장소로 올립니다.
2. [Railway](https://railway.app) 접속 → **New Project** → **Deploy from GitHub Repo** → 방금 올린 저장소 선택.
3. 자동으로 Python 빌드가 감지되고 `Procfile`(`web: gunicorn app:app --bind 0.0.0.0:$PORT`)로 실행됩니다.
4. **Variables**에서 아래 환경변수를 추가하세요.
   - `SECRET_KEY`: 안전한 임의 문자열
   - (선택) `CORS_ORIGINS`: `*` 또는 본인 도메인
5. **Deploy**가 끝나면 제공된 URL로 접속하여 동작을 확인합니다.

> ⚠️ 현재 소스는 메모리/로컬 파일 기반 데이터라 재배포 시 초기화될 수 있습니다. 운영에서는 **PostgreSQL 플러그인 추가**를 권장합니다.

## PostgreSQL 추가(권장)

1. Railway 프로젝트 화면 → **Plugins** → **PostgreSQL** 추가.
2. 추가 후 **Variables**에 `DATABASE_URL`이 자동 주입됩니다.
3. 앱 코드에서 `os.getenv("DATABASE_URL")`이 있을 경우 DB를 사용하도록 분기하세요. (예시 패치 아래 참고)

## HTTPS 및 프록시 처리

Railway는 기본적으로 HTTPS 프록시 뒤에 있으므로 Flask에 `ProxyFix`를 적용하는 것이 좋습니다.

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
```

세션 쿠키 보안 설정도 권장합니다.

```python
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
```

## .env 사용 (로컬)

개발용으로는 `.env.example`를 `.env`로 복사해서 값을 채우고, `python-dotenv`를 사용하세요.

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()
```

## Gunicorn 튜닝

`gunicorn.conf.py`에서 워커/스레드를 조절할 수 있습니다. 기본은 2 워커, 4 스레드입니다.

## Zero‑Downtime 운영 체크리스트

- [ ] `SECRET_KEY` 환경변수로 교체
- [ ] Admin 계정/비밀번호 하드코딩 제거 → DB로 이전
- [ ] 데이터 저장: PostgreSQL 사용으로 전환
- [ ] 로깅: `print` 대신 표준 로깅 사용 및 Railway 로그에서 확인
- [ ] CORS/보안 헤더 점검
- [ ] 백업 정책(Postgres 자동 스냅샷/Export)

## 예시: `app.py` 최소 패치

```python
import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

# HTTPS 프록시 처리
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# JSON 한글, 보안 쿠키
app.config["JSON_AS_ASCII"] = False
if os.getenv("FLASK_ENV") == "production":
    app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE="Lax")
```

> 데이터 영속화를 빠르게 적용하려면, 우선 `projects_data` 같은 큰 딕셔너리를 **JSONB 1레코드**로 저장/로드하는 간단 어댑터를 붙이는 방법이 있습니다. 운영 안정화 후 모델을 테이블로 쪼개세요.
