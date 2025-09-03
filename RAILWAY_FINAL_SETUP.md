# Railway 최종 배포 설정

## 🔧 Docker 빌드 오류 해결

### ❌ 문제: `pip: command not found`
```
/bin/bash: line 1: pip: command not found
ERROR: failed to build: failed to solve
```

### ✅ 해결책: Python 프로젝트 구조 정리

#### 1. 핵심 파일들
```
LaborApp/
├── app.py                    # 메인 Flask 앱
├── requirements.txt          # Python 의존성
├── runtime.txt              # Python 버전 지정
├── setup.py                 # Python 프로젝트 설정
├── nixpacks.toml           # Nixpacks 빌드 설정
├── Procfile                 # Railway 실행 명령
└── .env.example            # 환경변수 예시
```

#### 2. 제거된 파일들
- ❌ `package.json` (Node.js 프로젝트로 인식 방지)
- ❌ `build.sh` (복잡한 빌드 스크립트 제거)
- ❌ `railway.toml` (기본 Nixpacks 사용)

## 📋 현재 설정

### runtime.txt
```
python-3.11
```

### Procfile
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --preload
```

### nixpacks.toml
```toml
[phases.setup]
aptPkgs = ["python3", "python3-pip"]

[phases.build]
cmds = ["python3 -m pip install -r requirements.txt"]

[phases.start]
cmd = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120"
```

## 🚀 배포 단계

### 1. 코드 푸시
```bash
git add .
git commit -m "Railway Python 빌드 환경 수정"
git push origin main
```

### 2. Railway에서 빌드 로그 확인
- Python 3.11 환경 설정 ✅
- pip 설치 성공 ✅
- requirements.txt 패키지 설치 ✅
- Gunicorn 시작 ✅

### 3. 환경변수 확인
Railway 대시보드에서:
```env
DATABASE_URL=postgresql://postgres.wrrxyiblfxawxurchdhs:Knkkjy701!@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
JWT_SECRET_KEY=AnIEeldAewYSslDMuSOb+smFnQeck9JqT+cEOsj2jgB6NPJ1i9420zFhfyNLKueAk2ohfNumn8Wp7I2T+i2q+A==
SECRET_KEY=knkkjy701!xZ9$mP8qR3nF7wE2bV5cL4hS6dG9jK1aU0yT8iO3pQ7rN2eM5vB4xC6zA1wS9fD3gH7k
FLASK_ENV=production
```

## 🧪 배포 후 테스트

### 1. 헬스체크
```bash
curl https://your-app.railway.app/health
```

### 2. 메인 페이지
```bash
curl https://your-app.railway.app/
```

### 3. API 테스트
```bash
curl -X POST https://your-app.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### 4. 자동 테스트
```bash
python test_railway_simple.py https://your-app.railway.app
```

## 📊 예상 결과

✅ **빌드 성공**: Python 3.11 + pip 설치  
✅ **앱 시작**: Gunicorn 정상 실행  
✅ **헬스체크**: `/health` 엔드포인트 200 응답  
✅ **API 동작**: JWT 인증 엔드포인트 작동  
✅ **웹 인터페이스**: 기존 Flask 템플릿 정상 표시  

## 🔄 문제 발생 시

### A. 빌드 실패
```bash
# Railway 로그 확인
railway logs --build

# Python 버전 문제 시
echo "python-3.10" > runtime.txt
```

### B. 앱 시작 실패
```bash
# 실행 로그 확인
railway logs

# Worker 수 줄이기
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
```

### C. 메모리 부족
```bash
# 더 적은 리소스 사용
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --max-requests 100
```

## 🎯 성공 지표

- [ ] Railway 빌드 완료 (녹색 체크)
- [ ] 헬스체크 통과 (5분 이내)
- [ ] 메인 URL 접속 가능
- [ ] API 응답 확인
- [ ] 로그 오류 없음

---

**현재 상태**: Python 전용 빌드 환경으로 최적화  
**다음 단계**: 안정적인 배포 후 React 프론트엔드 재통합