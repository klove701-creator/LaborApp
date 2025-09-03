# test_static_files.py - 정적 파일 테스트
import requests
import sys

def test_static_files(base_url):
    """정적 파일 로딩 테스트"""
    base_url = base_url.rstrip('/')
    
    tests = [
        ('/health', '헬스체크 (정적 파일 상태 포함)'),
        ('/', '메인 페이지'),
        ('/static/style.css', 'CSS 파일'),
        ('/static/js/calendar.js', 'JavaScript 파일'),
    ]
    
    results = []
    
    for endpoint, description in tests:
        try:
            response = requests.get(f'{base_url}{endpoint}', timeout=30)
            
            if endpoint == '/health':
                if response.status_code == 200:
                    data = response.json()
                    static_status = data.get('static_files', 'unknown')
                    static_folder = data.get('static_folder', 'unknown')
                    print(f"✅ {description}: {response.status_code}")
                    print(f"   정적 파일: {static_status}, 폴더: {static_folder}")
                    results.append(True)
                else:
                    print(f"❌ {description}: {response.status_code}")
                    results.append(False)
            
            elif endpoint == '/':
                if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
                    print(f"✅ {description}: {response.status_code}")
                    # CSS 참조가 있는지 확인
                    if 'style.css' in response.text:
                        print("   CSS 참조 발견됨")
                    results.append(True)
                else:
                    print(f"❌ {description}: {response.status_code}")
                    results.append(False)
            
            elif endpoint.startswith('/static/'):
                if response.status_code == 200:
                    content_length = len(response.content)
                    print(f"✅ {description}: {response.status_code} ({content_length} bytes)")
                    results.append(True)
                else:
                    print(f"❌ {description}: {response.status_code}")
                    results.append(False)
            
        except Exception as e:
            print(f"❌ {description}: 오류 - {e}")
            results.append(False)
    
    return results

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("사용법: python test_static_files.py <URL>")
        print("예시: python test_static_files.py https://your-app.railway.app")
        sys.exit(1)
    
    base_url = sys.argv[1]
    
    print(f"🧪 정적 파일 테스트 시작: {base_url}")
    print("="*60)
    
    results = test_static_files(base_url)
    passed = sum(results)
    total = len(results)
    
    print("="*60)
    print(f"📊 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 정적 파일이 정상적으로 로드됩니다!")
    elif passed >= total // 2:
        print("⚠️ 일부 정적 파일에 문제가 있습니다.")
        print("💡 해결책:")
        print("  1. Railway 빌드 로그에서 static/ 폴더 복사 확인")
        print("  2. 정적 파일 라우팅 확인")
        print("  3. 파일 권한 확인")
    else:
        print("❌ 대부분의 정적 파일 로딩에 실패했습니다.")
        print("💡 해결책:")
        print("  1. static/ 폴더가 git에 포함되었는지 확인")
        print("  2. Railway에서 파일이 복사되었는지 확인")
        print("  3. Flask static_folder 설정 확인")
        sys.exit(1)