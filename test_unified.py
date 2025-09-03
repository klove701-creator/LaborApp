# test_unified.py - 통합 Railway 앱 테스트
import requests
import sys
import time

class UnifiedAppTester:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.token = None
        
    def test_health(self):
        """헬스체크 테스트"""
        print("🏥 헬스체크 테스트...")
        try:
            response = requests.get(f'{self.base_url}/health', timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 헬스체크 성공: {data.get('status')}")
                return True
            else:
                print(f"❌ 헬스체크 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 헬스체크 오류: {e}")
            return False
    
    def test_react_app(self):
        """React 앱 로드 테스트"""
        print("⚛️ React 앱 테스트...")
        try:
            response = requests.get(f'{self.base_url}/', timeout=10)
            if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
                print("✅ React 앱 로드 성공")
                return True
            else:
                print(f"❌ React 앱 로드 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ React 앱 로드 오류: {e}")
            return False
    
    def test_api_login(self):
        """API 로그인 테스트"""
        print("🔐 API 로그인 테스트...")
        try:
            response = requests.post(f'{self.base_url}/api/auth/login', 
                                   json={'username': 'admin', 'password': 'admin'},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
                user = data.get('user', {})
                print(f"✅ API 로그인 성공: {user.get('username')} ({user.get('role')})")
                return True
            else:
                print(f"❌ API 로그인 실패: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ API 로그인 오류: {e}")
            return False
    
    def test_api_projects(self):
        """API 프로젝트 조회 테스트"""
        if not self.token:
            print("⚠️ 토큰이 없어 프로젝트 테스트를 건너뜁니다.")
            return False
            
        print("📁 API 프로젝트 조회 테스트...")
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.get(f'{self.base_url}/api/projects', 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                projects = data.get('projects', {})
                print(f"✅ 프로젝트 조회 성공: {len(projects)}개 프로젝트")
                return True
            else:
                print(f"❌ 프로젝트 조회 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 프로젝트 조회 오류: {e}")
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print(f"🚀 통합 앱 테스트 시작: {self.base_url}\n")
        
        tests = [
            ("헬스체크", self.test_health),
            ("React 앱", self.test_react_app),
            ("API 로그인", self.test_api_login),
            ("API 프로젝트", self.test_api_projects),
        ]
        
        passed = 0
        total = len(tests)
        
        for name, test_func in tests:
            print(f"[{passed + 1}/{total}] {name} 테스트 중...")
            if test_func():
                passed += 1
            print()
            time.sleep(1)  # API 호출 간 간격
        
        print(f"📊 테스트 결과: {passed}/{total} 통과")
        
        if passed == total:
            print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
            print(f"✅ 앱이 정상적으로 배포되었습니다: {self.base_url}")
        else:
            print("⚠️ 일부 테스트가 실패했습니다.")
            print("📋 확인사항:")
            print("  1. Railway 앱이 실행 중인지 확인")
            print("  2. 환경 변수가 올바르게 설정되었는지 확인")
            print("  3. 데이터베이스 연결이 정상인지 확인")
        
        return passed == total

def main():
    if len(sys.argv) != 2:
        print("사용법: python test_unified.py <RAILWAY_APP_URL>")
        print("예시: python test_unified.py https://your-app.railway.app")
        sys.exit(1)
    
    app_url = sys.argv[1]
    tester = UnifiedAppTester(app_url)
    success = tester.run_all_tests()
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()