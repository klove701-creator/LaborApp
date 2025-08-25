# models.py - 데이터 관리 모듈
from datetime import datetime, date
import json
import os

DATA_FILE = 'app_data.json'

class DataManager:
    def __init__(self):
        self.users = {}
        self.projects_data = {}
        self.labor_costs = {}
        self.load_data()
    
    def load_data(self):
        """JSON 파일에서 데이터 로드"""
        print(f"🔍 JSON 파일 존재 여부: {os.path.exists(DATA_FILE)}")
        
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.projects_data = data.get('projects_data', {})
                    self.labor_costs = data.get('labor_costs', {})
                    print(f"✅ 데이터 로드 완료! 프로젝트 수: {len(self.projects_data)}")
                    return
            except Exception as e:
                print(f"❌ 데이터 로드 실패: {e}")
        
        # 기본 데이터
        print("📄 새 데이터 생성")
        self._create_default_data()
        self.save_data()
    
    def _create_default_data(self):
        """기본 데이터 생성"""
        self.users = {
            'admin': {'password': '1234', 'role': 'admin'},
            'user1': {'password': '1234', 'role': 'user', 'projects': ['현대카드 인테리어공사']}
        }
        
        self.projects_data = {
            '현대카드 인테리어공사': {
                'work_types': ['도장공사', '목공사', '타일'],
                'daily_data': {},
                'status': 'active',
                'created_date': '2025-08-24',
                'contracts': {
                    '도장공사': 200000,
                    '목공사': 250000,
                    '타일': 300000
                }
            }
        }
        
        self.labor_costs = {
            '도장공사': {'day': 120000, 'night': 150000, 'midnight': 180000},
            '목공사': {'day': 130000, 'night': 160000, 'midnight': 190000},
            '타일': {'day': 140000, 'night': 170000, 'midnight': 200000}
        }
    
    def save_data(self):
        """모든 데이터를 JSON 파일에 저장"""
        try:
            data = {
                'users': self.users,
                'projects_data': self.projects_data,
                'labor_costs': self.labor_costs,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 데이터 저장 완료!")
            return True
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
            return False
    
    def add_project(self, project_name, work_types, contracts=None):
        """새 프로젝트 추가"""
        if project_name not in self.projects_data:
            self.projects_data[project_name] = {
                'work_types': work_types,
                'contracts': contracts or {},
                'daily_data': {},
                'status': 'active',
                'created_date': date.today().strftime('%Y-%m-%d')
            }
            return self.save_data()
        return False
    
    def delete_project(self, project_name):
        """프로젝트 삭제"""
        if project_name in self.projects_data:
            del self.projects_data[project_name]
            # 사용자들에서도 제거
            for user_data in self.users.values():
                if 'projects' in user_data and project_name in user_data['projects']:
                    user_data['projects'].remove(project_name)
            return self.save_data()
        return False
    
    def add_work_type_to_project(self, project_name, work_type, username):
        """프로젝트에 공종 추가"""
        if project_name in self.projects_data:
            if work_type not in self.projects_data[project_name]['work_types']:
                self.projects_data[project_name]['work_types'].append(work_type)
                
                # 노무단가에도 기본값 추가
                if work_type not in self.labor_costs:
                    self.labor_costs[work_type] = {
                        'day': 0, 'night': 0, 'midnight': 0,
                        'locked': False,
                        'created_by_user': username,
                        'created_date': date.today().strftime('%Y-%m-%d')
                    }
                
                return self.save_data()
        return False
    
    def save_daily_work(self, project_name, selected_date, work_data):
        """일일 출역 데이터 저장"""
        if project_name not in self.projects_data:
            return False
        
        if selected_date not in self.projects_data[project_name]['daily_data']:
            self.projects_data[project_name]['daily_data'][selected_date] = {}
        
        for work_type, data in work_data.items():
            self.projects_data[project_name]['daily_data'][selected_date][work_type] = data
        
        return self.save_data()

# 전역 데이터 매니저 인스턴스
data_manager = DataManager()