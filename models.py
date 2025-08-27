# models.py - 데이터 관리 및 비즈니스 로직
import json
import os
from datetime import datetime, date

class DataManager:
    def __init__(self):
        self.users = {}
        self.projects_data = {}
        self.labor_costs = {}
        # 경로/유틸
        BASE_DIR = os.environ.get('RAILWAY_VOLUME') or os.environ.get('TMPDIR') or os.getcwd()
        self.DATA_FILE = os.path.join(BASE_DIR, 'app_data.json')
        self.load_data()
    
    def load_data(self):
        """JSON 파일에서 데이터 로드 - 운영 환경에서 데이터 보존"""
        print(f"🔍 JSON 파일 경로: {self.DATA_FILE} (존재: {os.path.exists(self.DATA_FILE)})")
        
        # 기존 데이터 파일이 있으면 절대 덮어쓰지 않음
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.projects_data = data.get('projects_data', {})
                    self.labor_costs = data.get('labor_costs', {})
                    print(f"✅ 기존 데이터 로드 완료! 프로젝트 {len(self.projects_data)}개, 사용자 {len(self.users)}개")
                    
                    # admin 계정이 없으면 추가 (기존 데이터 보존하면서)
                    if 'admin' not in self.users:
                        print("⚠️ admin 계정 없음 - 추가 생성")
                        self.users['admin'] = {'password': '1234', 'role': 'admin'}
                        self.save_data()
                    return
            except Exception as e:
                print(f"❌ 데이터 로드 실패: {e}")
                print("🔧 기존 파일을 백업하고 기본 계정만 생성합니다")
                # 기존 파일 백업
                import shutil
                backup_file = self.DATA_FILE + '.backup'
                shutil.copy2(self.DATA_FILE, backup_file)
                print(f"📁 백업 파일: {backup_file}")
        
        # 파일이 없거나 로드 실패시에만 기본 데이터 생성
        print("📄 새 설치 감지 - admin 계정만 생성")
        self._create_default_data()
        self.save_data()
    
    def _create_default_data(self):
        """기본 데이터 생성 (관리자 계정만)"""
        self.users = {
            'admin': {'password': '1234', 'role': 'admin'}
        }
        
        self.projects_data = {}
        
        self.labor_costs = {}
    
    def save_data(self):
        """모든 데이터를 JSON 파일에 저장"""
        try:
            os.makedirs(os.path.dirname(self.DATA_FILE), exist_ok=True)
            data = {
                'users': self.users,
                'projects_data': self.projects_data,
                'labor_costs': self.labor_costs,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 원자적 쓰기: 임시 파일에 먼저 저장 후 이동
            temp_file = self.DATA_FILE + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 임시 파일을 실제 파일로 이동 (원자적 연산)
            import shutil
            shutil.move(temp_file, self.DATA_FILE)
            
            print(f"✅ 데이터 저장 완료! → {self.DATA_FILE}")
            return True
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
            # 임시 파일 정리
            try:
                if os.path.exists(self.DATA_FILE + '.tmp'):
                    os.remove(self.DATA_FILE + '.tmp')
            except:
                pass
            return False