# Railway 통합 배포 가이드

## 🎯 개요

**단일 Railway 앱**에서 백엔드(Flask API) + 프런트엔드(React)를 함께 서빙합니다.

- ✅ **백엔드**: Flask API (JWT 인증)
- ✅ **프런트엔드**: React SPA (빌드된 정적 파일)
- ✅ **데이터베이스**: Supabase PostgreSQL
- ✅ **배포**: Railway 단일 서비스

## 🏗️ 통합 아키텍처

```
Railway 앱 (단일 서비스)
├── Flask 백엔드
│   ├── /api/* → JSON API 응답
│   ├── /health → 헬스체크
│   └── /* → React SPA 서빙
└── React 프런트엔드 (빌드됨)
    └── frontend/dist/* → 정적 파일
```

## 📋 배포 전 체크리스트

### 1. 필요한 파일들
```
LaborApp/
├── app.py                 # 통합 Flask 앱
├── package.json          # Node.js 설정
├── Procfile              # Railway 실행 명령
├── railway.toml          # Railway 빌드 설정
├── build.sh              # 통합 빌드 스크립트
├── requirements.txt      # Python 의존성
└── frontend/
    ├── package.json      # React 의존성
    └── src/              # React 소스
```

### 2. 환경 변수
Railway 대시보드에서 설정:
```env
DATABASE_URL=postgresql://user:pass@host:port/db
JWT_SECRET_KEY=your-super-secret-jwt-key
SECRET_KEY=flask-session-secret-key
FLASK_ENV=production
```

## 🚀 Railway 배포 단계

### 1. Railway 프로젝트 생성
```bash
# Railway CLI 설치
npm install -g @railway/cli

# Railway 로그인
railway login

# 프로젝트 연결
railway link
```

### 2. 환경 변수 설정
Railway 웹 대시보드에서:
- `DATABASE_URL`: Supabase 연결 문자열
- `JWT_SECRET_KEY`: 강력한 JWT 시크릿
- `SECRET_KEY`: Flask 세션 키
- `NODE_VERSION`: 18 (자동 감지됨)

### 3. 배포 실행
```bash
# 코드 푸시 (자동 빌드 & 배포)
git add .
git commit -m "Railway 통합 배포"
git push origin main

# 또는 직접 배포
railway up
```

## 🔧 빌드 프로세스

Railway에서 자동으로 실행되는 과정:

1. **Node.js 환경 설정** (v18)
2. **Python 환경 설정** (v3.11)
3. **빌드 스크립트 실행**:
   ```bash
   chmod +x build.sh && ./build.sh
   ```
4. **빌드 스크립트 내용**:
   - `pip install -r requirements.txt` (Python 의존성)
   - `cd frontend && npm install` (React 의존성)
   - `npm run build` (React 빌드 → `frontend/dist/`)
5. **앱 시작**: `gunicorn app:app`

## 🌐 라우팅 구조

배포된 앱의 URL 구조:

```
https://your-app.railway.app/
├── /                     → React 앱 (index.html)
├── /login                → React 로그인 페이지
├── /admin                → React 관리자 대시보드
├── /dashboard            → React 사용자 대시보드
├── /api/auth/login       → JWT 로그인 API
├── /api/auth/me          → 사용자 정보 API
├── /api/projects         → 프로젝트 목록 API
├── /api/admin/dashboard  → 관리자 대시보드 API
├── /health               → 헬스체크
└── /assets/*             → React 정적 파일 (CSS, JS)
```

## 🧪 배포 후 테스트

### 1. 헬스체크
```bash
curl https://your-app.railway.app/health
```

### 2. API 테스트
```bash
# 로그인 테스트
curl -X POST https://your-app.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

### 3. React 앱 접속
브라우저에서 `https://your-app.railway.app` 접속

## ⚡ 성능 최적화

### Railway 설정
- **Workers**: 2개 (메모리 효율성)
- **Timeout**: 120초
- **Restart Policy**: ON_FAILURE

### React 최적화
- **빌드 최적화**: Vite 번들링
- **정적 파일**: Flask에서 직접 서빙
- **캐싱**: 브라우저 캐시 활용

## 🔍 모니터링

### Railway 대시보드에서 확인:
1. **메트릭스**: CPU, 메모리 사용률
2. **로그**: 실시간 애플리케이션 로그
3. **배포 상태**: 빌드 성공/실패

### 로그 확인:
```bash
railway logs
```

## 🚨 트러블슈팅

### 1. "Application failed to respond"
**원인**: 앱이 시작되지 않음
**해결**:
```bash
railway logs  # 로그 확인
```
- 데이터베이스 연결 확인
- 환경 변수 설정 확인
- 빌드 오류 확인

### 2. API 호출 실패
**원인**: JWT 토큰 또는 CORS 문제
**해결**:
- JWT_SECRET_KEY 환경 변수 확인
- API URL이 정확한지 확인

### 3. React 앱 로드 실패
**원인**: 빌드 파일이 없음
**해결**:
```bash
# 로컬에서 빌드 테스트
cd frontend
npm install
npm run build
```

### 4. 데이터베이스 연결 실패
**원인**: Supabase 연결 설정 문제
**해결**:
- DATABASE_URL 형식 확인
- Supabase 프로젝트 상태 확인

## 📊 용량 및 한계

### Railway 무료 플랜:
- **실행 시간**: 월 500시간
- **메모리**: 512MB
- **대역폭**: 무제한
- **빌드 시간**: 빌드당 10분

### 업그레이드 고려 시점:
- 사용자 100명 이상
- 동시 접속 20명 이상
- 월 실행 시간 500시간 초과

## 🔄 업데이트 배포

코드 변경 후:
```bash
git add .
git commit -m "기능 업데이트"
git push origin main
# Railway에서 자동 재배포됨
```

---

## ✅ 배포 완료 확인

✅ Railway 앱 URL 접속 가능  
✅ React 로그인 페이지 표시  
✅ API 로그인 동작  
✅ 관리자/사용자 대시보드 정상 동작  
✅ 데이터베이스 연결 정상  

**🎉 단일 Railway 앱에서 풀스택 서비스 완료!**