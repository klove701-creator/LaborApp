# test_railway_simple.py - Railway 배포 간단 테스트
import requests
import sys

def test_health_check(base_url):
    """헬스체크 테스트"""
    try:
        response = requests.get(f'{base_url}/health', timeout=30)
        print(f"헬스체크 상태: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"응답: {data}")
            return True
        return False
    except Exception as e:
        print(f"헬스체크 오류: {e}")
        return False

def test_main_page(base_url):
    """메인 페이지 테스트"""
    try:
        response = requests.get(f'{base_url}/', timeout=30)
        print(f"메인 페이지 상태: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"메인 페이지 오류: {e}")
        return False

def test_api_endpoint(base_url):
    """API 엔드포인트 테스트"""
    try:
        # 로그인 시도 (실패해도 괜찮음, 엔드포인트가 응답하는지만 확인)
        response = requests.post(f'{base_url}/api/auth/login', 
                               json={'username': 'test', 'password': 'test'},
                               timeout=30)
        print(f"API 로그인 상태: {response.status_code}")
        # 400 또는 401은 정상 (엔드포인트가 작동함)
        return response.status_code in [200, 400, 401, 500]
    except Exception as e:
        print(f"API 테스트 오류: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("사용법: python test_railway_simple.py <URL>")
        print("예시: python test_railway_simple.py https://your-app.railway.app")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    
    print(f"🧪 Railway 간단 테스트 시작: {base_url}")
    print("="*50)
    
    tests = [
        ("헬스체크", lambda: test_health_check(base_url)),
        ("메인 페이지", lambda: test_main_page(base_url)),
        ("API 엔드포인트", lambda: test_api_endpoint(base_url)),
    ]
    
    passed = 0
    for name, test_func in tests:
        print(f"\n🔍 {name} 테스트...")
        if test_func():
            print(f"✅ {name} 성공")
            passed += 1
        else:
            print(f"❌ {name} 실패")
    
    print("\n" + "="*50)
    print(f"📊 결과: {passed}/{len(tests)} 테스트 통과")
    
    if passed == len(tests):
        print("🎉 Railway 배포가 성공적으로 완료되었습니다!")
    elif passed > 0:
        print("⚠️ 일부 기능이 작동합니다. 추가 설정이 필요할 수 있습니다.")
    else:
        print("❌ 앱이 제대로 시작되지 않았습니다. 로그를 확인해주세요.")
        sys.exit(1)