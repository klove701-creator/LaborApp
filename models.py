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
        """JSON 파일에서 데이터 로드"""
        print(f"🔍 JSON 파일 경로: {self.DATA_FILE} (존재: {os.path.exists(self.DATA_FILE)})")
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.projects_data = data.get('projects_data', {})
                    self.labor_costs = data.get('labor_costs', {})
                    print(f"✅ 데이터 로드 완료! 프로젝트 수: {len(self.projects_data)}")
                    return
            except Exception as e:
                print(f"❌ 데이터 로드 실패: {e}")
        
        print("📄 새 데이터 생성")
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
            with open(self.DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 데이터 저장 완료! → {self.DATA_FILE}")
            return True
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
            return False