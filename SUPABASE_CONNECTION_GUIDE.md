# Supabase 데이터베이스 연결 문제 해결

## 🚨 현재 오류
```
FATAL: password authentication failed for user "postgres"
```

## 🔍 문제 분석

현재 사용 중인 연결 문자열:
```
postgresql://postgres.wrrxyiblfxawxurchdhs:Knkkjy701!@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
```

## ✅ Supabase 연결 정보 확인 방법

### 1. Supabase 대시보드에서 확인
1. [Supabase Dashboard](https://app.supabase.com) 접속
2. 프로젝트 선택
3. Settings → Database 이동
4. "Connection String" 섹션에서 확인

### 2. 올바른 형식
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

또는 Connection Pooling 사용 시:
```
postgresql://postgres.wrrxyiblfxawxurchdhs:[YOUR-PASSWORD]@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
```

## 🔧 해결 단계

### A. 비밀번호 확인
Supabase에서 데이터베이스 비밀번호를 재확인하거나 재설정:

1. Supabase Dashboard → Settings → Database
2. "Reset database password" 클릭
3. 새 비밀번호 생성
4. 연결 문자열 업데이트

### B. 연결 문자열 형식 수정
```env
# 기본 연결 (포트 5432)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.wrrxyiblfxawxurchdhs.supabase.co:5432/postgres

# 또는 Connection Pooling (포트 6543) - 고성능
DATABASE_URL=postgresql://postgres.wrrxyiblfxawxurchdhs:[PASSWORD]@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
```

### C. Railway 환경변수 업데이트
1. Railway Dashboard → 프로젝트 → Variables
2. `DATABASE_URL` 수정
3. 새 연결 문자열로 교체
4. Deploy 버튼 클릭

## 🧪 연결 테스트

### 1. 로컬에서 테스트
```python
# test_db_connection.py
import psycopg2
import os

DATABASE_URL = "postgresql://postgres:[PASSWORD]@host:port/postgres"

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ 데이터베이스 연결 성공: {version[0]}")
    conn.close()
except Exception as e:
    print(f"❌ 데이터베이스 연결 실패: {e}")
```

### 2. Railway 배포 후 테스트
```bash
curl https://your-app.railway.app/health
# 응답에서 database: "connected" 확인
```

## 📋 일반적인 해결책들

### 1. 비밀번호에 특수문자가 있는 경우
```python
# URL 인코딩 필요
import urllib.parse
password = "My@Pass#123"
encoded_password = urllib.parse.quote(password, safe='')
DATABASE_URL = f"postgresql://postgres:{encoded_password}@host:port/postgres"
```

### 2. 프로젝트 참조(REF) 확인
```
# Supabase 프로젝트 REF 확인
wrrxyiblfxawxurchdhs - 이 부분이 정확한지 확인
```

### 3. SSL 모드 설정
```
postgresql://user:pass@host:port/db?sslmode=require
```

## 🔄 업데이트 예시

현재 문제가 있는 연결 문자열:
```
postgresql://postgres.wrrxyiblfxawxurchdhs:Knkkjy701!@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
```

수정된 연결 문자열 (예시):
```env
# Option 1: 직접 연결
DATABASE_URL=postgresql://postgres:NEW_PASSWORD@db.wrrxyiblfxawxurchdhs.supabase.co:5432/postgres

# Option 2: Connection Pooling (권장)
DATABASE_URL=postgresql://postgres.wrrxyiblfxawxurchdhs:NEW_PASSWORD@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres?sslmode=require
```

## ⚠️ 보안 주의사항

1. **비밀번호 노출 방지**: .env 파일을 git에 포함하지 마세요
2. **환경변수 사용**: Railway에서만 환경변수로 설정
3. **읽기 전용 사용자**: 가능하면 읽기 전용 데이터베이스 사용자 생성

## 🎯 성공 지표

- [ ] Railway 환경변수 업데이트 완료
- [ ] `/health` 엔드포인트에서 `database: "connected"` 응답
- [ ] 애플리케이션 로그에서 "✅ PostgreSQL 데이터베이스 연결 성공" 확인
- [ ] API 엔드포인트 정상 작동 (사용자 목록 조회 등)

---

**다음 단계**: Supabase에서 올바른 연결 정보 확인 후 Railway 환경변수 업데이트