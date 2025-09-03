# LaborApp 배포 가이드

## 🚀 배포 개요

리팩토링된 LaborApp은 다음과 같이 배포됩니다:
- **백엔드**: Railway (Flask API)
- **프런트엔드**: Netlify/Vercel (React SPA)
- **데이터베이스**: Supabase PostgreSQL (현재 상태 유지)

## 📋 배포 전 체크리스트

### 1. 환경 변수 설정
```env
# 백엔드 (.env)
DATABASE_URL=postgresql://...     # Supabase 연결 문자열
JWT_SECRET_KEY=your-secret-key
SECRET_KEY=flask-secret-key
PORT=5000

# 프런트엔드 (.env)
VITE_API_URL=https://kiyenolabor.up.railway.app
```

### 2. 필수 파일 확인
- ✅ `requirements.txt` (Python 의존성)
- ✅ `Procfile` (Railway 실행 명령)
- ✅ `api_app.py` (메인 API 서버)
- ✅ `package.json` (React 의존성)

## 🛤️ Railway 백엔드 배포

### 1. Railway 프로젝트 생성
```bash
# Railway CLI 설치
npm install -g @railway/cli

# 로그인 및 프로젝트 생성
railway login
railway init
```

### 2. 환경 변수 설정
Railway 대시보드에서 다음 변수 설정:
```
DATABASE_URL=<your-supabase-connection-string>
JWT_SECRET_KEY=<generate-secure-key>
SECRET_KEY=<flask-secret-key>
```

### 3. 배포 실행
```bash
railway up
```

### 4. 도메인 확인
배포 완료 후 제공되는 URL 기록:
```
https://your-app-name.railway.app
```

## 🌐 Netlify/Vercel 프런트엔드 배포

### Option A: Netlify
1. GitHub에 코드 푸시
2. Netlify에서 새 사이트 생성
3. 빌드 설정:
   ```
   Build command: npm run build
   Publish directory: dist
   ```
4. 환경 변수 설정:
   ```
   VITE_API_URL=https://your-railway-domain.railway.app
   ```

### Option B: Vercel
```bash
# Vercel CLI 설치
npm install -g vercel

# 프로젝트 배포
cd frontend
vercel --prod
```

## 🧪 배포 후 테스트

### 1. API 헬스 체크
```bash
curl https://your-railway-domain.railway.app/api/health
```

### 2. 전체 기능 테스트
```bash
python test_api.py
```

### 3. 프런트엔드 접속 확인
브라우저에서 Netlify/Vercel URL 접속

## 🔧 환경별 설정

### 개발 환경
```bash
# 백엔드
python api_app.py

# 프런트엔드
cd frontend
npm run dev
```

### 프로덕션 환경
- **백엔드**: Railway 자동 배포
- **프런트엔드**: Netlify/Vercel 자동 배포
- **데이터베이스**: Supabase (무중단 서비스)

## 📊 모니터링

### 1. Railway 모니터링
- CPU, 메모리 사용률
- API 응답 시간
- 오류 로그 확인

### 2. 프런트엔드 모니터링
- 페이지 로드 시간
- JavaScript 오류
- 사용자 트래픽

## 🚨 트러블슈팅

### API 연결 실패
1. Railway 서비스 상태 확인
2. 환경 변수 `DATABASE_URL` 확인
3. Supabase 연결 상태 확인

### 프런트엔드 로그인 실패
1. API URL 설정 확인 (`VITE_API_URL`)
2. CORS 설정 확인
3. JWT 토큰 만료 시간 확인

### 성능 문제
1. Railway worker 수 조정
2. React Query 캐싱 최적화
3. 이미지/정적 파일 CDN 적용

## 📈 스케일링 전략

### 백엔드 스케일링
- Railway Pro 플랜으로 업그레이드
- 데이터베이스 연결 풀링
- Redis 캐싱 레이어 추가

### 프런트엔드 최적화
- 코드 스플리팅 적용
- Service Worker PWA 변환
- 이미지 최적화

## 🔐 보안 고려사항

### 1. API 보안
- JWT 토큰 만료 시간 단축 (현재 24시간)
- HTTPS 강제 적용
- Rate limiting 구현

### 2. 프런트엔드 보안
- CSP(Content Security Policy) 설정
- XSS 방지 헤더 추가
- 민감 정보 환경 변수 관리

---

## 📞 지원

배포 중 문제 발생 시:
1. `test_api.py` 스크립트 실행
2. Railway/Netlify 로그 확인
3. README_REFACTOR.md 참조

**배포 완료 후**: 기존 Flask 서버는 백업 후 중단 가능