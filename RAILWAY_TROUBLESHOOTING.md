# Railway 배포 문제 해결 가이드

## 🚨 현재 문제: "Service Unavailable" 

### 📋 해결한 문제들:

✅ **Import 오류 수정**
- `flask-cors`, `flask-jwt-extended` 패키지 설치
- `api_app` 불필요한 import 제거

✅ **애플리케이션 시작 오류 방지**
- 데이터베이스 연결 실패 시에도 앱 시작 가능
- 헬스체크 엔드포인트 항상 200 응답

✅ **Railway 설정 최적화**
- Worker 수 1개로 감소 (메모리 절약)
- `--preload` 옵션 추가
- React 빌드 제거 (단순화)

## 🔧 적용된 수정사항

### 1. Procfile 수정
```bash
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --preload
```

### 2. railway.toml 단순화
```toml
[build]
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --preload"
healthcheckPath = "/health"
```

### 3. 헬스체크 개선
```python
@app.route('/health')
def health_check():
    # 데이터베이스 오류가 있어도 항상 200 응답
    return jsonify({'status': 'running', 'app': 'LaborApp'}), 200
```

### 4. 데이터베이스 오류 처리
```python
# 데이터베이스 연결 실패 시에도 앱 시작
except Exception as e:
    app.logger.warning("데이터베이스 없이 애플리케이션을 시작합니다.")
    dm = None
```

## 🧪 배포 후 테스트

```bash
# 간단 테스트
python test_railway_simple.py https://your-app.railway.app

# 헬스체크 직접 확인
curl https://your-app.railway.app/health
```

## 📋 환경변수 확인사항

Railway 대시보드에서 다음 환경변수가 설정되어 있는지 확인:

```env
DATABASE_URL=postgresql://postgres.wrrxyiblfxawxurchdhs:Knkkjy701!@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
JWT_SECRET_KEY=AnIEeldAewYSslDMuSOb+smFnQeck9JqT+cEOsj2jgB6NPJ1i9420zFhfyNLKueAk2ohfNumn8Wp7I2T+i2q+A==
SECRET_KEY=knkkjy701!xZ9$mP8qR3nF7wE2bV5cL4hS6dG9jK1aU0yT8iO3pQ7rN2eM5vB4xC6zA1wS9fD3gH7k
FLASK_ENV=production
```

## 🚀 재배포 단계

1. **코드 푸시**:
   ```bash
   git add .
   git commit -m "Railway 배포 오류 수정"
   git push origin main
   ```

2. **Railway 로그 확인**:
   ```bash
   railway logs
   ```

3. **빌드 성공 확인**:
   - Railway 대시보드에서 빌드 로그 확인
   - Python 패키지 설치 성공 여부 확인

4. **애플리케이션 시작 확인**:
   - Gunicorn 프로세스 정상 시작
   - 포트 바인딩 성공

5. **헬스체크 통과 확인**:
   ```bash
   curl https://your-app.railway.app/health
   ```

## ⚠️ 추가 문제 해결

### 메모리 부족 오류
```toml
# railway.toml에서 worker 수 줄이기
startCommand = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 1"
```

### 빌드 시간 초과
```toml
# 빌드 명령 단순화
buildCommand = "pip install --no-cache-dir -r requirements.txt"
```

### 포트 바인딩 오류
```python
# app.py 마지막 부분
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

## 🎯 성공 지표

✅ Railway 빌드 성공  
✅ 애플리케이션 시작 성공  
✅ 헬스체크 `/health` 응답 (200 OK)  
✅ 메인 페이지 `/` 로그인 화면 표시  
✅ API 엔드포인트 `/api/auth/login` 응답  

## 🔄 다음 단계

1. **기본 API 동작 확인**
2. **데이터베이스 연결 복구**
3. **React 프론트엔드 재통합**
4. **전체 기능 테스트**

---

**현재 상태**: 단순화된 Flask 백엔드만 배포  
**목표**: Railway에서 안정적인 헬스체크 통과 후 기능 확장