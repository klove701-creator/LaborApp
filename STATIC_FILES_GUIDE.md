# CSS 스타일시트 로딩 오류 해결 가이드

## 🚨 문제: "This page failed to load a stylesheet from a URL"

### ❌ 발생 원인
```
style.css:1 - 스타일시트 로딩 실패
```

Railway 배포 환경에서 정적 파일(CSS, JS, 이미지)이 제대로 서빙되지 않는 문제

## ✅ 적용된 해결책

### 1. 명시적 정적 파일 라우팅
```python
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)
```

### 2. 헬스체크에 정적 파일 상태 추가
```python
@app.route('/health')
def health_check():
    static_files_exist = os.path.exists(os.path.join(app.static_folder or 'static', 'style.css'))
    return jsonify({
        'static_files': 'found' if static_files_exist else 'missing',
        'static_folder': app.static_folder or 'static'
    })
```

### 3. 빌드 시 정적 파일 확인
```toml
# nixpacks.toml
[phases.build]
cmds = [
  "python3 -m pip install -r requirements.txt",
  "ls -la static/",
  "ls -la templates/"
]
```

## 📁 현재 파일 구조

```
LaborApp/
├── app.py                    # Flask 앱 (정적 라우팅 추가)
├── static/                   # 정적 파일들
│   ├── style.css            # 메인 스타일시트
│   └── js/
│       ├── calendar.js      # 캘린더 스크립트
│       └── currency-format.js # 통화 포맷팅
├── templates/               # Flask 템플릿
│   ├── login.html          # 로그인 페이지
│   ├── base.html           # 기본 레이아웃
│   └── ...                 # 기타 템플릿들
└── nixpacks.toml           # 빌드 설정 (파일 확인 포함)
```

## 🧪 테스트 방법

### 1. 배포 후 정적 파일 테스트
```bash
python test_static_files.py https://your-app.railway.app
```

### 2. 개별 파일 직접 테스트
```bash
# CSS 파일
curl -I https://your-app.railway.app/static/style.css

# JavaScript 파일  
curl -I https://your-app.railway.app/static/js/calendar.js

# 헬스체크 (정적 파일 상태 포함)
curl https://your-app.railway.app/health
```

### 3. 브라우저에서 확인
1. 메인 페이지 접속: `https://your-app.railway.app/`
2. 개발자 도구 (F12) → Network 탭
3. CSS 파일 로딩 상태 확인
4. Console에서 404 오류 없는지 확인

## 📊 예상 결과

### ✅ 성공 시
```
✅ 헬스체크: 200 (정적 파일: found)
✅ 메인 페이지: 200 (CSS 참조 발견됨)
✅ CSS 파일: 200 (12,345 bytes)
✅ JavaScript 파일: 200 (1,234 bytes)
```

### ❌ 실패 시 해결 방법

#### A. 정적 파일이 없음 (404 오류)
```bash
# 파일이 git에 포함되었는지 확인
git ls-files | grep static/

# Railway 빌드 로그 확인
railway logs --build
```

#### B. 정적 파일 권한 문제
```python
# app.py에서 static_folder 명시적 설정
app = Flask(__name__, static_folder='static')
```

#### C. MIME 타입 문제
```python
# 정적 파일 라우트에서 MIME 타입 설정
@app.route('/static/<path:filename>')
def serve_static(filename):
    response = send_from_directory(app.static_folder, filename)
    if filename.endswith('.css'):
        response.headers['Content-Type'] = 'text/css'
    return response
```

## 🔧 추가 최적화

### 1. CSS 압축 (선택사항)
```bash
# 배포 전 CSS 최적화
pip install cssmin
python -c "import cssmin; open('static/style.min.css','w').write(cssmin.cssmin(open('static/style.css').read()))"
```

### 2. 정적 파일 캐싱
```python
@app.route('/static/<path:filename>')
def serve_static(filename):
    response = send_from_directory(app.static_folder, filename)
    response.headers['Cache-Control'] = 'public, max-age=3600'  # 1시간 캐싱
    return response
```

### 3. CDN 활용 (향후)
```html
<!-- 외부 CSS 라이브러리는 CDN 사용 -->
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<!-- 커스텀 CSS만 로컬 서빙 -->
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
```

## 🚀 배포 체크리스트

- [ ] `static/` 폴더가 git에 포함됨
- [ ] `templates/` 폴더가 git에 포함됨  
- [ ] Flask 앱에서 정적 라우팅 설정됨
- [ ] Railway 빌드 로그에서 파일 복사 확인
- [ ] 헬스체크에서 `static_files: found` 확인
- [ ] 브라우저에서 CSS 로딩 정상 확인

---

**현재 상태**: 정적 파일 서빙 개선 완료  
**다음 단계**: Railway 재배포 후 스타일시트 로딩 확인