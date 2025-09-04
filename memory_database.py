# memory_database.py - 메모리 기반 임시 데이터베이스
import json
from datetime import datetime, date

class MemoryDatabaseManager:
    def __init__(self):
        """메모리 기반 데이터베이스 초기화"""
        self.users = {
            'admin': {
                'password': 'admin123',
                'role': 'admin',
                'status': 'active'
            },
            'test': {
                'password': 'test123',
                'role': 'user',
                'status': 'active'
            }
        }
        
        self.projects = {}
        
        self.labor_costs = {
            '일반작업': 150000,
            '특수작업': 200000,
            '기계작업': 180000
        }
        
        print("✅ 메모리 데이터베이스 초기화 완료")
    
    def get_users(self):
        """사용자 목록 반환"""
        return self.users.copy()
    
    def get_projects(self):
        """프로젝트 목록 반환"""
        return self.projects.copy()
    
    def get_labor_costs(self):
        """노무단가 목록 반환"""
        return self.labor_costs.copy()
    
    def add_user(self, username, password, role='user'):
        """사용자 추가"""
        self.users[username] = {
            'password': password,
            'role': role,
            'status': 'active'
        }
        return True
    
    def add_project(self, project_name, project_data):
        """프로젝트 추가"""
        self.projects[project_name] = project_data
        return True
    
    def update_labor_cost(self, work_type, cost):
        """노무단가 업데이트"""
        self.labor_costs[work_type] = cost
        return True
    
    def close(self):
        """연결 종료 (메모리 DB에서는 불필요)"""
        pass