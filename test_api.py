# test_api.py - API 엔드포인트 테스트 스크립트
import requests
import json
import os

# 테스트 설정
API_BASE_URL = 'http://localhost:5000/api'
TEST_USERNAME = 'admin'
TEST_PASSWORD = 'admin'

class APITester:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        
    def test_login(self):
        """로그인 테스트"""
        print("🧪 로그인 테스트...")
        try:
            response = self.session.post(f'{API_BASE_URL}/auth/login', json={
                'username': TEST_USERNAME,
                'password': TEST_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
                self.session.headers.update({'Authorization': f'Bearer {self.token}'})
                print(f"✅ 로그인 성공: {data.get('user', {}).get('username')}")
                return True
            else:
                print(f"❌ 로그인 실패: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ 로그인 오류: {e}")
            return False
    
    def test_get_current_user(self):
        """현재 사용자 정보 조회 테스트"""
        print("🧪 사용자 정보 조회 테스트...")
        try:
            response = self.session.get(f'{API_BASE_URL}/auth/me')
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ 사용자 정보 조회 성공: {user_data.get('username')} ({user_data.get('role')})")
                return True
            else:
                print(f"❌ 사용자 정보 조회 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 사용자 정보 조회 오류: {e}")
            return False
    
    def test_get_projects(self):
        """프로젝트 목록 조회 테스트"""
        print("🧪 프로젝트 목록 조회 테스트...")
        try:
            response = self.session.get(f'{API_BASE_URL}/projects')

            if response.status_code == 200:
                projects = response.json()
                print(f"✅ 프로젝트 목록 조회 성공: {len(projects)}개 프로젝트")
                if projects:
                    sample_ids = [p.get('id') for p in projects[:3]]
                    print(f"   📋 프로젝트: {sample_ids}")
                return True
            else:
                print(f"❌ 프로젝트 목록 조회 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 프로젝트 목록 조회 오류: {e}")
            return False
    
    def test_admin_dashboard(self):
        """관리자 대시보드 테스트"""
        print("🧪 관리자 대시보드 테스트...")
        try:
            response = self.session.get(f'{API_BASE_URL}/admin/dashboard')
            
            if response.status_code == 200:
                dashboard = response.json().get('dashboard', [])
                print(f"✅ 관리자 대시보드 조회 성공: {len(dashboard)}개 프로젝트 요약")
                return True
            else:
                print(f"❌ 관리자 대시보드 조회 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 관리자 대시보드 조회 오류: {e}")
            return False
    
    def test_labor_costs(self):
        """노무단가 조회 테스트"""
        print("🧪 노무단가 조회 테스트...")
        try:
            response = self.session.get(f'{API_BASE_URL}/labor-costs')
            
            if response.status_code == 200:
                labor_costs = response.json().get('labor_costs', {})
                print(f"✅ 노무단가 조회 성공: {len(labor_costs)}개 공종")
                return True
            else:
                print(f"❌ 노무단가 조회 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 노무단가 조회 오류: {e}")
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 API 엔드포인트 통합 테스트 시작\n")
        
        tests = [
            self.test_login,
            self.test_get_current_user,
            self.test_get_projects,
            self.test_admin_dashboard,
            self.test_labor_costs,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            print()
        
        print(f"📊 테스트 결과: {passed}/{total} 통과")
        
        if passed == total:
            print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            print("⚠️ 일부 테스트가 실패했습니다. API 서버 상태를 확인해주세요.")
        
        return passed == total

if __name__ == '__main__':
    tester = APITester()
    success = tester.run_all_tests()
    
    if not success:
        print("\n💡 해결책:")
        print("1. API 서버가 실행 중인지 확인 (python api_app.py)")
        print("2. 데이터베이스 연결이 정상인지 확인")
        print("3. 테스트 계정이 데이터베이스에 존재하는지 확인")
        exit(1)