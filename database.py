# database.py - Supabase PostgreSQL 연결
import os
import psycopg2
import json
from datetime import datetime, date
from psycopg2.extras import RealDictCursor

class DatabaseManager:
    def __init__(self):
        # Supabase 연결 정보
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
        
        self.conn = None
        self.connect()
    
    def connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = psycopg2.connect(
                self.database_url,
                cursor_factory=RealDictCursor
            )
            print("✅ Supabase PostgreSQL 연결 성공")
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            raise
    
    def get_cursor(self):
        """커서 생성 (연결 확인 포함)"""
        if self.conn is None or self.conn.closed:
            self.connect()
        return self.conn.cursor()
    
    # ===== 사용자 관리 =====
    def get_users(self):
        """모든 사용자 조회"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT username, password, role, status, created_date, projects
                FROM users
            """)
            users_data = {}
            for row in cur.fetchall():
                users_data[row['username']] = {
                    'password': row['password'],
                    'role': row['role'],
                    'status': row['status'],
                    'created_date': str(row['created_date']),
                    'projects': row['projects'] or []
                }
            return users_data
    
    def create_user(self, username, password, role, projects=None, status='active'):
        """사용자 생성"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, password, role, projects, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, password, role, projects or [], status))
            self.conn.commit()
    
    def update_user(self, old_username, new_username=None, password=None, 
                    role=None, projects=None, status=None):
        """사용자 정보 업데이트"""
        with self.get_cursor() as cur:
            # 동적 UPDATE 쿼리 생성
            updates = []
            values = []
            
            if new_username and new_username != old_username:
                updates.append("username = %s")
                values.append(new_username)
            if password:
                updates.append("password = %s")
                values.append(password)
            if role:
                updates.append("role = %s")
                values.append(role)
            if projects is not None:
                updates.append("projects = %s")
                values.append(projects)
            if status:
                updates.append("status = %s")
                values.append(status)
            
            if updates:
                query = f"UPDATE users SET {', '.join(updates)} WHERE username = %s"
                values.append(old_username)
                cur.execute(query, values)
                self.conn.commit()
    
    def delete_user(self, username):
        """사용자 삭제"""
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM users WHERE username = %s", (username,))
            self.conn.commit()
    
    # ===== 프로젝트 관리 =====
    def get_projects(self):
        """모든 프로젝트 조회"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT project_name, status, created_date, work_types, contracts, companies
                FROM projects
            """)
            projects_data = {}
            for row in cur.fetchall():
                projects_data[row['project_name']] = {
                    'status': row['status'],
                    'created_date': str(row['created_date']),
                    'work_types': row['work_types'] or [],
                    'contracts': row['contracts'] or {},
                    'companies': row['companies'] or {},
                    'daily_data': self._get_project_daily_data(row['project_name'])
                }
            return projects_data
    
    def _get_project_daily_data(self, project_name):
        """프로젝트의 일일 데이터 조회"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT work_date, work_type, day_workers, night_workers, 
                       midnight_workers, total_workers, progress
                FROM daily_data 
                WHERE project_name = %s
                ORDER BY work_date, work_type
            """, (project_name,))
            
            daily_data = {}
            for row in cur.fetchall():
                date_str = str(row['work_date'])
                if date_str not in daily_data:
                    daily_data[date_str] = {}
                
                daily_data[date_str][row['work_type']] = {
                    'day': row['day_workers'],
                    'night': row['night_workers'],
                    'midnight': row['midnight_workers'],
                    'total': row['total_workers'],
                    'progress': float(row['progress'])
                }
            return daily_data
    
    def create_project(self, project_name, work_types, contracts=None, 
                      companies=None, status='active'):
        """프로젝트 생성"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO projects (project_name, work_types, contracts, companies, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_name, work_types, 
                  json.dumps(contracts or {}), 
                  json.dumps(companies or {}), 
                  status))
            self.conn.commit()
    
    def update_project(self, project_name, **kwargs):
        """프로젝트 업데이트"""
        with self.get_cursor() as cur:
            updates = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['work_types', 'contracts', 'companies']:
                    updates.append(f"{key} = %s")
                    values.append(json.dumps(value) if key in ['contracts', 'companies'] else value)
                elif key in ['status']:
                    updates.append(f"{key} = %s")
                    values.append(value)
            
            if updates:
                query = f"UPDATE projects SET {', '.join(updates)} WHERE project_name = %s"
                values.append(project_name)
                cur.execute(query, values)
                self.conn.commit()
    
    def delete_project(self, project_name):
        """프로젝트 및 관련 일일 데이터 삭제"""
        with self.get_cursor() as cur:
            # 일일 데이터 먼저 삭제
            cur.execute("DELETE FROM daily_data WHERE project_name = %s", (project_name,))
            # 프로젝트 삭제
            cur.execute("DELETE FROM projects WHERE project_name = %s", (project_name,))
            self.conn.commit()
    
    # ===== 일일 데이터 관리 =====
    def save_daily_data(self, project_name, work_date, work_type, 
                       day_workers, night_workers, midnight_workers, progress=0.0):
        """일일 출역 데이터 저장/업데이트"""
        total_workers = day_workers + night_workers + midnight_workers
        
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO daily_data 
                (project_name, work_date, work_type, day_workers, night_workers, 
                 midnight_workers, total_workers, progress, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (project_name, work_date, work_type)
                DO UPDATE SET
                    day_workers = EXCLUDED.day_workers,
                    night_workers = EXCLUDED.night_workers,
                    midnight_workers = EXCLUDED.midnight_workers,
                    total_workers = EXCLUDED.total_workers,
                    progress = EXCLUDED.progress,
                    updated_at = NOW()
            """, (project_name, work_date, work_type, day_workers, 
                  night_workers, midnight_workers, total_workers, progress))
            self.conn.commit()
    
    # ===== 노무단가 관리 =====
    def get_labor_costs(self):
        """모든 노무단가 조회"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT work_type, day_cost, night_cost, midnight_cost, locked
                FROM labor_costs
            """)
            labor_costs = {}
            for row in cur.fetchall():
                labor_costs[row['work_type']] = {
                    'day': row['day_cost'],
                    'night': row['night_cost'],
                    'midnight': row['midnight_cost'],
                    'locked': row['locked']
                }
            return labor_costs
    
    def save_labor_cost(self, work_type, day_cost, night_cost, midnight_cost, locked=False):
        """노무단가 저장/업데이트"""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO labor_costs (work_type, day_cost, night_cost, midnight_cost, locked)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (work_type)
                DO UPDATE SET
                    day_cost = EXCLUDED.day_cost,
                    night_cost = EXCLUDED.night_cost,
                    midnight_cost = EXCLUDED.midnight_cost,
                    locked = EXCLUDED.locked
            """, (work_type, day_cost, night_cost, midnight_cost, locked))
            self.conn.commit()
    
    def delete_labor_cost(self, work_type):
        """노무단가 삭제"""
        with self.get_cursor() as cur:
            cur.execute("DELETE FROM labor_costs WHERE work_type = %s", (work_type,))
            self.conn.commit()
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()
            print("✅ 데이터베이스 연결 종료")